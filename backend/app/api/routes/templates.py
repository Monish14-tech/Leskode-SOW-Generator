"""SOW Template management routes."""
import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.auth import get_current_user, require_role
from app.db.database import get_db
from app.db.models import (
    UserProfile, SowTemplate, SowTemplateVersion, TemplateStatus, UserRole
)
from app.document.extractor import extract_template_structure, ExtractionError

router = APIRouter()
logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path("templates")
TEMPLATES_DIR.mkdir(exist_ok=True)


def _template_dict(t: SowTemplate) -> dict:
    versions = [_version_dict(v) for v in (t.versions or [])]
    active_v = next((v for v in (t.versions or []) if v.status == TemplateStatus.ACTIVE), None)
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "organization_id": t.organization_id,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "active_version": {
            "id": active_v.id,
            "version_number": active_v.version_number,
            "status": active_v.status.value if active_v.status else "active",
            "original_filename": active_v.original_filename,
            "detected_placeholders": (active_v.extracted_structure or {}).get("placeholders", []) if active_v.extracted_structure else list((active_v.placeholder_map or {}).keys()),
        } if active_v else None,
        "versions": versions,
    }


def _version_dict(v: SowTemplateVersion) -> dict:
    return {
        "id": v.id,
        "template_id": v.template_id,
        "version_number": v.version_number,
        "original_filename": v.original_filename,
        "status": v.status.value if v.status else "draft",
        "section_map": v.section_map or {},
        "placeholder_map": v.placeholder_map or {},
        "extracted_structure": v.extracted_structure or {},
        "change_summary": v.change_summary,
        "published_at": v.published_at.isoformat() if v.published_at else None,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


@router.get("")
@router.get("/")
def list_templates(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    templates = db.query(SowTemplate).filter(
        SowTemplate.organization_id == current_user.organization_id
    ).all()
    return [_template_dict(t) for t in templates]


@router.post("/upload", status_code=201)
async def upload_template(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    change_summary: Optional[str] = Form(None),
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a master SOW template or sample SOW in any file format."""
    if not file or not file.filename:
        raise HTTPException(400, "No file uploaded.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, "Template file is empty.")
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(413, "Template file must be under 50MB.")

    # Clean template name or default to file stem
    clean_name = (name or "").strip()
    if not clean_name:
        clean_name = Path(file.filename).stem or "Master SOW Template"

    ext = Path(file.filename).suffix.lower()

    # Save file to backend templates directory with absolute path
    backend_base = Path(__file__).resolve().parent.parent.parent.parent
    templates_dir = backend_base / "templates"
    templates_dir.mkdir(exist_ok=True)
    safe_name = f"template_{uuid.uuid4()}{ext}"
    save_path = templates_dir / safe_name
    with open(save_path, "wb") as f:
        f.write(content)

    # Create or find template record
    template = db.query(SowTemplate).filter(
        SowTemplate.organization_id == current_user.organization_id,
        SowTemplate.name == clean_name,
    ).first()

    if not template:
        template = SowTemplate(
            organization_id=current_user.organization_id,
            name=clean_name,
            description=description,
        )
        db.add(template)
        db.flush()

    # Determine version number
    existing_count = db.query(SowTemplateVersion).filter(
        SowTemplateVersion.template_id == template.id
    ).count()
    version_number = f"v{existing_count + 1}.0"

    # Extract template structure (supports docx, pdf, txt, or any format)
    structure = {"placeholders": [], "headings": [], "tables": []}
    if ext == ".docx":
        try:
            structure = extract_template_structure(str(save_path))
        except Exception as e:
            logger.warning(f"Template docx structure extraction note: {e}")
            structure = {"placeholders": [], "headings": [], "tables": [], "note": str(e)}
    elif ext == ".pdf":
        try:
            from app.document.extractor import extract_pdf
            sections, _ = extract_pdf(str(save_path))
            structure = {
                "headings": [{"text": s.get("heading") or f"Section {i+1}", "level": 1} for i, s in enumerate(sections) if s.get("heading")],
                "placeholders": [],
                "tables": [],
            }
        except Exception as e:
            logger.warning(f"Template pdf structure extraction note: {e}")
            structure = {"placeholders": [], "headings": [], "tables": [], "note": str(e)}

    # Build default placeholder map from discovered placeholders
    placeholder_map = {}
    for ph in structure.get("placeholders", []):
        placeholder_map[f"{{{{{ph}}}}}"] = ph.lower()

    # Archive previous active versions across org so new upload takes effect immediately
    old_active = (
        db.query(SowTemplateVersion)
        .join(SowTemplate, SowTemplateVersion.template_id == SowTemplate.id)
        .filter(
            SowTemplate.organization_id == current_user.organization_id,
            SowTemplateVersion.status == TemplateStatus.ACTIVE,
        )
        .all()
    )
    for oav in old_active:
        oav.status = TemplateStatus.ARCHIVED
    db.flush()

    version = SowTemplateVersion(
        template_id=template.id,
        version_number=version_number,
        storage_path=str(save_path),
        original_filename=file.filename,
        status=TemplateStatus.ACTIVE,
        extracted_structure=structure,
        placeholder_map=placeholder_map,
        section_map={},
        change_summary=change_summary or f"Uploaded and activated {file.filename}",
        published_by=current_user.id,
        published_at=datetime.now(timezone.utc),
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    db.refresh(template)

    logger.info(f"Master template uploaded and activated: {clean_name} v{version_number} at {save_path}")
    return {"template": _template_dict(template), "version": _version_dict(version)}


@router.post("/versions/{version_id}/publish")
def publish_template_version(
    version_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Publish a template version as the active version."""
    version = db.query(SowTemplateVersion).filter(
        SowTemplateVersion.id == version_id
    ).first()
    if not version:
        raise HTTPException(404, "Template version not found.")

    # Verify org access via template
    template = db.query(SowTemplate).filter(SowTemplate.id == version.template_id).first()
    if not template or template.organization_id != current_user.organization_id:
        raise HTTPException(403, "Access denied.")

    # Archive other active versions across org
    other_active = (
        db.query(SowTemplateVersion)
        .join(SowTemplate, SowTemplateVersion.template_id == SowTemplate.id)
        .filter(
            SowTemplate.organization_id == current_user.organization_id,
            SowTemplateVersion.id != version_id,
            SowTemplateVersion.status == TemplateStatus.ACTIVE,
        )
        .all()
    )
    for oav in other_active:
        oav.status = TemplateStatus.ARCHIVED
    db.flush()

    version.status = TemplateStatus.ACTIVE
    version.published_by = current_user.id
    version.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(version)
    return _version_dict(version)


@router.patch("/versions/{version_id}/mapping")
def update_section_mapping(
    version_id: str,
    section_map: dict,
    placeholder_map: dict,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update section and placeholder mappings for a template version."""
    version = db.query(SowTemplateVersion).filter(
        SowTemplateVersion.id == version_id
    ).first()
    if not version:
        raise HTTPException(404, "Template version not found.")

    template = db.query(SowTemplate).filter(SowTemplate.id == version.template_id).first()
    if not template or template.organization_id != current_user.organization_id:
        raise HTTPException(403, "Access denied.")

    version.section_map = section_map
    version.placeholder_map = placeholder_map
    db.commit()
    db.refresh(version)
    return _version_dict(version)


@router.get("/active")
def get_active_template(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the currently active template version for this organisation."""
    version = db.query(SowTemplateVersion).join(SowTemplate).filter(
        SowTemplate.organization_id == current_user.organization_id,
        SowTemplateVersion.status == TemplateStatus.ACTIVE,
    ).order_by(SowTemplateVersion.published_at.desc()).first()

    if not version:
        return {"active": False, "message": "No active template. Please upload and publish a master template."}

    return {"active": True, "version": _version_dict(version)}


@router.delete("/{template_id}")
def delete_template(
    template_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a master template, clear foreign key references, and delete files from disk."""
    template = db.query(SowTemplate).filter(
        SowTemplate.id == template_id,
        SowTemplate.organization_id == current_user.organization_id,
    ).first()
    if not template:
        raise HTTPException(404, "Template not found.")

    version_ids = [v.id for v in (template.versions or [])]
    if version_ids:
        # Clear foreign key references on projects and sow_documents
        from app.db.models import Project, SowDocument
        db.query(Project).filter(Project.active_template_id.in_(version_ids)).update(
            {"active_template_id": None}, synchronize_session=False
        )
        db.query(SowDocument).filter(SowDocument.template_version_id.in_(version_ids)).update(
            {"template_version_id": None}, synchronize_session=False
        )

    # Delete physical files
    backend_base = Path(__file__).resolve().parent.parent.parent.parent
    for version in (template.versions or []):
        if version.storage_path:
            candidates = [
                Path(version.storage_path),
                backend_base / version.storage_path,
                backend_base / "templates" / Path(version.storage_path).name,
            ]
            for c in candidates:
                # Do not delete the fallback seeded master template from disk
                if c.exists() and c.is_file() and "Leskode_Master_SOW_Template.docx" not in c.name:
                    try:
                        os.remove(c)
                        logger.info(f"Removed template file: {c}")
                    except Exception as e:
                        logger.warning(f"Failed to remove template file {c}: {e}")

    was_active = any(v.status == TemplateStatus.ACTIVE for v in (template.versions or []))

    db.delete(template)
    db.commit()

    # If the active template was deleted, activate the most recent available template version if any
    if was_active:
        remaining_version = db.query(SowTemplateVersion).join(
            SowTemplate, SowTemplateVersion.template_id == SowTemplate.id
        ).filter(
            SowTemplate.organization_id == current_user.organization_id,
        ).order_by(SowTemplateVersion.created_at.desc()).first()
        if remaining_version:
            remaining_version.status = TemplateStatus.ACTIVE
            db.commit()

    return {"message": "Master template deleted successfully", "deleted_id": template_id}
