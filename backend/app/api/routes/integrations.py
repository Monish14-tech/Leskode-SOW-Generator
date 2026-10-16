"""Integrations, clarifications, assumptions/exclusions/risks routes."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

from app.core.auth import get_current_user, require_project_access
from app.db.database import get_db
from app.db.models import (
    UserProfile, IntegrationItem, ClarificationQuestion, Assumption,
    Exclusion, Risk, FeasibilityStatus, TaskSource, ClarificationStatus,
    Requirement, ProjectModuleMapping
)
from app.ai.pipeline import generate_clarification_questions, generate_assumptions_exclusions

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── INTEGRATION ITEMS ──────────────────────────────────────────────────────

class IntegrationCreate(BaseModel):
    source_app: str
    destination_app: str
    data_direction: Optional[str] = "one-way"
    data_exchanged: Optional[str] = None
    business_purpose: Optional[str] = None
    trigger_or_frequency: Optional[str] = None
    auth_method: Optional[str] = None
    api_connector: Optional[str] = None
    error_handling: Optional[str] = None
    duplicate_handling: Optional[str] = None
    retry_strategy: Optional[str] = None
    ownership: Optional[str] = None
    testing_requirements: Optional[str] = None
    pending_questions: Optional[str] = None
    linked_requirement_ids: Optional[List[str]] = []


def _int_dict(i: IntegrationItem) -> dict:
    return {
        "id": i.id, "project_id": i.project_id,
        "integration_id_label": i.integration_id_label,
        "source_app": i.source_app, "destination_app": i.destination_app,
        "data_direction": i.data_direction, "data_exchanged": i.data_exchanged,
        "business_purpose": i.business_purpose,
        "trigger_or_frequency": i.trigger_or_frequency,
        "auth_method": i.auth_method, "api_connector": i.api_connector,
        "error_handling": i.error_handling, "duplicate_handling": i.duplicate_handling,
        "retry_strategy": i.retry_strategy, "ownership": i.ownership,
        "feasibility_status": i.feasibility_status.value if i.feasibility_status else "Pending Assessment",
        "testing_requirements": i.testing_requirements,
        "pending_questions": i.pending_questions,
        "linked_requirement_ids": i.linked_requirement_ids or [],
        "is_approved": i.is_approved,
        "source": i.source.value if i.source else "AI Recommendation",
        "created_at": i.created_at.isoformat() if i.created_at else None,
    }


@router.get("/{project_id}/integrations")
def list_integrations(project_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    items = db.query(IntegrationItem).filter(IntegrationItem.project_id == project_id).all()
    return [_int_dict(i) for i in items]


@router.post("/{project_id}/integrations", status_code=201)
def create_integration(project_id: str, req: IntegrationCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    count = db.query(IntegrationItem).filter(IntegrationItem.project_id == project_id).count()
    item = IntegrationItem(
        project_id=project_id,
        integration_id_label=f"INT-{count + 1:03d}",
        source=TaskSource.CONSULTANT_ADDITION,
        is_approved=True,
        feasibility_status=FeasibilityStatus.PENDING,
        **req.model_dump(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _int_dict(item)


def _gen_integrations_bg(project_id: str):
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        mappings = db.query(ProjectModuleMapping).filter(ProjectModuleMapping.project_id == project_id).all()
        active_modules = [((m.module.name.lower() if m.module else "") + " " + (m.module.display_name.lower() if m.module else "")) for m in mappings]
        reqs = db.query(Requirement).filter(Requirement.project_id == project_id).all()

        count = db.query(IntegrationItem).filter(IntegrationItem.project_id == project_id).count()
        candidates = []

        # 1. Zoho CRM <-> Zoho Books
        if any("crm" in m for m in active_modules) and any("books" in m for m in active_modules):
            crm_reqs = [r.req_id for r in reqs if "crm" in (r.suggested_zoho_module or "").lower() or "invoice" in r.title.lower()]
            candidates.append({
                "source_app": "Zoho CRM",
                "destination_app": "Zoho Books",
                "data_direction": "bidirectional",
                "data_exchanged": "Accounts <-> Customers, Deals (Closed Won) -> Sales Invoices",
                "business_purpose": "Synchronize verified customer master and auto-convert won deals into accounting invoices",
                "trigger_or_frequency": "Real-time on Deal status = Closed Won & daily customer sync",
                "auth_method": "OAuth 2.0 Native Zoho Finance Connector",
                "api_connector": "Zoho Finance Suite Integration",
                "error_handling": "Retry queue with notification to Finance Administrator",
                "duplicate_handling": "Match by GSTIN or Email ID",
                "retry_strategy": "Exponential backoff up to 5 attempts",
                "ownership": "Consultant & Zoho Implementation Team",
                "feasibility_status": FeasibilityStatus.CONFIRMED,
                "testing_requirements": "UAT deal closure to invoice creation reconciliation test",
                "linked_requirement_ids": crm_reqs[:5],
            })

        # 2. Zoho Books <-> Zoho Inventory
        if any("inventory" in m for m in active_modules) and any("books" in m for m in active_modules):
            inv_reqs = [r.req_id for r in reqs if "inventory" in (r.suggested_zoho_module or "").lower() or "stock" in r.title.lower()]
            candidates.append({
                "source_app": "Zoho Books",
                "destination_app": "Zoho Inventory",
                "data_direction": "bidirectional",
                "data_exchanged": "Item masters, stock levels, warehouse transfers, vendor purchase orders",
                "business_purpose": "Real-time stock valuation sync with financial accounting general ledger",
                "trigger_or_frequency": "Instantaneous database sync",
                "auth_method": "Native Shared Finance DB",
                "api_connector": "Zoho Finance Platform Native Sync",
                "error_handling": "System transaction rollback on validation failure",
                "duplicate_handling": "SKU unique identifier enforcement",
                "retry_strategy": "Immediate automatic transaction retry",
                "ownership": "Inventory Controller & Finance Head",
                "feasibility_status": FeasibilityStatus.CONFIRMED,
                "testing_requirements": "Multi-warehouse dispatch and ledger reconciliation test",
                "linked_requirement_ids": inv_reqs[:5],
            })

        # 3. Weighbridge / Gate Entry / IoT -> Zoho Creator / Inventory
        weigh_reqs = [r.req_id for r in reqs if any(k in (r.title + " " + r.description).lower() for k in ["weigh", "gate", "vehicle", "truck", "scale"])]
        if weigh_reqs or any("creator" in m for m in active_modules):
            candidates.append({
                "source_app": "Weighbridge Electronic Scale / Gate Entry",
                "destination_app": "Zoho Creator / Zoho Inventory",
                "data_direction": "one-way",
                "data_exchanged": "Gross weight, tare weight, net weight, vehicle number, weighment slip ID, timestamp",
                "business_purpose": "Automated capture of weighbridge gross/tare slips directly into ERP to prevent manual tampering",
                "trigger_or_frequency": "Instant TCP/IP webhook on scale lock & weighment print",
                "auth_method": "API Token & HMAC SHA-256",
                "api_connector": "Zoho Creator REST API & Node.js serial gateway",
                "error_handling": "Local buffer storage on network disconnect with auto-sync on reconnect",
                "duplicate_handling": "Unique slip number constraint",
                "retry_strategy": "Local queue replay every 30 seconds until acknowledged",
                "ownership": "Weighbridge Operator & Integration Engineer",
                "feasibility_status": FeasibilityStatus.CONFIRMED,
                "testing_requirements": "Live weighment slip simulation and invoice weight verification test",
                "linked_requirement_ids": weigh_reqs[:5],
            })

        # 4. Zoho People <-> Zoho Payroll
        if any("people" in m for m in active_modules) and any("payroll" in m for m in active_modules):
            candidates.append({
                "source_app": "Zoho People",
                "destination_app": "Zoho Payroll",
                "data_direction": "one-way",
                "data_exchanged": "Employee master records, biometric attendance logs, approved leaves, LOP days",
                "business_purpose": "Automated monthly payroll run based on attendance and leave records",
                "trigger_or_frequency": "Monthly payroll cutoff run & instant employee onboard sync",
                "auth_method": "Native Zoho People-Payroll Sync Connector",
                "api_connector": "Zoho HR Suite Connector",
                "error_handling": "Payroll exception alert to HR Manager",
                "duplicate_handling": "Employee ID uniqueness enforcement",
                "retry_strategy": "Automatic re-sync on profile update",
                "ownership": "HR Administrator",
                "feasibility_status": FeasibilityStatus.CONFIRMED,
                "testing_requirements": "Attendance to payslip generation variance audit",
                "linked_requirement_ids": [],
            })

        # 5. Core Zoho Apps -> Zoho Analytics
        if any("analytics" in m for m in active_modules):
            candidates.append({
                "source_app": "Zoho CRM / Books / Inventory",
                "destination_app": "Zoho Analytics",
                "data_direction": "one-way",
                "data_exchanged": "Sales pipeline data, daily trading prices, dispatch logs, customer ageing",
                "business_purpose": "Real-time executive business intelligence dashboards and market price board analytics",
                "trigger_or_frequency": "Hourly periodic sync & on-demand manual refresh",
                "auth_method": "Zoho Advanced Analytics Native Connector",
                "api_connector": "Zoho Analytics Data Engine",
                "error_handling": "Sync failure alert to System Admin",
                "duplicate_handling": "Table primary key replacement",
                "retry_strategy": "Scheduled re-run on next hourly cycle",
                "ownership": "BI Analyst & Executive Management",
                "feasibility_status": FeasibilityStatus.CONFIRMED,
                "testing_requirements": "Dashboard metrics validation against source accounting ledgers",
                "linked_requirement_ids": [],
            })

        for i, item_data in enumerate(candidates):
            exists = db.query(IntegrationItem).filter(
                IntegrationItem.project_id == project_id,
                IntegrationItem.source_app == item_data["source_app"],
                IntegrationItem.destination_app == item_data["destination_app"],
            ).first()
            if not exists:
                new_item = IntegrationItem(
                    project_id=project_id,
                    integration_id_label=f"INT-{count + i + 1:03d}",
                    source=TaskSource.AI_RECOMMENDATION,
                    is_approved=True,
                    **item_data,
                )
                db.add(new_item)
        db.commit()
    except Exception as e:
        logger.error(f"Integration generation failed: {e}", exc_info=True)
    finally:
        db.close()


@router.post("/{project_id}/integrations/generate")
def generate_integrations(project_id: str, background_tasks: BackgroundTasks, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    background_tasks.add_task(_gen_integrations_bg, project_id)
    return {"message": "Integration generation started."}


@router.patch("/{project_id}/integrations/{item_id}")
def update_integration(project_id: str, item_id: str, req: IntegrationCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    item = db.query(IntegrationItem).filter(IntegrationItem.id == item_id, IntegrationItem.project_id == project_id).first()
    if not item:
        raise HTTPException(404, "Integration not found.")
    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return _int_dict(item)


@router.delete("/{project_id}/integrations/{item_id}", status_code=204)
def delete_integration(project_id: str, item_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    item = db.query(IntegrationItem).filter(IntegrationItem.id == item_id, IntegrationItem.project_id == project_id).first()
    if not item:
        raise HTTPException(404, "Integration not found.")
    db.delete(item)
    db.commit()


# ─── CLARIFICATION QUESTIONS ────────────────────────────────────────────────

class ClarificationCreate(BaseModel):
    group: Optional[str] = "Business Process"
    question: str
    why_it_matters: Optional[str] = None
    related_requirement_ids: Optional[List[str]] = []
    suggested_options: Optional[List[str]] = []
    impact_if_unanswered: Optional[str] = None
    responsible_person: Optional[str] = None


class ClarificationAnswer(BaseModel):
    answer: str
    status: Optional[str] = "Answered"


def _clq_dict(c: ClarificationQuestion) -> dict:
    return {
        "id": c.id, "project_id": c.project_id,
        "question_id_label": c.question_id_label,
        "group": c.group, "question": c.question,
        "why_it_matters": c.why_it_matters,
        "related_requirement_ids": c.related_requirement_ids or [],
        "suggested_options": c.suggested_options or [],
        "answer": c.answer,
        "responsible_person": c.responsible_person,
        "status": c.status.value if c.status else "Open",
        "impact_if_unanswered": c.impact_if_unanswered,
        "source": c.source.value if c.source else "AI Recommendation",
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


def _gen_clarifications_bg(project_id: str):
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        requirements = db.query(Requirement).filter(Requirement.project_id == project_id).all()
        req_dicts = [{"req_id": r.req_id, "title": r.title, "description": r.description} for r in requirements]
        missing = [r.description for r in requirements if r.category and r.category.value == "Missing Information"]
        unclear = [r.description for r in requirements if r.category and r.category.value == "Unclear/Contradictory"]

        result = generate_clarification_questions(req_dicts, missing, unclear)
        count = db.query(ClarificationQuestion).filter(ClarificationQuestion.project_id == project_id).count()

        for i, q_data in enumerate(result.get("questions", [])):
            clq = ClarificationQuestion(
                project_id=project_id,
                question_id_label=q_data.get("question_id_label", f"CLQ-{count + i + 1:03d}"),
                group=q_data.get("group", "Business Process"),
                question=q_data.get("question", ""),
                why_it_matters=q_data.get("why_it_matters"),
                related_requirement_ids=q_data.get("related_requirement_ids", []),
                suggested_options=q_data.get("suggested_options", []),
                impact_if_unanswered=q_data.get("impact_if_unanswered"),
                status=ClarificationStatus.OPEN,
                source=TaskSource.AI_RECOMMENDATION,
            )
            db.add(clq)
        db.commit()
    except Exception as e:
        logger.error(f"Clarification generation failed: {e}", exc_info=True)
    finally:
        db.close()


@router.post("/{project_id}/clarifications/generate")
def generate_clarifications(project_id: str, background_tasks: BackgroundTasks, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    background_tasks.add_task(_gen_clarifications_bg, project_id)
    return {"message": "Clarification generation started."}


@router.get("/{project_id}/clarifications")
def list_clarifications(project_id: str, group: Optional[str] = None, status: Optional[str] = None, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    q = db.query(ClarificationQuestion).filter(ClarificationQuestion.project_id == project_id)
    if group:
        q = q.filter(ClarificationQuestion.group == group)
    if status:
        q = q.filter(ClarificationQuestion.status == status)
    return [_clq_dict(c) for c in q.order_by(ClarificationQuestion.created_at).all()]


@router.post("/{project_id}/clarifications", status_code=201)
def create_clarification(project_id: str, req: ClarificationCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    count = db.query(ClarificationQuestion).filter(ClarificationQuestion.project_id == project_id).count()
    clq = ClarificationQuestion(
        project_id=project_id,
        question_id_label=f"CLQ-{count + 1:03d}",
        source=TaskSource.CONSULTANT_ADDITION,
        status=ClarificationStatus.OPEN,
        **req.model_dump(),
    )
    db.add(clq)
    db.commit()
    db.refresh(clq)
    return _clq_dict(clq)


@router.patch("/{project_id}/clarifications/{clq_id}/answer")
@router.patch("/{project_id}/clarifications/{clq_id}")
def answer_clarification(project_id: str, clq_id: str, req: ClarificationAnswer, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    clq = db.query(ClarificationQuestion).filter(ClarificationQuestion.id == clq_id, ClarificationQuestion.project_id == project_id).first()
    if not clq:
        raise HTTPException(404, "Question not found.")
    clq.answer = req.answer
    for s in ClarificationStatus:
        if s.value == req.status:
            clq.status = s
            break
    db.commit()
    db.refresh(clq)
    return _clq_dict(clq)


@router.delete("/{project_id}/clarifications/{clq_id}", status_code=204)
def delete_clarification(project_id: str, clq_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    clq = db.query(ClarificationQuestion).filter(ClarificationQuestion.id == clq_id, ClarificationQuestion.project_id == project_id).first()
    if not clq:
        raise HTTPException(404, "Question not found.")
    db.delete(clq)
    db.commit()
