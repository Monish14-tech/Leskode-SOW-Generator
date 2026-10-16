"""Module mapping routes."""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_project_access
from app.db.database import get_db
from app.db.models import (
    UserProfile, ZohoModule, ProjectModuleMapping, Requirement,
    Project, ProjectStatus, FeasibilityStatus, RequirementStatus
)
from app.ai.pipeline import recommend_zoho_modules, AINotConfiguredError, AIServiceError

router = APIRouter()
logger = logging.getLogger(__name__)

# Seed Zoho module catalogue if empty
ZOHO_MODULES = [
    {"name": "zoho_crm", "display_name": "Zoho CRM", "category": "Sales & Marketing",
     "description": "Customer relationship management — leads, contacts, accounts, deals, activities."},
    {"name": "zoho_books", "display_name": "Zoho Books", "category": "Finance",
     "description": "Accounting, invoicing, expenses, GST compliance, bank reconciliation."},
    {"name": "zoho_inventory", "display_name": "Zoho Inventory", "category": "Operations",
     "description": "Inventory management, purchase orders, warehousing, multi-location stock."},
    {"name": "zoho_creator", "display_name": "Zoho Creator", "category": "Custom Apps",
     "description": "Low-code custom application builder for unique business workflows."},
    {"name": "zoho_desk", "display_name": "Zoho Desk", "category": "Support",
     "description": "Customer support ticketing, SLA management, knowledge base."},
    {"name": "zoho_forms", "display_name": "Zoho Forms", "category": "Data Collection",
     "description": "Online forms for data collection, embedded in websites or apps."},
    {"name": "zoho_campaigns", "display_name": "Zoho Campaigns", "category": "Marketing",
     "description": "Email marketing, automation campaigns, subscriber management."},
    {"name": "zoho_analytics", "display_name": "Zoho Analytics", "category": "Business Intelligence",
     "description": "Advanced reporting, dashboards, data blending from multiple sources."},
    {"name": "zoho_sign", "display_name": "Zoho Sign", "category": "Documents",
     "description": "Digital signatures, document workflows, compliance."},
    {"name": "zoho_projects", "display_name": "Zoho Projects", "category": "Project Management",
     "description": "Project planning, tasks, milestones, time tracking, Gantt charts."},
    {"name": "zoho_flow", "display_name": "Zoho Flow", "category": "Integration",
     "description": "Integration platform connecting Zoho apps and third-party services."},
    {"name": "zoho_workdrive", "display_name": "Zoho WorkDrive", "category": "Collaboration",
     "description": "Team file storage, document collaboration, version control."},
    {"name": "zoho_people", "display_name": "Zoho People", "category": "HR",
     "description": "HR management, attendance, leave, performance reviews."},
    {"name": "zoho_salesiq", "display_name": "Zoho SalesIQ", "category": "Sales & Marketing",
     "description": "Website visitor tracking, live chat, lead scoring."},
    {"name": "zoho_expense", "display_name": "Zoho Expense", "category": "Finance",
     "description": "Expense management, reimbursement workflows, receipt scanning."},
]


def _ensure_modules_seeded(db: Session):
    if db.query(ZohoModule).count() == 0:
        for m in ZOHO_MODULES:
            db.add(ZohoModule(**m))
        db.commit()


def _mapping_dict(m: ProjectModuleMapping) -> dict:
    return {
        "id": m.id,
        "project_id": m.project_id,
        "module_id": m.module_id,
        "module_name": m.module.display_name if m.module else None,
        "module_slug": m.module.name if m.module else None,
        "business_purpose": m.business_purpose,
        "recommendation_reason": m.recommendation_reason,
        "linked_requirement_ids": m.linked_requirement_ids or [],
        "proposed_configuration": m.proposed_configuration,
        "custom_fields": m.custom_fields or [],
        "feasibility_status": m.feasibility_status.value if m.feasibility_status else "Pending Assessment",
        "is_approved": m.is_approved,
        "is_ai_recommended": m.is_ai_recommended,
        "consultant_notes": m.consultant_notes,
        "licensing_notes": m.licensing_notes,
        "custom_dev_required": m.custom_dev_required,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


class MappingUpdate(BaseModel):
    business_purpose: Optional[str] = None
    recommendation_reason: Optional[str] = None
    proposed_configuration: Optional[str] = None
    feasibility_status: Optional[str] = None
    is_approved: Optional[bool] = None
    consultant_notes: Optional[str] = None
    licensing_notes: Optional[str] = None
    custom_dev_required: Optional[str] = None
    linked_requirement_ids: Optional[List[str]] = None


def _ai_recommend_background(project_id: str):
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        _ensure_modules_seeded(db)
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        requirements = db.query(Requirement).filter(
            Requirement.project_id == project_id,
            Requirement.review_status != RequirementStatus.REJECTED,
        ).all()

        if not requirements:
            return

        req_dicts = [
            {
                "req_id": r.req_id,
                "title": r.title,
                "description": r.description,
                "suggested_zoho_module": r.suggested_zoho_module,
            }
            for r in requirements
        ]

        result = recommend_zoho_modules(req_dicts, project.existing_systems or "")

        all_modules = {m.name: m for m in db.query(ZohoModule).all()}

        for mod_data in result.get("modules", []):
            module_name = mod_data.get("name", "")
            # Find matching module
            module = None
            for m in all_modules.values():
                if m.display_name.lower() == module_name.lower() or m.name.lower() == module_name.lower().replace(" ", "_"):
                    module = m
                    break

            if not module:
                # Create unknown module
                module = ZohoModule(
                    name=module_name.lower().replace(" ", "_"),
                    display_name=module_name,
                    category="Other",
                    description=mod_data.get("business_purpose", ""),
                )
                db.add(module)
                db.flush()

            # Skip if already mapped
            existing = db.query(ProjectModuleMapping).filter(
                ProjectModuleMapping.project_id == project_id,
                ProjectModuleMapping.module_id == module.id,
            ).first()
            if existing:
                continue

            mapping = ProjectModuleMapping(
                project_id=project_id,
                module_id=module.id,
                business_purpose=mod_data.get("business_purpose"),
                recommendation_reason=mod_data.get("recommendation_reason"),
                linked_requirement_ids=mod_data.get("linked_requirement_ids", []),
                proposed_configuration=mod_data.get("proposed_configuration"),
                feasibility_status=FeasibilityStatus.PENDING,
                is_approved=False,
                is_ai_recommended=True,
                licensing_notes=mod_data.get("licensing_notes"),
                custom_dev_required=mod_data.get("custom_dev_required"),
            )
            db.add(mapping)

        project.status = ProjectStatus.SCOPE_REVIEW
        db.commit()
        logger.info(f"Module recommendations saved for project {project_id}")

    except Exception as e:
        logger.error(f"Module recommendation failed for {project_id}: {e}", exc_info=True)
    finally:
        db.close()


@router.get("/catalogue")
def get_module_catalogue(
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_modules_seeded(db)
    modules = db.query(ZohoModule).filter(ZohoModule.is_active == True).all()
    return [
        {"id": m.id, "name": m.name, "display_name": m.display_name,
         "description": m.description, "category": m.category}
        for m in modules
    ]


@router.post("/{project_id}/recommend")
def recommend_modules(
    project_id: str,
    background_tasks: BackgroundTasks,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    background_tasks.add_task(_ai_recommend_background, project_id)
    return {"message": "Module recommendation started in background."}


@router.get("/{project_id}")
def get_project_modules(
    project_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    mappings = db.query(ProjectModuleMapping).filter(
        ProjectModuleMapping.project_id == project_id
    ).all()
    return [_mapping_dict(m) for m in mappings]


@router.post("/{project_id}")
def add_module(
    project_id: str,
    module_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    module = db.query(ZohoModule).filter(ZohoModule.id == module_id).first()
    if not module:
        raise HTTPException(404, "Module not found in catalogue.")

    existing = db.query(ProjectModuleMapping).filter(
        ProjectModuleMapping.project_id == project_id,
        ProjectModuleMapping.module_id == module_id,
    ).first()
    if existing:
        raise HTTPException(409, "Module already mapped to this project.")

    mapping = ProjectModuleMapping(
        project_id=project_id,
        module_id=module_id,
        is_ai_recommended=False,
        feasibility_status=FeasibilityStatus.PENDING,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return _mapping_dict(mapping)


@router.patch("/{project_id}/{mapping_id}")
def update_module_mapping(
    project_id: str,
    mapping_id: str,
    update: MappingUpdate,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    mapping = db.query(ProjectModuleMapping).filter(
        ProjectModuleMapping.id == mapping_id,
        ProjectModuleMapping.project_id == project_id,
    ).first()
    if not mapping:
        raise HTTPException(404, "Mapping not found.")

    data = update.model_dump(exclude_unset=True)
    for k, v in data.items():
        if k == "feasibility_status" and v:
            for fs in FeasibilityStatus:
                if fs.value == v:
                    setattr(mapping, k, fs)
                    break
        else:
            setattr(mapping, k, v)

    db.commit()
    db.refresh(mapping)
    return _mapping_dict(mapping)


@router.delete("/{project_id}/{mapping_id}", status_code=204)
def remove_module(
    project_id: str,
    mapping_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    mapping = db.query(ProjectModuleMapping).filter(
        ProjectModuleMapping.id == mapping_id,
        ProjectModuleMapping.project_id == project_id,
    ).first()
    if not mapping:
        raise HTTPException(404, "Mapping not found.")
    db.delete(mapping)
    db.commit()
