"""SOW generation, download, and version management routes."""
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_project_access
from app.db.database import get_db
from app.db.models import (
    UserProfile, SowDocument, SowTemplateVersion, Project, ProjectStatus,
    Requirement, ScopeTask, AutomationItem, IntegrationItem,
    ClarificationQuestion, Assumption, Exclusion, Risk,
    ProjectModuleMapping, SowStatus, TemplateStatus, ClarificationStatus
)
from app.document.generator import generate_sow_docx, GenerationError
from app.document.leskode_template import generate_leskode_sow

router = APIRouter()
logger = logging.getLogger(__name__)

SOW_OUTPUT_DIR = Path("sow_outputs")
SOW_OUTPUT_DIR.mkdir(exist_ok=True)


def _sow_dict(s: SowDocument) -> dict:
    return {
        "id": s.id,
        "project_id": s.project_id,
        "template_version_id": s.template_version_id,
        "version_number": s.version_number,
        "status": s.status.value if s.status else "draft",
        "docx_available": bool(s.docx_storage_path and os.path.exists(s.docx_storage_path)),
        "pdf_available": bool(s.pdf_storage_path and os.path.exists(s.pdf_storage_path)),
        "unresolved_placeholders": s.unresolved_placeholders or [],
        "validation_result": s.validation_result or {},
        "generated_at": s.generated_at.isoformat() if s.generated_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _build_sow_content(project_id: str, db: Session) -> dict:
    """Assemble all approved project data into the structured Leskode SOW content dictionary."""
    project = db.query(Project).filter(Project.id == project_id).first()

    # Only approved requirements
    approved_reqs = db.query(Requirement).filter(
        Requirement.project_id == project_id,
        Requirement.review_status == RequirementStatus.APPROVED_BY_CONSULTANT,
    ).all()
    reqs = approved_reqs if approved_reqs else db.query(Requirement).filter(
        Requirement.project_id == project_id,
        Requirement.review_status != RequirementStatus.REJECTED,
    ).all()

    # Only approved tasks
    approved_tasks = db.query(ScopeTask).filter(
        ScopeTask.project_id == project_id,
        ScopeTask.parent_task_id == None,
        ScopeTask.is_approved == True,
    ).all()
    tasks = approved_tasks if approved_tasks else db.query(ScopeTask).filter(
        ScopeTask.project_id == project_id,
        ScopeTask.parent_task_id == None,
    ).all()

    # Only approved automations
    approved_autos = db.query(AutomationItem).filter(
        AutomationItem.project_id == project_id,
        AutomationItem.is_approved == True,
    ).all()
    automations = approved_autos if approved_autos else db.query(AutomationItem).filter(
        AutomationItem.project_id == project_id,
    ).all()

    # Only approved integrations
    approved_ints = db.query(IntegrationItem).filter(
        IntegrationItem.project_id == project_id,
        IntegrationItem.is_approved == True,
    ).all()
    integrations = approved_ints if approved_ints else db.query(IntegrationItem).filter(
        IntegrationItem.project_id == project_id,
    ).all()

    clarifications = db.query(ClarificationQuestion).filter(
        ClarificationQuestion.project_id == project_id,
        ClarificationQuestion.status == ClarificationStatus.OPEN,
    ).all()
    assumptions = db.query(Assumption).filter(Assumption.project_id == project_id).all()
    exclusions = db.query(Exclusion).filter(Exclusion.project_id == project_id).all()
    risks = db.query(Risk).filter(Risk.project_id == project_id).all()

    # Only approved modules
    approved_mods = db.query(ProjectModuleMapping).filter(
        ProjectModuleMapping.project_id == project_id,
        ProjectModuleMapping.is_approved == True,
    ).all()
    modules = approved_mods if approved_mods else db.query(ProjectModuleMapping).filter(
        ProjectModuleMapping.project_id == project_id,
    ).all()

    client_name = project.client_name if project else "Valued Client"
    project_name = project.project_name if project else "Zoho Implementation"
    prepared_by = getattr(project, "prepared_by", None) or "Leskode Solutions Team"

    app_names = [m.module.display_name for m in modules if m.module]
    app_line = f"Zoho One ({', '.join(app_names)})" if app_names else "Zoho One (CRM, Books, Inventory, Desk, Flow, Analytics)"

    # Business background from requirements
    bg_reqs = [r for r in reqs if r.category and "Background" in r.category.value]
    objective_reqs = [r for r in reqs if r.category and "Objective" in r.category.value]

    business_background = (
        "\n".join([r.description for r in bg_reqs])
        if bg_reqs
        else f"{client_name} is implementing a comprehensive, fully integrated business management ecosystem on the Zoho platform to replace manual and fragmented workflows."
    )

    setup_description = (
        f"The implementation spans core Zoho applications ({app_line}). Each application is configured to exchange data "
        "seamlessly with adjacent systems, eliminating duplicate data entry and providing real-time operational visibility."
    )

    objectives = (
        "\n".join([f"• {r.title}: {r.description}" for r in objective_reqs])
        if objective_reqs
        else f"Deploy an integrated Zoho ecosystem for {client_name} that connects lead intake, quotation, inventory control, and financial reporting into an automated workflow."
    )

    # Build Module Blocks for Repeating Section 6 (Part 2 of Template)
    module_blocks = []
    for m in modules:
        m_name = m.module.display_name if m.module else "Zoho Module"
        m_code = m.module.name if m.module else "crm"
        m_purpose = m.business_purpose or f"Manages {m_name} workflows, operational records, and cross-application handoffs."

        module_tasks = [t for t in tasks if t.module_mapping_id == m.id]
        bullets = []
        for t in module_tasks[:5]:
            lead = t.name.split(":")[0].split("—")[0].split("-")[0].strip()
            detail = t.description or t.deliverables or t.name
            bullets.append((lead, detail))

        # Standard module coverage fallback per Part 2 table
        if len(bullets) < 3:
            if "crm" in m_code.lower():
                bullets.extend([
                    ("Lead Intake", "Captures website forms, social ads, and inbound inquiries with automated duplicate checking and assignment."),
                    ("Pipeline Stages", "Tracks qualification, quotation, and negotiation with mandatory exit conditions per stage."),
                    ("Rate-Linked Quotes", "Generates formal quotes using standard pricing and approved customer price tiers.")
                ])
            elif "book" in m_code.lower() or "finance" in m_code.lower():
                bullets.extend([
                    ("Automated Invoicing", "Invoices generated directly from approved Sales Orders with HSN codes and GST calculations."),
                    ("Three-Way Matching", "Vendor Bills verified against Purchase Orders and Goods Receipts prior to payment."),
                    ("Receivables Follow-up", "Automated email and SMS payment reminder escalations for overdue customer accounts.")
                ])
            elif "inventor" in m_code.lower() or "stock" in m_code.lower():
                bullets.extend([
                    ("Item Master", "Standardized SKU catalog with multi-unit conversions (units, packets, metric tonnes) and reorder thresholds."),
                    ("Multi-Godown Tracking", "Location-wise stock visibility across main yards and processing centers with inter-godown transfer orders."),
                    ("Batch Traceability", "Tracking manufacturer heat numbers, test certificate references, and aging on stock inward.")
                ])
            else:
                bullets.extend([
                    ("Setup & Configuration", f"Tailored configuration of {m_name} aligned with customer business process rules."),
                    ("Workflow Automation", "Automated triggers, stage progression alerts, and inter-application synchronization."),
                    ("Audit & Security", "Role-based access permissions, activity audit logs, and data integrity safeguards.")
                ])

        # Flow steps for 5-box visual figure (Part 2, d)
        flow_steps = [
            {"type": "START", "label": "Record Ingested", "detail": f"New entry in {m_name}"},
            {"type": "PROCESS", "label": "Validation & Rules", "detail": "Field checks & assignment"},
            {"type": "DECISION", "label": "Approval Required?", "detail": "Condition check"},
            {"type": "PROCESS", "label": "Downstream Sync", "detail": "Push to adjacent modules"},
            {"type": "END", "label": "Completed Status", "detail": "Audit logged"}
        ]
        if "crm" in m_code.lower():
            flow_steps = [
                {"type": "START", "label": "Enquiry Received", "detail": "Webform / Ads / WhatsApp"},
                {"type": "PROCESS", "label": "De-duplication & Assign", "detail": "Round-robin assignment"},
                {"type": "DECISION", "label": "Qualified Lead?", "detail": "BANT check"},
                {"type": "WARNING", "label": "Quote & Approval", "detail": "Check margin floor"},
                {"type": "END", "label": "Order Confirmed", "detail": "Convert to Books SO"}
            ]
        elif "book" in m_code.lower():
            flow_steps = [
                {"type": "START", "label": "Sales Order Synced", "detail": "From Zoho CRM"},
                {"type": "PROCESS", "label": "Tax Invoice Generated", "detail": "HSN & GST auto-applied"},
                {"type": "DECISION", "label": "Credit Limit OK?", "detail": "Overdue balance check"},
                {"type": "PROCESS", "label": "Dispatch & e-Way Bill", "detail": "NIC portal push"},
                {"type": "END", "label": "Payment Reconciled", "detail": "Bank statement matched"}
            ]
        elif "inventor" in m_code.lower():
            flow_steps = [
                {"type": "START", "label": "Purchase Order Raised", "detail": "Procurement team"},
                {"type": "PROCESS", "label": "Goods Receipt (GRN)", "detail": "Physical inspection"},
                {"type": "CHECK", "label": "Batch / Quality Check", "detail": "Mill test certificates"},
                {"type": "PROCESS", "label": "Godown Bin Allocation", "detail": "Stock inward entry"},
                {"type": "END", "label": "Available for Sale", "detail": "Real-time sync to CRM"}
            ]

        note = None
        if "crm" in m_code.lower():
            note = "WhatsApp integration requires client WhatsApp Business API credentials."
        elif "book" in m_code.lower():
            note = "Direct bank feed availability depends on individual bank API support."
        elif "inventor" in m_code.lower():
            note = "Hardware procurement (barcode scanners, label printers) is outside software scope."

        module_blocks.append({
            "name": m_name,
            "modules_line": f"{m_name} (Modules: {m_code})",
            "purpose": m_purpose,
            "flow_steps": flow_steps,
            "bullets": bullets[:5],
            "note": note
        })

    # Integrations table
    int_tuples = []
    for i in integrations:
        int_tuples.append((
            f"{i.source_app} ↔ {i.destination_app}",
            i.data_direction or "Bidirectional",
            i.api_connector or i.auth_method or "Native Zoho Integration",
            i.business_purpose or i.data_exchanged or "Standard synchronization"
        ))
    if not int_tuples:
        int_tuples = [
            ("CRM ↔ Books", "Bidirectional", "Native Zoho Integration", "Available — customer, item master, and sales order synchronization"),
            ("Books ↔ Inventory", "Bidirectional", "Native Zoho Integration", "Available — stock balance sync and purchase goods inwarding"),
            ("Website Forms → CRM", "Inbound", "Zoho Forms / Webhooks", "Available — website lead capture with instant attribution"),
            ("Books → GST Portal", "Outbound", "Native Zoho Books e-Way / e-Invoice", "Available — requires client GST portal credentials")
        ]

    # Deliverables table
    deliv_tuples = []
    for idx, m in enumerate(modules, start=1):
        m_name = m.module.display_name if m.module else f"Module {idx}"
        m_tasks = [t for t in tasks if t.module_mapping_id == m.id]
        desc = "; ".join([t.name for t in m_tasks[:4]]) if m_tasks else f"Configuration and rollout of {m_name}."
        deliv_tuples.append((f"Phase {idx}: {m_name}", desc))
    if not deliv_tuples:
        deliv_tuples = [
            ("Phase 1: Discovery & Architecture", "Architecture blueprint, field schema dictionary, pipeline stages definition, and UAT acceptance criteria."),
            ("Phase 2: Zoho CRM Setup", "Configured lead-to-deal pipeline, customer categories, rate-linked quotes, activity management, and executive sales reports."),
            ("Phase 3: Zoho Books Setup", "Chart of accounts, GST invoicing with e-invoice/e-way bill, category price lists, vendor POs, banking, and P&L statements."),
            ("Phase 4: Zoho Inventory Setup", "Standardized item catalogue, multi-godown stock tracking, reorder thresholds, and goods receipt note (GRN) workflow."),
            ("Phase 5: Integrations & Testing", "Native synchronization across CRM, Books, Inventory, and Analytics plus configured website intake forms."),
            ("Phase 6: Training & Handover", "Role-based training sessions for sales, accounts, and stores teams with recorded training videos and SOP guide.")
        ]

    # Assumptions & Exclusions
    assumptions_list = [a.description for a in assumptions] if assumptions else [
        "Licences in place; one coordinator for decisions and UAT.",
        "Existing master data (customers, vendors, items) will be provided in agreed CSV/Excel templates.",
        "Zoho application licences will be procured by the client prior to the start of each phase.",
        "API credentials for payment gateway, WhatsApp, and banking providers will be arranged by the client.",
        "UAT sign-off will be provided within 5–7 business days of test delivery."
    ]

    exclusions_list = [e.description for e in exclusions] if exclusions else [
        "Custom mobile app development outside standard Zoho mobile apps.",
        "Direct integration with proprietary weighbridge or on-premise legacy hardware.",
        "Hardware procurement (barcode scanners, label printers, biometric devices, workstations).",
        "Export invoicing and multi-currency accounting configuration.",
        "Post-go-live support beyond the agreed hypercare period (available under separate AMC)."
    ]

    # Points to confirm
    ptc_tuples = [
        (c.question, c.impact_if_unanswered or c.why_it_matters or "Defines configuration and timeline impact")
        for c in clarifications
    ] if clarifications else [
        ("Historical Data Volume", "Determines data cleansing and migration hours required if added via Change Request."),
        ("User Role Hierarchy & Approvers", "Defines the exact approval chains and discount floor authorization rules in CRM and Books."),
        ("Third-Party API Endpoints", "Determines Zoho Flow connector requirements versus custom Deluge webhook scripts."),
        ("GST / Invoicing Multi-Branch Setup", "Dictates the chart of accounts complexity and branch prefix configurations in Zoho Books.")
    ]

    existing_count = db.query(SowDocument).filter(SowDocument.project_id == project_id).count()

    return {
        "client_name": client_name,
        "project_name": project_name,
        "prepared_by": prepared_by,
        "solution_title": f"Zoho Business Management Solution for {client_name}",
        "application_line": app_line,
        "business_one_liner": project.notes or "Enterprise Operations & Business Automation",
        "version_date": f"Version 1.{existing_count + 1} | {datetime.now().strftime('%B %Y')}",
        "project_date": datetime.now().strftime("%d %B %Y"),
        "prepared_date": datetime.now().strftime("%d %B %Y"),
        "business_background": business_background,
        "setup_description": setup_description,
        "business_objectives": objectives,
        "module_blocks": module_blocks,
        "integrations": int_tuples,
        "deliverables": deliv_tuples,
        "assumptions": assumptions_list,
        "exclusions": exclusions_list,
        "points_to_confirm": ptc_tuples,
        "training_audience": f"{client_name}'s management, sales, accounts, and operations personnel",
        "total_duration": "8–10 Weeks",
    }


@router.post("/{project_id}/generate", status_code=201)
def generate_sow(
    project_id: str,
    template_version_id: Optional[str] = None,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an authentic Leskode SOW DOCX strictly following the official SOW Flow Template."""
    project = require_project_access(project_id, current_user, db)

    # Find active template version if requested
    from app.db.models import SowTemplate
    if template_version_id:
        version = db.query(SowTemplateVersion).filter(
            SowTemplateVersion.id == template_version_id
        ).first()
    else:
        version = (
            db.query(SowTemplateVersion)
            .join(SowTemplate, SowTemplateVersion.template_id == SowTemplate.id)
            .filter(
                SowTemplate.organization_id == current_user.organization_id,
                SowTemplateVersion.status == TemplateStatus.ACTIVE,
            )
            .order_by(SowTemplateVersion.published_at.desc())
            .first()
        )

    # Determine version count for filename
    existing_count = db.query(SowDocument).filter(SowDocument.project_id == project_id).count()
    safe_project_name = "".join(c if c.isalnum() else "_" for c in project.project_name)[:50]
    output_filename = f"{safe_project_name}_SOW_v{existing_count + 1}.docx"
    output_path = SOW_OUTPUT_DIR / f"{uuid.uuid4()}_{output_filename}"

    # Build content
    content = _build_sow_content(project_id, db)

    # Resolve template path safely if version exists
    tpl_path = None
    if version and version.storage_path:
        backend_base = Path(__file__).resolve().parent.parent.parent
        candidates = [
            Path(version.storage_path),
            backend_base / version.storage_path,
            backend_base / "templates" / Path(version.storage_path).name,
            Path("templates") / Path(version.storage_path).name,
        ]
        for c in candidates:
            if c.exists() and c.is_file():
                tpl_path = c
                break

    # If active master template DOCX exists, populate it directly to replicate exact logos, layout, and styling
    if tpl_path:
        try:
            logger.info(f"Generating SOW from master template: {tpl_path} ({version.original_filename if version else 'custom'})")
            gen_result = generate_sow_docx(
                template_path=str(tpl_path),
                output_path=str(output_path),
                content=content,
                placeholder_map=version.placeholder_map or {},
            )
        except Exception as e:
            logger.warning(f"Master template generation failed: {e}. Falling back to official Leskode generator.")
            generate_leskode_sow(content, str(output_path))
            gen_result = {
                "status": "success",
                "output_path": str(output_path),
                "file_size_bytes": os.path.getsize(str(output_path)),
                "unresolved_placeholders": [],
                "warnings": [f"Master template note ({e}), generated using official Leskode SOW engine."],
            }
    else:
        # Generate with the official Leskode 17-section SOW Flow Template
        generate_leskode_sow(content, str(output_path))
        gen_result = {
            "status": "success",
            "output_path": str(output_path),
            "file_size_bytes": os.path.getsize(str(output_path)),
            "unresolved_placeholders": [],
            "warnings": [],
        }

    # Save SOW document record
    sow_doc = SowDocument(
        project_id=project_id,
        template_version_id=version.id if version else None,
        version_number=existing_count + 1,
        status=SowStatus.DRAFT,
        docx_storage_path=str(output_path),
        content_snapshot=content,
        unresolved_placeholders=gen_result.get("unresolved_placeholders", []),
        validation_result={"warnings": gen_result.get("warnings", [])},
        generated_at=datetime.now(timezone.utc),
        generated_by=current_user.id,
    )
    db.add(sow_doc)

    # Update project status
    if project.status not in [ProjectStatus.APPROVED]:
        project.status = ProjectStatus.SOW_DRAFT

    db.commit()
    db.refresh(sow_doc)

    return {
        **_sow_dict(sow_doc),
        "generation_warnings": gen_result.get("warnings", []),
        "unresolved_placeholders": gen_result.get("unresolved_placeholders", []),
    }


@router.get("/{project_id}")
def list_sow_documents(
    project_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    docs = db.query(SowDocument).filter(
        SowDocument.project_id == project_id
    ).order_by(SowDocument.created_at.desc()).all()
    return [_sow_dict(d) for d in docs]


@router.get("/{project_id}/download/{sow_id}")
def download_sow(
    project_id: str,
    sow_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    doc = db.query(SowDocument).filter(
        SowDocument.id == sow_id,
        SowDocument.project_id == project_id,
    ).first()

    if not doc or not doc.docx_storage_path or not os.path.exists(doc.docx_storage_path):
        raise HTTPException(404, "SOW DOCX file not found on server")

    filename = Path(doc.docx_storage_path).name
    # Strip uuid prefix for clean download name
    clean_filename = "_".join(filename.split("_")[1:]) if "_" in filename else filename

    return FileResponse(
        path=doc.docx_storage_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=clean_filename,
    )


@router.get("/{project_id}/preview/{sow_id}")
def preview_sow(
    project_id: str,
    sow_id: str,
    current_user: UserProfile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_project_access(project_id, current_user, db)
    doc = db.query(SowDocument).filter(
        SowDocument.id == sow_id,
        SowDocument.project_id == project_id,
    ).first()

    if not doc:
        raise HTTPException(404, "SOW not found")

    return {
        "id": doc.id,
        "version_number": doc.version_number,
        "status": doc.status.value if doc.status else "draft",
        "content_snapshot": doc.content_snapshot or {},
        "unresolved_placeholders": doc.unresolved_placeholders or [],
        "generated_at": doc.generated_at.isoformat() if doc.generated_at else None,
    }
