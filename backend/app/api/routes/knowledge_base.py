"""Knowledge base routes."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.db.models import UserProfile, KnowledgeBaseRecord

router = APIRouter()


class KBCreate(BaseModel):
    category: str
    title: str
    content: str
    tags: Optional[List[str]] = []
    zoho_modules: Optional[List[str]] = []


@router.get("")
def list_kb(
    category: Optional[str] = None,
    search: Optional[str] = None,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(KnowledgeBaseRecord).filter(
        KnowledgeBaseRecord.organization_id == current_user.organization_id,
        KnowledgeBaseRecord.is_approved == True,
    )
    if category:
        q = q.filter(KnowledgeBaseRecord.category == category)
    if search:
        q = q.filter(
            (KnowledgeBaseRecord.title.ilike(f"%{search}%")) |
            (KnowledgeBaseRecord.content.ilike(f"%{search}%"))
        )
    return [
        {
            "id": r.id, "category": r.category, "title": r.title,
            "content": r.content, "tags": r.tags, "zoho_modules": r.zoho_modules,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in q.order_by(KnowledgeBaseRecord.created_at.desc()).all()
    ]


@router.post("", status_code=201)
def create_kb(
    req: KBCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = KnowledgeBaseRecord(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        is_approved=True,
        **req.model_dump(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "title": record.title, "category": record.category}


@router.delete("/{record_id}", status_code=204)
def delete_kb(record_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(KnowledgeBaseRecord).filter(
        KnowledgeBaseRecord.id == record_id,
        KnowledgeBaseRecord.organization_id == current_user.organization_id,
    ).first()
    if not record:
        raise HTTPException(404, "Record not found.")
    db.delete(record)
    db.commit()
