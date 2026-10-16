"""Tasks, automations, integrations, clarifications, assumptions routes."""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_project_access
from app.db.database import get_db
from app.db.models import (
    UserProfile, ScopeTask, TaskType, TaskSource,
    ProjectModuleMapping, Requirement, Project, ProjectStatus
)
from app.ai.pipeline import generate_scope_tasks

router = APIRouter()
logger = logging.getLogger(__name__)


class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    module_mapping_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    task_type: Optional[str] = "Configuration"
    priority: Optional[str] = "Medium"
    requirement_ids: Optional[List[str]] = []
    acceptance_criteria: Optional[str] = None
    deliverables: Optional[str] = None
    estimated_effort: Optional[str] = None
    proposed_owner: Optional[str] = None


class TaskUpdate(TaskCreate):
    is_approved: Optional[bool] = None
    source: Optional[str] = None


def _task_dict(t: ScopeTask) -> dict:
    return {
        "id": t.id,
        "project_id": t.project_id,
        "module_mapping_id": t.module_mapping_id,
        "parent_task_id": t.parent_task_id,
        "task_id_label": t.task_id_label,
        "name": t.name,
        "description": t.description,
        "task_type": t.task_type.value if t.task_type else None,
        "priority": t.priority,
        "source": t.source.value if t.source else "AI Recommendation",
        "requirement_ids": t.requirement_ids or [],
        "dependencies": t.dependencies or [],
        "estimated_effort": t.estimated_effort,
        "proposed_owner": t.proposed_owner,
        "acceptance_criteria": t.acceptance_criteria,
        "deliverables": t.deliverables,
        "exclusions": t.exclusions,
        "open_questions": t.open_questions,
        "is_approved": t.is_approved,
        "sort_order": t.sort_order,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _generate_tasks_bg(project_id: str, mapping_id: str):
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        mapping = db.query(ProjectModuleMapping).filter(
            ProjectModuleMapping.id == mapping_id
        ).first()
        if not mapping:
            return

        module_name = mapping.module.display_name if mapping.module else "Unknown"
        req_ids = mapping.linked_requirement_ids or []

        requirements = db.query(Requirement).filter(
            Requirement.id.in_(req_ids) if req_ids else Requirement.project_id == project_id
        ).limit(20).all()

        req_dicts = [{"req_id": r.req_id, "title": r.title, "description": r.description} for r in requirements]

        existing_count = db.query(ScopeTask).filter(ScopeTask.project_id == project_id).count()
        result = generate_scope_tasks(module_name, mapping.business_purpose or "", req_dicts, existing_count + 1)

        for task_data in result.get("tasks", []):
            task = ScopeTask(
                project_id=project_id,
                module_mapping_id=mapping_id,
                task_id_label=task_data.get("task_id_label"),
                name=task_data.get("name", "Task"),
                description=task_data.get("description"),
                task_type=_parse_task_type(task_data.get("task_type")),
                priority=task_data.get("priority", "Medium"),
                source=TaskSource.AI_RECOMMENDATION,
                requirement_ids=task_data.get("requirement_ids", []),
                acceptance_criteria=task_data.get("acceptance_criteria"),
                deliverables=task_data.get("deliverables"),
                is_approved=False,
            )
            db.add(task)
            db.flush()

            for sub_data in task_data.get("subtasks", []):
                subtask = ScopeTask(
                    project_id=project_id,
                    module_mapping_id=mapping_id,
                    parent_task_id=task.id,
                    task_id_label=sub_data.get("task_id_label"),
                    name=sub_data.get("name", "Subtask"),
                    description=sub_data.get("description"),
                    task_type=_parse_task_type(sub_data.get("task_type")),
                    source=TaskSource.AI_RECOMMENDATION,
                    is_approved=False,
                )
                db.add(subtask)

        db.commit()
        logger.info(f"Tasks generated for mapping {mapping_id}")
    except Exception as e:
        logger.error(f"Task generation failed: {e}", exc_info=True)
    finally:
        db.close()


def _parse_task_type(s: Optional[str]) -> Optional[TaskType]:
    if not s:
        return TaskType.CONFIGURATION
    for tt in TaskType:
        if tt.value.lower() == s.lower():
            return tt
    return TaskType.CONFIGURATION


class GenerateTasksRequest(BaseModel):
    module_mapping_id: Optional[str] = None


@router.post("/{project_id}/generate")
def generate_tasks_post(
    project_id: str,
    background_tasks: BackgroundTasks,
    body: Optional[GenerateTasksRequest] = None,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    mapping_id = body.module_mapping_id if body else None
    if mapping_id == "all":
        approved_maps = db.query(ProjectModuleMapping).filter(
            ProjectModuleMapping.project_id == project_id,
            ProjectModuleMapping.is_approved == True
        ).all()
        if not approved_maps:
            approved_maps = db.query(ProjectModuleMapping).filter(ProjectModuleMapping.project_id == project_id).all()
        for m in approved_maps:
            background_tasks.add_task(_generate_tasks_bg, project_id, m.id)
        return {"message": f"Task generation started for {len(approved_maps)} module(s)."}

    if not mapping_id:
        first_map = db.query(ProjectModuleMapping).filter(
            ProjectModuleMapping.project_id == project_id,
            ProjectModuleMapping.is_approved == True
        ).first()
        if not first_map:
            first_map = db.query(ProjectModuleMapping).filter(
                ProjectModuleMapping.project_id == project_id
            ).first()
        if first_map:
            mapping_id = first_map.id

    if not mapping_id:
        raise HTTPException(400, "No module mapping found for task generation")

    background_tasks.add_task(_generate_tasks_bg, project_id, mapping_id)
    return {"message": "Task generation started."}


@router.post("/{project_id}/generate/{mapping_id}")
def generate_tasks_for_module(
    project_id: str,
    mapping_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    background_tasks.add_task(_generate_tasks_bg, project_id, mapping_id)
    return {"message": "Task generation started."}


@router.get("/{project_id}")
def list_tasks(
    project_id: str,
    module_mapping_id: Optional[str] = None,
    parent_only: bool = False,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    q = db.query(ScopeTask).filter(ScopeTask.project_id == project_id)
    if module_mapping_id:
        q = q.filter(ScopeTask.module_mapping_id == module_mapping_id)
    if parent_only:
        q = q.filter(ScopeTask.parent_task_id == None)
    tasks = q.order_by(ScopeTask.sort_order, ScopeTask.created_at).all()
    return [_task_dict(t) for t in tasks]


@router.post("/{project_id}", status_code=201)
def create_task(
    project_id: str,
    req: TaskCreate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    count = db.query(ScopeTask).filter(ScopeTask.project_id == project_id).count()
    task = ScopeTask(
        project_id=project_id,
        module_mapping_id=req.module_mapping_id,
        parent_task_id=req.parent_task_id,
        task_id_label=f"T-{count + 1:03d}",
        name=req.name,
        description=req.description,
        task_type=_parse_task_type(req.task_type),
        priority=req.priority,
        source=TaskSource.CONSULTANT_ADDITION,
        requirement_ids=req.requirement_ids or [],
        acceptance_criteria=req.acceptance_criteria,
        deliverables=req.deliverables,
        estimated_effort=req.estimated_effort,
        proposed_owner=req.proposed_owner,
        is_approved=True,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_dict(task)


@router.patch("/{project_id}/{task_id}")
def update_task(
    project_id: str,
    task_id: str,
    update: TaskUpdate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    task = db.query(ScopeTask).filter(
        ScopeTask.id == task_id,
        ScopeTask.project_id == project_id,
    ).first()
    if not task:
        raise HTTPException(404, "Task not found.")
    data = update.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "task_type" and v:
            setattr(task, k, _parse_task_type(v))
        elif k == "source" and v:
            for src in TaskSource:
                if src.value == v:
                    setattr(task, k, src)
                    break
        else:
            setattr(task, k, v)
    db.commit()
    db.refresh(task)
    return _task_dict(task)


@router.delete("/{project_id}/{task_id}", status_code=204)
def delete_task(
    project_id: str,
    task_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    task = db.query(ScopeTask).filter(
        ScopeTask.id == task_id,
        ScopeTask.project_id == project_id,
    ).first()
    if not task:
        raise HTTPException(404, "Task not found.")
    db.delete(task)
    db.commit()
