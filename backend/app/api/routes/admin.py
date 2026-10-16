"""Admin routes — user management, audit logs, AI config."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_role
from app.db.database import get_db
from app.db.models import UserProfile, UserRole, AuditLog, Organization
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/users")
def list_users(
    current_user: UserProfile = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    users = db.query(UserProfile).filter(
        UserProfile.organization_id == current_user.organization_id
    ).all()
    return [
        {
            "id": u.id, "email": u.email, "full_name": u.full_name,
            "role": u.role.value if u.role else "consultant",
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    role: str,
    current_user: UserProfile = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    user = db.query(UserProfile).filter(
        UserProfile.id == user_id,
        UserProfile.organization_id == current_user.organization_id,
    ).first()
    if not user:
        raise HTTPException(404, "User not found.")
    for r in UserRole:
        if r.value == role:
            user.role = r
            break
    else:
        raise HTTPException(400, f"Invalid role: {role}")
    db.commit()
    return {"id": user.id, "role": user.role.value}


@router.get("/audit-logs")
def get_audit_logs(
    skip: int = 0,
    limit: int = 50,
    current_user: UserProfile = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    logs = db.query(AuditLog).filter(
        AuditLog.organization_id == current_user.organization_id
    ).order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
    return [
        {
            "id": l.id, "action": l.action, "resource_type": l.resource_type,
            "resource_id": l.resource_id, "details": l.details,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]


@router.get("/ai-config")
def get_ai_config(current_user: UserProfile = Depends(require_role(UserRole.ADMIN))):
    return {
        "provider": settings.ai_provider,
        "configured": settings.ai_configured,
        "model": {
            "openai": settings.openai_model,
            "anthropic": settings.anthropic_model,
            "google": settings.google_model,
            "ollama": settings.ollama_model,
        }.get(settings.ai_provider),
        "available_providers": ["openai", "anthropic", "google", "ollama"],
    }


@router.get("/workspace")
def get_workspace(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    org = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()
    if not org:
        raise HTTPException(404, "Organisation not found.")
    return {
        "id": org.id, "name": org.name, "slug": org.slug,
        "settings": org.settings or {},
        "created_at": org.created_at.isoformat() if org.created_at else None,
    }
