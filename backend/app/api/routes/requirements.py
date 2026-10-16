"""Requirements analysis routes."""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_project_access
from app.db.database import get_db
from app.db.models import (
    UserProfile, Requirement, ExtractedSection, UploadedDocument,
    Project, ProjectStatus, RequirementStatus, RequirementCategory
)
from app.ai.pipeline import extract_requirements_from_text, AINotConfiguredError, AIServiceError

router = APIRouter()
logger = logging.getLogger(__name__)


class RequirementCreate(BaseModel):
    title: str
    description: str
    category: Optional[str] = "Standard Requirement"
    suggested_zoho_module: Optional[str] = None
    review_status: Optional[str] = "Needs Review"
    consultant_comments: Optional[str] = None


class RequirementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    suggested_zoho_module: Optional[str] = None
    review_status: Optional[str] = None
    consultant_comments: Optional[str] = None


def _req_dict(r: Requirement) -> dict:
    return {
        "id": r.id,
        "project_id": r.project_id,
        "req_id": r.req_id,
        "title": r.title,
        "description": r.description,
        "category": r.category.value if r.category else None,
        "source_filename": r.source_filename,
        "source_page": r.source_page,
        "source_heading": r.source_heading,
        "supporting_excerpt": r.supporting_excerpt,
        "suggested_zoho_module": r.suggested_zoho_module,
        "confidence": r.confidence,
        "is_ai_generated": r.is_ai_generated,
        "review_status": r.review_status.value if r.review_status else "Needs Review",
        "consultant_comments": r.consultant_comments,
        "conflict_ids": r.conflict_ids or [],
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _analyse_in_background(project_id: str, doc_ids: List[str]):
    """Run AI requirement analysis in the background."""
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        project.status = ProjectStatus.ANALYSING
        db.commit()

        # Count existing requirements
        existing_count = db.query(Requirement).filter(
            Requirement.project_id == project_id
        ).count()

        # Process each document
        for doc_id in doc_ids:
            doc = db.query(UploadedDocument).filter(
                UploadedDocument.id == doc_id,
                UploadedDocument.project_id == project_id,
            ).first()
            if not doc or doc.is_excluded:
                continue

            sections = db.query(ExtractedSection).filter(
                ExtractedSection.document_id == doc_id,
                ExtractedSection.is_excluded == False,
            ).order_by(ExtractedSection.section_order).all()

            if not sections:
                continue

            # Process in chunks to handle large documents
            chunk_size = 3
            for i in range(0, len(sections), chunk_size):
                chunk = sections[i:i + chunk_size]
                combined_text = "\n\n".join([
                    f"[{s.heading or 'Section'}]\n{s.content}"
                    for s in chunk
                ])
                page_hint = f"{chunk[0].page_number or 'N/A'} - {chunk[-1].page_number or 'N/A'}"

                try:
                    result = extract_requirements_from_text(
                        combined_text,
                        doc.original_filename,
                        page_hint,
                        existing_count,
                    )
                except (AINotConfiguredError, AIServiceError) as e:
                    logger.error(f"AI analysis failed: {e}")
                    project.status = ProjectStatus.REQUIREMENTS_REVIEW
                    db.commit()
                    return

                # Save requirements
                for req_data in result.get("requirements", []):
                    # Skip duplicates
                    dup = db.query(Requirement).filter(
                        Requirement.project_id == project_id,
                        Requirement.req_id == req_data.get("req_id"),
                    ).first()
                    if dup:
                        continue

                    # Find source section
                    source_section = None
                    if chunk:
                        source_section = chunk[0]

                    req = Requirement(
                        project_id=project_id,
                        source_section_id=source_section.id if source_section else None,
                        req_id=req_data.get("req_id", f"REQ-{existing_count + 1:03d}"),
                        title=req_data.get("title", "Untitled Requirement"),
                        description=req_data.get("description", ""),
                        category=_parse_category(req_data.get("category")),
                        source_filename=doc.original_filename,
                        source_page=chunk[0].page_number if chunk else None,
                        source_heading=chunk[0].heading if chunk else None,
                        supporting_excerpt=req_data.get("supporting_excerpt"),
                        suggested_zoho_module=req_data.get("suggested_zoho_module"),
                        confidence=req_data.get("confidence", 0.7),
                        is_ai_generated=req_data.get("is_ai_generated", True),
                        review_status=RequirementStatus.NEEDS_REVIEW,
                        conflict_ids=[],
                    )
                    db.add(req)
                    existing_count += 1

                db.commit()

        project.status = ProjectStatus.REQUIREMENTS_REVIEW
        db.commit()
        logger.info(f"Analysis complete for project {project_id}: {existing_count} requirements")

    except Exception as e:
        logger.error(f"Analysis failed for project {project_id}: {e}", exc_info=True)
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = ProjectStatus.REQUIREMENTS_REVIEW
            db.commit()
    finally:
        db.close()


def _parse_category(cat_str: Optional[str]) -> Optional[RequirementCategory]:
    if not cat_str:
        return RequirementCategory.FUNCTIONAL
    for cat in RequirementCategory:
        if cat.value.lower() == cat_str.lower():
            return cat
    return RequirementCategory.FUNCTIONAL


@router.post("/{project_id}/analyse")
def trigger_analysis(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger AI requirement analysis for all uploaded documents."""
    project = require_project_access(project_id, current_user, db)
    docs = db.query(UploadedDocument).filter(
        UploadedDocument.project_id == project_id,
        UploadedDocument.is_excluded == False,
    ).all()

    if not docs:
        raise HTTPException(400, "No documents uploaded. Please upload at least one requirement document first.")

    extracted_docs = [d for d in docs if d.status.value == "extracted"]
    if not extracted_docs:
        raise HTTPException(400, "No documents have been successfully extracted yet. Please wait for extraction to complete.")

    doc_ids = [d.id for d in extracted_docs]
    background_tasks.add_task(_analyse_in_background, project_id, doc_ids)
    return {"message": f"Analysis started for {len(doc_ids)} document(s).", "doc_count": len(doc_ids)}


@router.get("/{project_id}")
def list_requirements(
    project_id: str,
    category: Optional[str] = None,
    status: Optional[str] = None,
    is_ai: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    q = db.query(Requirement).filter(Requirement.project_id == project_id)

    if category:
        q = q.filter(Requirement.category == category)
    if status:
        q = q.filter(Requirement.review_status == status)
    if is_ai is not None:
        q = q.filter(Requirement.is_ai_generated == is_ai)
    if search:
        q = q.filter(
            (Requirement.title.ilike(f"%{search}%")) |
            (Requirement.description.ilike(f"%{search}%"))
        )

    total = q.count()
    reqs = q.order_by(Requirement.req_id).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [_req_dict(r) for r in reqs],
    }


@router.post("/{project_id}", status_code=201)
def create_requirement(
    project_id: str,
    req_in: RequirementCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    count = db.query(Requirement).filter(Requirement.project_id == project_id).count()
    req = Requirement(
        project_id=project_id,
        req_id=f"REQ-{count + 1:03d}",
        title=req_in.title,
        description=req_in.description,
        category=_parse_category(req_in.category),
        suggested_zoho_module=req_in.suggested_zoho_module,
        review_status=RequirementStatus.APPROVED_BY_CONSULTANT if req_in.review_status == "Approved" else RequirementStatus.NEEDS_REVIEW,
        consultant_comments=req_in.consultant_comments,
        is_ai_generated=False,
        confidence=1.0,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _req_dict(req)


@router.patch("/{project_id}/{req_id}")
def update_requirement(
    project_id: str,
    req_id: str,
    update: RequirementUpdate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    req = db.query(Requirement).filter(
        Requirement.id == req_id,
        Requirement.project_id == project_id,
    ).first()
    if not req:
        raise HTTPException(404, "Requirement not found.")

    data = update.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "review_status" and v:
            for rs in RequirementStatus:
                if rs.value == v:
                    setattr(req, k, rs)
                    break
        elif k == "category" and v:
            setattr(req, k, _parse_category(v))
        else:
            setattr(req, k, v)

    db.commit()
    db.refresh(req)
    return _req_dict(req)


@router.delete("/{project_id}/{req_id}", status_code=204)
def delete_requirement(
    project_id: str,
    req_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    req = db.query(Requirement).filter(
        Requirement.id == req_id,
        Requirement.project_id == project_id,
    ).first()
    if not req:
        raise HTTPException(404, "Requirement not found.")
    db.delete(req)
    db.commit()
