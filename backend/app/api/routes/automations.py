"""Automations routes."""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_project_access
from app.db.database import get_db
from app.db.models import (
    UserProfile, AutomationItem, FeasibilityStatus, TaskSource,
    Requirement, ProjectModuleMapping
)
from app.ai.pipeline import generate_automation_matrix

router = APIRouter()
logger = logging.getLogger(__name__)


class AutomationCreate(BaseModel):
    name: str
    business_objective: Optional[str] = None
    zoho_module: Optional[str] = None
    trigger_event: Optional[str] = None
    trigger_conditions: Optional[str] = None
    action_performed: Optional[str] = None
    recipient_role: Optional[str] = None
    timing: Optional[str] = None
    exception_conditions: Optional[str] = None
    failure_handling: Optional[str] = None
    escalation_conditions: Optional[str] = None
    linked_requirement_ids: Optional[List[str]] = []
    uat_scenario: Optional[str] = None
    pending_questions: Optional[str] = None


class AutomationUpdate(AutomationCreate):
    is_approved: Optional[bool] = None
    feasibility_status: Optional[str] = None


def _auto_dict(a: AutomationItem) -> dict:
    return {
        "id": a.id,
        "project_id": a.project_id,
        "automation_id_label": a.automation_id_label,
        "name": a.name,
        "business_objective": a.business_objective,
        "zoho_module": a.zoho_module,
        "trigger_event": a.trigger_event,
        "trigger_conditions": a.trigger_conditions,
        "action_performed": a.action_performed,
        "recipient_role": a.recipient_role,
        "timing": a.timing,
        "exception_conditions": a.exception_conditions,
        "failure_handling": a.failure_handling,
        "escalation_conditions": a.escalation_conditions,
        "linked_requirement_ids": a.linked_requirement_ids or [],
        "dependencies": a.dependencies or [],
        "feasibility_status": a.feasibility_status.value if a.feasibility_status else "Pending Assessment",
        "uat_scenario": a.uat_scenario,
        "pending_questions": a.pending_questions,
        "is_approved": a.is_approved,
        "source": a.source.value if a.source else "AI Recommendation",
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _gen_automations_bg(project_id: str):
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        requirements = db.query(Requirement).filter(
            Requirement.project_id == project_id
        ).limit(40).all()

        mappings = db.query(ProjectModuleMapping).filter(
            ProjectModuleMapping.project_id == project_id,
            ProjectModuleMapping.is_approved == True,
        ).all()
        module_names = [m.module.display_name for m in mappings if m.module]

        req_dicts = [{"req_id": r.req_id, "title": r.title, "description": r.description} for r in requirements]
        result = generate_automation_matrix(req_dicts, module_names)

        existing_count = db.query(AutomationItem).filter(AutomationItem.project_id == project_id).count()

        for i, auto_data in enumerate(result.get("automations", [])):
            auto = AutomationItem(
                project_id=project_id,
                automation_id_label=auto_data.get("automation_id_label", f"AUTO-{existing_count + i + 1:03d}"),
                name=auto_data.get("name", "Automation"),
                business_objective=auto_data.get("business_objective"),
                zoho_module=auto_data.get("zoho_module"),
                trigger_event=auto_data.get("trigger_event"),
                trigger_conditions=auto_data.get("trigger_conditions"),
                action_performed=auto_data.get("action_performed"),
                recipient_role=auto_data.get("recipient_role"),
                timing=auto_data.get("timing"),
                exception_conditions=auto_data.get("exception_conditions"),
                failure_handling=auto_data.get("failure_handling"),
                escalation_conditions=auto_data.get("escalation_conditions"),
                linked_requirement_ids=auto_data.get("linked_requirement_ids", []),
                feasibility_status=FeasibilityStatus.PENDING,
                uat_scenario=auto_data.get("uat_scenario"),
                pending_questions=str(auto_data.get("pending_questions", [])),
                is_approved=False,
                source=TaskSource.AI_RECOMMENDATION,
            )
            db.add(auto)

        db.commit()
        logger.info(f"Automations generated for {project_id}")
    except Exception as e:
        logger.error(f"Automation generation failed: {e}", exc_info=True)
    finally:
        db.close()


@router.post("/{project_id}/generate")
def generate_automations(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    background_tasks.add_task(_gen_automations_bg, project_id)
    return {"message": "Automation generation started."}


@router.get("/{project_id}")
def list_automations(
    project_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    autos = db.query(AutomationItem).filter(
        AutomationItem.project_id == project_id
    ).order_by(AutomationItem.created_at).all()
    return [_auto_dict(a) for a in autos]


@router.post("/{project_id}", status_code=201)
def create_automation(
    project_id: str,
    req: AutomationCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    count = db.query(AutomationItem).filter(AutomationItem.project_id == project_id).count()
    auto = AutomationItem(
        project_id=project_id,
        automation_id_label=f"AUTO-{count + 1:03d}",
        source=TaskSource.CONSULTANT_ADDITION,
        is_approved=True,
        feasibility_status=FeasibilityStatus.PENDING,
        **req.model_dump(),
    )
    db.add(auto)
    db.commit()
    db.refresh(auto)
    return _auto_dict(auto)


@router.patch("/{project_id}/{auto_id}")
def update_automation(
    project_id: str,
    auto_id: str,
    update: AutomationUpdate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    auto = db.query(AutomationItem).filter(
        AutomationItem.id == auto_id,
        AutomationItem.project_id == project_id,
    ).first()
    if not auto:
        raise HTTPException(404, "Automation not found.")
    data = update.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "feasibility_status" and v:
            for fs in FeasibilityStatus:
                if fs.value == v:
                    setattr(auto, k, fs)
                    break
        else:
            setattr(auto, k, v)
    db.commit()
    db.refresh(auto)
    return _auto_dict(auto)


@router.delete("/{project_id}/{auto_id}", status_code=204)
def delete_automation(
    project_id: str,
    auto_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    auto = db.query(AutomationItem).filter(
        AutomationItem.id == auto_id,
        AutomationItem.project_id == project_id,
    ).first()
    if not auto:
        raise HTTPException(404, "Automation not found.")
    db.delete(auto)
    db.commit()
