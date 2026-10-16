"""Assumptions, exclusions, risks routes."""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

from app.core.auth import get_current_user, require_project_access
from app.db.database import get_db
from app.db.models import UserProfile, Assumption, Exclusion, Risk, Requirement, ProjectModuleMapping
from app.ai.pipeline import generate_assumptions_exclusions

router = APIRouter()
logger = logging.getLogger(__name__)


class AssumptionCreate(BaseModel):
    description: str
    source: Optional[str] = "Consultant Addition"
    impact: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = "Pending Validation"
    related_requirement_ids: Optional[List[str]] = []


class ExclusionCreate(BaseModel):
    description: str
    exclusion_type: Optional[str] = "Pending decision"
    source: Optional[str] = "Consultant Addition"
    impact: Optional[str] = None
    related_requirement_ids: Optional[List[str]] = []


class RiskCreate(BaseModel):
    description: str
    impact: Optional[str] = None
    probability: Optional[str] = "Medium"
    mitigation: Optional[str] = None
    owner: Optional[str] = None
    status: Optional[str] = "Open"
    related_requirement_ids: Optional[List[str]] = []


def _assumption_dict(a: Assumption) -> dict:
    return {
        "id": a.id, "project_id": a.project_id,
        "description": a.description, "source": a.source,
        "impact": a.impact, "owner": a.owner, "status": a.status,
        "related_requirement_ids": a.related_requirement_ids or [],
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _exclusion_dict(e: Exclusion) -> dict:
    return {
        "id": e.id, "project_id": e.project_id,
        "description": e.description, "exclusion_type": e.exclusion_type,
        "source": e.source, "impact": e.impact,
        "related_requirement_ids": e.related_requirement_ids or [],
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _risk_dict(r: Risk) -> dict:
    return {
        "id": r.id, "project_id": r.project_id,
        "description": r.description, "impact": r.impact,
        "probability": r.probability, "mitigation": r.mitigation,
        "owner": r.owner, "status": r.status,
        "related_requirement_ids": r.related_requirement_ids or [],
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _gen_assumptions_bg(project_id: str):
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        requirements = db.query(Requirement).filter(Requirement.project_id == project_id).limit(30).all()
        mappings = db.query(ProjectModuleMapping).filter(ProjectModuleMapping.project_id == project_id).all()
        module_names = [m.module.display_name for m in mappings if m.module]
        req_dicts = [{"req_id": r.req_id, "title": r.title, "description": r.description} for r in requirements]

        result = generate_assumptions_exclusions(req_dicts, module_names)

        for a_data in result.get("assumptions", []):
            assumption = Assumption(
                project_id=project_id,
                description=a_data.get("description", ""),
                source=a_data.get("source", "AI Recommendation"),
                impact=a_data.get("impact"),
                status=a_data.get("status", "Pending Validation"),
                related_requirement_ids=a_data.get("related_requirement_ids", []),
            )
            db.add(assumption)

        for e_data in result.get("exclusions", []):
            exclusion = Exclusion(
                project_id=project_id,
                description=e_data.get("description", ""),
                exclusion_type=e_data.get("exclusion_type", "Pending decision"),
                source=e_data.get("source", "AI Recommendation"),
                impact=e_data.get("impact"),
                related_requirement_ids=e_data.get("related_requirement_ids", []),
            )
            db.add(exclusion)

        for r_data in result.get("risks", []):
            risk = Risk(
                project_id=project_id,
                description=r_data.get("description", ""),
                impact=r_data.get("impact"),
                probability=r_data.get("probability", "Medium"),
                mitigation=r_data.get("mitigation"),
                status="Open",
                related_requirement_ids=[],
            )
            db.add(risk)

        db.commit()
    except Exception as e:
        logger.error(f"Assumptions generation failed: {e}", exc_info=True)
    finally:
        db.close()


@router.get("/{project_id}")
def get_all_assumptions(project_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    return {
        "assumptions": [_assumption_dict(a) for a in db.query(Assumption).filter(Assumption.project_id == project_id).all()],
        "exclusions": [_exclusion_dict(e) for e in db.query(Exclusion).filter(Exclusion.project_id == project_id).all()],
        "risks": [_risk_dict(r) for r in db.query(Risk).filter(Risk.project_id == project_id).all()]
    }


@router.post("/{project_id}/generate")
def generate_all(project_id: str, background_tasks: BackgroundTasks, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    background_tasks.add_task(_gen_assumptions_bg, project_id)
    return {"message": "Generation started."}


@router.get("/{project_id}/assumptions")
def list_assumptions(project_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    return [_assumption_dict(a) for a in db.query(Assumption).filter(Assumption.project_id == project_id).all()]


@router.post("/{project_id}/assumptions", status_code=201)
def create_assumption(project_id: str, req: AssumptionCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    a = Assumption(project_id=project_id, **req.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return _assumption_dict(a)


@router.delete("/{project_id}/assumptions/{item_id}", status_code=204)
def delete_assumption(project_id: str, item_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    a = db.query(Assumption).filter(Assumption.id == item_id, Assumption.project_id == project_id).first()
    if not a:
        raise HTTPException(404, "Not found.")
    db.delete(a)
    db.commit()


@router.get("/{project_id}/exclusions")
def list_exclusions(project_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    return [_exclusion_dict(e) for e in db.query(Exclusion).filter(Exclusion.project_id == project_id).all()]


@router.post("/{project_id}/exclusions", status_code=201)
def create_exclusion(project_id: str, req: ExclusionCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    e = Exclusion(project_id=project_id, **req.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return _exclusion_dict(e)


@router.delete("/{project_id}/exclusions/{item_id}", status_code=204)
def delete_exclusion(project_id: str, item_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    e = db.query(Exclusion).filter(Exclusion.id == item_id, Exclusion.project_id == project_id).first()
    if not e:
        raise HTTPException(404, "Not found.")
    db.delete(e)
    db.commit()


@router.get("/{project_id}/risks")
def list_risks(project_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    return [_risk_dict(r) for r in db.query(Risk).filter(Risk.project_id == project_id).all()]


@router.post("/{project_id}/risks", status_code=201)
def create_risk(project_id: str, req: RiskCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    r = Risk(project_id=project_id, **req.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _risk_dict(r)


@router.delete("/{project_id}/risks/{item_id}", status_code=204)
def delete_risk(project_id: str, item_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_project_access(project_id, current_user, db)
    r = db.query(Risk).filter(Risk.id == item_id, Risk.project_id == project_id).first()
    if not r:
        raise HTTPException(404, "Not found.")
    db.delete(r)
    db.commit()
