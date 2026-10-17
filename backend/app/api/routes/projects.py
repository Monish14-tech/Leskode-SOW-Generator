"""Projects CRUD routes."""
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_project_access
from app.db.database import get_db
from app.db.models import (
    Project, UserProfile, ProjectStatus, UploadedDocument,
    Requirement, SowDocument
)

router = APIRouter()
logger = logging.getLogger(__name__)


class ProjectCreate(BaseModel):
    client_name: str
    project_name: str
    prepared_by: Optional[str] = "Leskode Solutions Team"
    industry: Optional[str] = None
    description: Optional[str] = None
    existing_systems: Optional[str] = None
    proposed_zoho_apps: Optional[List[str]] = []
    target_start_date: Optional[datetime] = None
    target_end_date: Optional[datetime] = None
    notes: Optional[str] = None


class ProjectUpdate(ProjectCreate):
    status: Optional[ProjectStatus] = None


def _project_dict(p: Project, include_stats: bool = False) -> dict:
    d = {
        "id": p.id,
        "client_name": p.client_name,
        "project_name": p.project_name,
        "prepared_by": getattr(p, "prepared_by", None) or "Leskode Solutions Team",
        "industry": p.industry,
        "description": p.description,
        "existing_systems": p.existing_systems,
        "proposed_zoho_apps": p.proposed_zoho_apps or [],
        "status": p.status.value if p.status else "Draft",
        "target_start_date": p.target_start_date.isoformat() if p.target_start_date else None,
        "target_end_date": p.target_end_date.isoformat() if p.target_end_date else None,
        "notes": p.notes,
        "owner_id": p.owner_id,
        "organization_id": p.organization_id,
        "active_template_id": p.active_template_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }
    if include_stats:
        d["stats"] = {
            "document_count": len(p.documents) if p.documents else 0,
            "requirement_count": len(p.requirements) if p.requirements else 0,
            "sow_count": len(p.sow_documents) if p.sow_documents else 0,
        }
    return d


@router.get("")
@router.get("/")
def list_projects(
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Project).filter(Project.organization_id == current_user.organization_id)
    if status:
        q = q.filter(Project.status == status)
    if search:
        q = q.filter(
            (Project.client_name.ilike(f"%{search}%")) |
            (Project.project_name.ilike(f"%{search}%"))
        )
    total = q.count()
    projects = q.order_by(Project.created_at.desc()).offset(skip).limit(limit).all()
    return {
        "total": total,
        "items": [_project_dict(p, include_stats=True) for p in projects],
        "skip": skip,
        "limit": limit,
    }


@router.post("", status_code=201)
@router.post("/", status_code=201)
def create_project(
    req: ProjectCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = Project(
        organization_id=current_user.organization_id,
        owner_id=current_user.id,
        client_name=req.client_name,
        project_name=req.project_name,
        prepared_by=req.prepared_by or "Leskode Solutions Team",
        industry=req.industry,
        description=req.description,
        existing_systems=req.existing_systems,
        proposed_zoho_apps=req.proposed_zoho_apps or [],
        target_start_date=req.target_start_date,
        target_end_date=req.target_end_date,
        notes=req.notes,
        status=ProjectStatus.DRAFT,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info(f"Created project {project.id} for org {current_user.organization_id}")
    return _project_dict(project)


@router.get("/{project_id}")
def get_project(
    project_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = require_project_access(project_id, current_user, db)
    return _project_dict(project, include_stats=True)


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    req: ProjectUpdate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = require_project_access(project_id, current_user, db)
    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return _project_dict(project)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = require_project_access(project_id, current_user, db)
    db.delete(project)
    db.commit()


@router.get("/stats/dashboard")
def dashboard_stats(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dashboard statistics for the current user's organization."""
    org_id = current_user.organization_id
    all_projects = db.query(Project).filter(Project.organization_id == org_id).all()

    status_counts = {}
    for p in all_projects:
        s = p.status.value if p.status else "Draft"
        status_counts[s] = status_counts.get(s, 0) + 1

    recent = db.query(Project).filter(
        Project.organization_id == org_id
    ).order_by(Project.updated_at.desc()).limit(5).all()

    pending_clarifications = sum(
        db.query(Requirement).filter(
            Requirement.project_id == p.id,
            Requirement.review_status == "Pending Client Clarification",
        ).count()
        for p in all_projects
    )

    return {
        "total_projects": len(all_projects),
        "status_counts": status_counts,
        "draft_sows": status_counts.get("SOW Draft", 0),
        "awaiting_review": status_counts.get("Under Review", 0),
        "approved": status_counts.get("Approved", 0),
        "pending_clarifications": pending_clarifications,
        "recent_projects": [_project_dict(p) for p in recent],
    }
