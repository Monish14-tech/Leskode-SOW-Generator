"""Validation routes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.auth import get_current_user, require_project_access
from app.db.database import get_db
from app.db.models import (
    UserProfile, Requirement, ScopeTask, AutomationItem, IntegrationItem,
    ClarificationQuestion, ValidationResult, ValidationLevel, RequirementStatus,
    ClarificationStatus, Project, ProjectStatus
)

router = APIRouter()


@router.post("/{project_id}/run")
def run_validation(
    project_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run scope validation checks and save the result."""
    project = require_project_access(project_id, current_user, db)

    requirements = db.query(Requirement).filter(Requirement.project_id == project_id).all()
    tasks = db.query(ScopeTask).filter(ScopeTask.project_id == project_id).all()
    automations = db.query(AutomationItem).filter(AutomationItem.project_id == project_id).all()
    integrations = db.query(IntegrationItem).filter(IntegrationItem.project_id == project_id).all()
    clarifications = db.query(ClarificationQuestion).filter(ClarificationQuestion.project_id == project_id).all()

    # Build coverage map
    covered_req_ids = set()
    for t in tasks:
        covered_req_ids.update(t.requirement_ids or [])
    for a in automations:
        covered_req_ids.update(a.linked_requirement_ids or [])
    for i in integrations:
        covered_req_ids.update(i.linked_requirement_ids or [])

    confirmed_reqs = [r for r in requirements if r.review_status == RequirementStatus.APPROVED_BY_CONSULTANT]
    unmapped = [r for r in requirements if r.req_id not in covered_req_ids and r.review_status != RequirementStatus.REJECTED]
    open_clarifications = [c for c in clarifications if c.status == ClarificationStatus.OPEN]
    pending_ai_approvals = [t for t in tasks if not t.is_approved]
    missing_acceptance = [t for t in tasks if t.is_approved and not t.acceptance_criteria]

    issues = []
    warnings = []

    for r in unmapped[:10]:
        issues.append(f"Requirement {r.req_id} ({r.title[:40]}) has no scope mapping.")

    for c in open_clarifications[:5]:
        warnings.append(f"Clarification '{c.question[:60]}...' is still open.")

    if pending_ai_approvals:
        warnings.append(f"{len(pending_ai_approvals)} AI-generated tasks are awaiting consultant approval.")

    if missing_acceptance:
        warnings.append(f"{len(missing_acceptance)} approved tasks are missing acceptance criteria.")

    if not requirements:
        issues.append("No requirements have been extracted. Please upload and analyse documents first.")

    # Determine overall level
    if issues:
        level = ValidationLevel.FAIL
    elif warnings:
        level = ValidationLevel.WARNING
    else:
        level = ValidationLevel.PASS

    result = ValidationResult(
        project_id=project_id,
        total_requirements=len(requirements),
        confirmed_requirements=len(confirmed_reqs),
        unmapped_requirements=len(unmapped),
        pending_clarifications=len(open_clarifications),
        pending_ai_approvals=len(pending_ai_approvals),
        feasibility_checks_needed=sum(1 for t in tasks if not t.is_approved),
        missing_acceptance_criteria=len(missing_acceptance),
        template_mapping_issues=0,
        overall_level=level,
        issues=issues,
        warnings=warnings,
        consultant_acknowledged=False,
    )
    db.add(result)

    if level == ValidationLevel.PASS:
        project.status = ProjectStatus.READY_FOR_SOW

    db.commit()
    db.refresh(result)

    return {
        "id": result.id,
        "project_id": result.project_id,
        "total_requirements": result.total_requirements,
        "confirmed_requirements": result.confirmed_requirements,
        "unmapped_requirements": result.unmapped_requirements,
        "pending_clarifications": result.pending_clarifications,
        "pending_ai_approvals": result.pending_ai_approvals,
        "missing_acceptance_criteria": result.missing_acceptance_criteria,
        "overall_level": result.overall_level.value,
        "issues": result.issues,
        "warnings": result.warnings,
        "consultant_acknowledged": result.consultant_acknowledged,
        "run_at": result.run_at.isoformat() if result.run_at else None,
    }


@router.post("/{project_id}/acknowledge")
def acknowledge_validation(
    project_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Consultant acknowledges outstanding issues and proceeds to SOW generation."""
    require_project_access(project_id, current_user, db)
    result = db.query(ValidationResult).filter(
        ValidationResult.project_id == project_id
    ).order_by(ValidationResult.run_at.desc()).first()

    if not result:
        raise HTTPException(400, "Run validation first before acknowledging.")

    result.consultant_acknowledged = True
    result.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    return {"acknowledged": True, "message": "Acknowledged. You may now proceed to SOW generation."}


@router.get("/{project_id}/latest")
def get_latest_validation(
    project_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    result = db.query(ValidationResult).filter(
        ValidationResult.project_id == project_id
    ).order_by(ValidationResult.run_at.desc()).first()
    if not result:
        return {"has_validation": False}
    return {
        "has_validation": True,
        "id": result.id,
        "total_requirements": result.total_requirements,
        "confirmed_requirements": result.confirmed_requirements,
        "unmapped_requirements": result.unmapped_requirements,
        "pending_clarifications": result.pending_clarifications,
        "pending_ai_approvals": result.pending_ai_approvals,
        "missing_acceptance_criteria": result.missing_acceptance_criteria,
        "overall_level": result.overall_level.value,
        "issues": result.issues,
        "warnings": result.warnings,
        "consultant_acknowledged": result.consultant_acknowledged,
        "run_at": result.run_at.isoformat() if result.run_at else None,
    }
