"""
Document upload, extraction, and management routes.
"""
import os
import uuid
import logging
from typing import Optional
from datetime import datetime, timezone
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.auth import get_current_user, require_project_access
from app.db.database import get_db
from app.db.models import (
    UserProfile, UploadedDocument, ExtractedSection, Project,
    DocStatus, ProjectStatus
)
from app.document.extractor import extract_document, ExtractionError

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _doc_dict(doc: UploadedDocument) -> dict:
    return {
        "id": doc.id,
        "project_id": doc.project_id,
        "filename": doc.filename,
        "original_filename": doc.original_filename,
        "file_type": doc.file_type,
        "file_size_bytes": doc.file_size_bytes,
        "status": doc.status.value if doc.status else "uploaded",
        "extraction_method": doc.extraction_method,
        "extraction_error": doc.extraction_error,
        "page_count": doc.page_count,
        "sheet_names": doc.sheet_names or [],
        "ocr_performed": doc.ocr_performed,
        "is_excluded": doc.is_excluded,
        "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
        "extracted_at": doc.extracted_at.isoformat() if doc.extracted_at else None,
    }


def _section_dict(s: ExtractedSection) -> dict:
    return {
        "id": s.id,
        "document_id": s.document_id,
        "heading": s.heading,
        "content": s.content,
        "page_number": s.page_number,
        "sheet_name": s.sheet_name,
        "section_order": s.section_order,
        "is_excluded": s.is_excluded,
        "char_count": s.char_count,
    }


def _extract_in_background(doc_id: str, file_path: str, filename: str):
    """Background task to perform document extraction."""
    from app.db.database import SessionLocal
    from datetime import datetime
    db = SessionLocal()
    try:
        doc = db.query(UploadedDocument).filter(UploadedDocument.id == doc_id).first()
        if not doc:
            return

        doc.status = DocStatus.EXTRACTING
        db.commit()

        result = extract_document(file_path, filename)

        # Save sections
        for sec_data in result["sections"]:
            section = ExtractedSection(
                document_id=doc_id,
                heading=sec_data.get("heading"),
                content=sec_data.get("content", ""),
                page_number=sec_data.get("page_number"),
                sheet_name=sec_data.get("sheet_name"),
                section_order=sec_data.get("section_order", 0),
                char_count=sec_data.get("char_count", 0),
                is_excluded=False,
            )
            db.add(section)

        doc.status = DocStatus.EXTRACTED
        doc.extraction_method = result["extraction_method"]
        doc.page_count = result["page_count"]
        doc.sheet_names = result.get("sheet_names", [])
        doc.ocr_performed = False
        doc.extracted_at = datetime.now(timezone.utc)

        # Update project status
        project = db.query(Project).filter(Project.id == doc.project_id).first()
        if project and project.status == ProjectStatus.DRAFT:
            project.status = ProjectStatus.DOCUMENTS_UPLOADED

        db.commit()
        logger.info(f"Extraction complete for doc {doc_id}: {len(result['sections'])} sections")

    except ExtractionError as e:
        doc = db.query(UploadedDocument).filter(UploadedDocument.id == doc_id).first()
        if doc:
            doc.status = DocStatus.FAILED
            doc.extraction_error = str(e)
            db.commit()
        logger.error(f"Extraction failed for doc {doc_id}: {e}")
    except Exception as e:
        doc = db.query(UploadedDocument).filter(UploadedDocument.id == doc_id).first()
        if doc:
            doc.status = DocStatus.FAILED
            doc.extraction_error = f"Unexpected error: {e}"
            db.commit()
        logger.error(f"Unexpected extraction error for doc {doc_id}: {e}", exc_info=True)
    finally:
        db.close()


@router.post("/{project_id}/upload", status_code=201)
@router.post("/upload/{project_id}", status_code=201)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a requirement document and start extraction."""
    project = require_project_access(project_id, current_user, db)

    # Validate extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(ALLOWED_TYPES.keys())}",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb}MB.",
        )
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Save to disk
    safe_filename = f"{uuid.uuid4()}{ext}"
    save_path = UPLOAD_DIR / safe_filename
    with open(save_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = UploadedDocument(
        project_id=project_id,
        filename=safe_filename,
        original_filename=file.filename,
        file_type=ext,
        file_size_bytes=len(content),
        storage_path=str(save_path),
        status=DocStatus.UPLOADED,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Queue extraction
    if background_tasks:
        background_tasks.add_task(_extract_in_background, doc.id, str(save_path), file.filename)
    else:
        _extract_in_background(doc.id, str(save_path), file.filename)

    return _doc_dict(doc)


@router.get("/{project_id}")
def list_documents(
    project_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    docs = db.query(UploadedDocument).filter(
        UploadedDocument.project_id == project_id
    ).order_by(UploadedDocument.uploaded_at.desc()).all()
    return [_doc_dict(d) for d in docs]


@router.get("/{project_id}/sections")
def list_project_sections(
    project_id: str,
    document_id: Optional[str] = None,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    q = db.query(ExtractedSection).join(
        UploadedDocument, ExtractedSection.document_id == UploadedDocument.id
    ).filter(UploadedDocument.project_id == project_id)
    if document_id:
        q = q.filter(ExtractedSection.document_id == document_id)
    sections = q.order_by(ExtractedSection.section_order).all()
    return {"sections": [_section_dict(s) for s in sections]}


@router.get("/{project_id}/{doc_id}/sections")
def get_sections(
    project_id: str,
    doc_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.id == doc_id,
        UploadedDocument.project_id == project_id,
    ).first()
    if not doc:
        raise HTTPException(404, "Document not found.")

    sections = db.query(ExtractedSection).filter(
        ExtractedSection.document_id == doc_id
    ).order_by(ExtractedSection.section_order).all()

    return {
        "document": _doc_dict(doc),
        "sections": [_section_dict(s) for s in sections],
    }


@router.post("/{project_id}/{doc_id}/retry-extraction")
def retry_extraction(
    project_id: str,
    doc_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.id == doc_id,
        UploadedDocument.project_id == project_id,
    ).first()
    if not doc:
        raise HTTPException(404, "Document not found.")
    if doc.status not in [DocStatus.FAILED, DocStatus.EXTRACTED]:
        raise HTTPException(400, f"Cannot retry extraction for document in status: {doc.status.value}")

    # Clear existing sections
    db.query(ExtractedSection).filter(ExtractedSection.document_id == doc_id).delete()
    doc.status = DocStatus.UPLOADED
    doc.extraction_error = None
    db.commit()

    background_tasks.add_task(_extract_in_background, doc.id, doc.storage_path, doc.original_filename)
    return {"message": "Extraction queued.", "doc_id": doc_id}


@router.patch("/{project_id}/{doc_id}/exclude-section/{section_id}")
def toggle_section_exclusion(
    project_id: str,
    doc_id: str,
    section_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    section = db.query(ExtractedSection).filter(ExtractedSection.id == section_id).first()
    if not section:
        raise HTTPException(404, "Section not found.")
    section.is_excluded = not section.is_excluded
    db.commit()
    return {"section_id": section_id, "is_excluded": section.is_excluded}


@router.delete("/{project_id}/{doc_id}", status_code=204)
def delete_document(
    project_id: str,
    doc_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    doc = db.query(UploadedDocument).filter(
        UploadedDocument.id == doc_id,
        UploadedDocument.project_id == project_id,
    ).first()
    if not doc:
        raise HTTPException(404, "Document not found.")

    # Delete file from disk
    if doc.storage_path and os.path.exists(doc.storage_path):
        os.remove(doc.storage_path)

    db.delete(doc)
    db.commit()
