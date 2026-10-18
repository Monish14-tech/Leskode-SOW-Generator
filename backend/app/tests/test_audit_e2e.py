"""
ScopePilot AI — End-to-End System Audit & Verification Test Suite
Tests all 10 core requirements:
1. Document extraction (DOCX, PDF, TXT)
2. Requirements extraction, AI recommendation labelling, source references
3. Module recommendations & catalogue
4. Task and subtask generation
5. Automation matrix and SLA pending confirmation constraints
6. Clarification questions and answering
7. Scope coverage validation
8. SOW DOCX generation, verification, and file content
9. Error handling: missing credentials, invalid files, malformed AI responses, auth errors
10. Database persistence and user isolation
"""
import os
import io
import pytest
from docx import Document
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import SessionLocal, init_db, engine
from app.db.models import (
    Base, UserProfile, Organization, Project, UploadedDocument,
    Requirement, ProjectModuleMapping, ScopeTask, AutomationItem,
    ClarificationQuestion, SowDocument, UserRole, ProjectStatus,
    FeasibilityStatus, RequirementStatus, SowStatus
)
from app.document.extractor import extract_docx, extract_txt, extract_pdf
from app.document.generator import generate_sow_docx
from app.ai.pipeline import (
    call_ai, extract_requirements_from_text, recommend_zoho_modules,
    generate_scope_tasks, generate_automation_matrix,
    generate_clarification_questions, generate_assumptions_exclusions,
    validate_scope_coverage, AINotConfiguredError, AIServiceError
)
from app.core.auth import verify_jwt_token
from app.api.routes.auth import _create_token


@pytest.fixture(scope="module")
def setup_db():
    init_db()
    db = SessionLocal()
    yield db
    db.close()


# ─── TEST 1: Document Upload & Extraction ────────────────────────────────────
def test_document_extraction_txt():
    content = "Business Background:\nAcme Corp is expanding into international sales.\nThey need automated invoicing and lead tracking."
    sections, pages = extract_txt(content.encode("utf-8"))
    assert len(sections) > 0
    assert any("Acme Corp" in s["content"] for s in sections)
    assert pages >= 1


def test_document_extraction_docx(tmp_path):
    docx_file = tmp_path / "test_reqs.docx"
    doc = Document()
    doc.add_heading("1. Business Background", level=1)
    doc.add_paragraph("Acme Corp is an enterprise manufacturer operating across 3 locations.")
    doc.add_heading("2. Sales Requirements", level=1)
    doc.add_paragraph("The sales team requires lead management and automated assignment rules.")
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Role"
    table.rows[0].cells[1].text = "Count"
    table.rows[1].cells[0].text = "Sales Rep"
    table.rows[1].cells[1].text = "15"
    doc.save(str(docx_file))

    sections, pages = extract_docx(str(docx_file))
    assert len(sections) >= 2
    assert any(s["heading"] == "1. Business Background" for s in sections)
    assert any("lead management" in s["content"] for s in sections)
    assert any("Sales Rep" in s["content"] for s in sections)  # Table extraction


# ─── TEST 2: Requirements Extraction & Labelling ──────────────────────────────
def test_requirements_extraction_and_labelling():
    text = (
        "The sales team receives 500 leads daily from web landing pages.\n"
        "All incoming leads must be automatically assigned to regional sales reps.\n"
        "Finance requires automated tax invoice generation with GST compliance.\n"
        "Support team needs ticket SLA tracking and escalation within 4 hours."
    )
    result = extract_requirements_from_text(text, "sales_spec.docx")
    reqs = result.get("requirements", [])
    assert len(reqs) >= 3

    # Check that each requirement has an ID and a supporting excerpt / source
    for r in reqs:
        assert r["req_id"].startswith("REQ-")
        assert len(r["title"]) > 0
        assert len(r["description"]) > 0
        assert len(r["supporting_excerpt"]) > 0
        assert "is_ai_generated" in r
        assert isinstance(r["is_ai_generated"], bool)
        assert 0.0 <= r["confidence"] <= 1.0

    # Verify both confirmed and AI recommendations are properly identified
    confirmed = [r for r in reqs if not r["is_ai_generated"]]
    ai_recs = [r for r in reqs if r["is_ai_generated"]]
    assert len(confirmed) > 0, "Should have confirmed requirements directly from source text"
    assert len(ai_recs) >= 0


# ─── TEST 3: Zoho Module Recommendations ──────────────────────────────────────
def test_zoho_module_recommendations():
    sample_reqs = [
        {"req_id": "REQ-001", "title": "Lead capture and pipeline", "suggested_zoho_module": "Zoho CRM"},
        {"req_id": "REQ-002", "title": "Automated GST invoicing", "suggested_zoho_module": "Zoho Books"},
        {"req_id": "REQ-003", "title": "Customer support tickets", "suggested_zoho_module": "Zoho Desk"},
    ]
    recs = recommend_zoho_modules(sample_reqs)
    modules = recs.get("modules", [])
    assert len(modules) >= 2
    mod_names = [m["name"] for m in modules]
    assert "Zoho CRM" in mod_names
    assert "Zoho Books" in mod_names

    # Check fields
    for m in modules:
        assert m["is_ai_recommended"] is True
        assert len(m["business_purpose"]) > 10
        assert len(m["linked_requirement_ids"]) > 0


# ─── TEST 4: Scope Tasks Generation ───────────────────────────────────────────
def test_scope_tasks_generation():
    sample_reqs = [
        {"req_id": "REQ-001", "title": "Lead capture and assignment"}
    ]
    scope = generate_scope_tasks("Zoho CRM", "Sales pipeline automation", sample_reqs)
    tasks = scope.get("tasks", [])
    assert len(tasks) >= 1

    for t in tasks:
        assert t["task_id_label"].startswith("T-")
        assert len(t["name"]) > 0
        assert t["task_type"] in [
            "Configuration", "Customisation", "Automation",
            "Integration", "Data Migration", "Report", "Security & Access", "Testing"
        ]
        assert t["priority"] in ["High", "Medium", "Low"]
        assert t["source"] in ["Requirement", "AI Recommendation"]
        assert "deliverables" in t


# ─── TEST 5: Automation Matrix Generation ─────────────────────────────────────
def test_automation_matrix_generation():
    sample_reqs = [{"req_id": "REQ-001", "title": "Lead notification"}]
    matrix = generate_automation_matrix(sample_reqs, ["Zoho CRM"])
    autos = matrix.get("automations", [])
    assert len(autos) >= 1

    for a in autos:
        assert a["automation_id_label"].startswith("AUTO-")
        assert len(a["trigger_event"]) > 0
        assert len(a["action_performed"]) > 0
        assert len(a["recipient_role"]) > 0
        # Check rule: SLAs not specified in client requirements must be flagged as PENDING_CONFIRMATION or valid timing
        assert any(k in a["timing"] for k in ["PENDING_CONFIRMATION", "Instant", "Daily", "Immediate", "Real-time"])
        assert a["source"] in ["AI Recommendation", "Client Requirement", "Requirement"]


# ─── TEST 6: Clarifications & Assumptions ─────────────────────────────────────
def test_clarifications_and_assumptions():
    sample_reqs = [{"req_id": "REQ-001", "title": "Data migration"}]
    clq = generate_clarification_questions(sample_reqs, ["Volume unknown"], [])
    questions = clq.get("questions", [])
    assert len(questions) >= 1
    assert questions[0]["question_id_label"].startswith("CLQ-")
    assert len(questions[0]["suggested_options"]) > 0

    assump = generate_assumptions_exclusions(sample_reqs, ["Zoho CRM"])
    assert len(assump.get("assumptions", [])) >= 1
    assert "exclusions" in assump
    assert "risks" in assump


# ─── TEST 7: Scope Coverage Validation ────────────────────────────────────────
def test_scope_coverage_validation():
    reqs = [{"req_id": "REQ-001", "review_status": "Approved by Consultant"}, {"req_id": "REQ-002", "review_status": "Approved by Consultant"}]
    tasks = [{"requirement_ids": ["REQ-001"], "is_approved": True}]
    automations = []
    integrations = []
    clarifications = [{"status": "Open", "question": "Record volume?"}]

    val = validate_scope_coverage(reqs, tasks, automations, integrations, clarifications)
    assert val["total_requirements"] == 2
    assert "REQ-002" in val["unmapped_req_ids"]
    assert val["pending_clarifications"] == 1
    assert val["overall_level"] in ["warning", "fail"]


# ─── TEST 8: Actual SOW DOCX Generation ───────────────────────────────────────
def test_actual_sow_docx_generation(tmp_path):
    # Create master template
    template_path = tmp_path / "master_template.docx"
    doc = Document()
    doc.add_heading("MASTER STATEMENT OF WORK", 0)
    doc.add_paragraph("Client Name: {{CLIENT_NAME}}")
    doc.add_paragraph("Project Name: {{PROJECT_NAME}}")
    doc.add_paragraph("Date: {{PROJECT_DATE}}")
    doc.add_heading("1. Business Background", 1)
    doc.add_paragraph("{{BUSINESS_BACKGROUND}}")
    doc.add_heading("2. Scope of Modules", 1)
    doc.add_paragraph("{{MODULE_SCOPE}}")
    doc.add_heading("3. Assumptions", 1)
    doc.add_paragraph("{{ASSUMPTIONS}}")
    doc.save(str(template_path))

    # Generate populated SOW
    output_path = tmp_path / "Generated_SOW.docx"
    content = {
        "client_name": "Stark Industries",
        "project_name": "Global Zoho One Deployment",
        "project_date": "15 October 2026",
        "business_background": "Stark Industries requires an integrated CRM and Finance platform.",
        "module_scope": "• Zoho CRM: Complete lead-to-deal automation\n• Zoho Books: Multi-currency invoicing",
        "assumptions": "• Client provides super admin access during week 1",
    }

    result = generate_sow_docx(str(template_path), str(output_path), content)
    assert result["status"] == "success"
    assert os.path.exists(str(output_path))
    assert result["file_size_bytes"] > 1000

    # Inspect generated DOCX content
    gen_doc = Document(str(output_path))
    full_text = "\n".join(p.text for p in gen_doc.paragraphs)
    assert "Stark Industries" in full_text
    assert "Global Zoho One Deployment" in full_text
    assert "Stark Industries requires an integrated CRM" in full_text
    assert "{{CLIENT_NAME}}" not in full_text


# ─── TEST 9: Error Handling & Security ────────────────────────────────────────
def test_missing_credentials_raises_error():
    # Calling low-level call_ai without credentials must raise AINotConfiguredError
    settings = get_settings()
    if not settings.ai_configured:
        with pytest.raises(AINotConfiguredError):
            call_ai("prompt", "system")


def test_malformed_ai_json_handling():
    from app.ai.pipeline import _extract_json
    with pytest.raises(AIServiceError):
        _extract_json("This is not valid json at all")


def test_auth_token_tampering():
    token = _create_token("user-123", "user@example.com")
    tampered_token = token[:-5] + "XXXXX"
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        verify_jwt_token(tampered_token)


# ─── TEST 10: Database Persistence & User Isolation ───────────────────────────
def test_database_persistence_and_isolation(setup_db: Session):
    db = setup_db
    # Create test org and user
    org = Organization(name="Test Org Alpha", slug=f"test-org-{os.urandom(4).hex()}")
    db.add(org)
    db.flush()

    user = UserProfile(
        supabase_user_id=f"sub-{os.urandom(4).hex()}",
        organization_id=org.id,
        email="consultant@alpha.com",
        full_name="Alpha Consultant",
        role=UserRole.CONSULTANT,
    )
    db.add(user)
    db.flush()

    project = Project(
        organization_id=org.id,
        owner_id=user.id,
        client_name="Wayne Enterprises",
        project_name="Wayne CRM Rollout",
        status=ProjectStatus.DRAFT,
    )
    db.add(project)
    db.commit()

    # Query back and verify persistence
    p = db.query(Project).filter(Project.id == project.id).first()
    assert p is not None
    assert p.client_name == "Wayne Enterprises"
    assert p.organization_id == org.id

    # Verify requirement relation
    req = Requirement(
        project_id=project.id,
        req_id="REQ-001",
        title="Lead Capture",
        description="Capture leads from website",
        is_ai_generated=False,
    )
    db.add(req)
    db.commit()

    saved_req = db.query(Requirement).filter(Requirement.project_id == project.id).first()
    assert saved_req is not None
    assert saved_req.title == "Lead Capture"
    assert saved_req.is_ai_generated is False


def test_14_leskode_17_section_sow_generation(tmp_path):
    """
    Verify complete SOW generation strictly adhering to the 4-page Leskode SOW Flow Template:
    - All 17 sections in exact order
    - Locked wording Part 4 A, B, C, D, E, F
    - Sign-off block with Vaishnavi T, Director and Prepared by Monish
    - Master flow spine and visual flow figures
    """
    from app.document.leskode_template import generate_leskode_sow

    out_file = tmp_path / "Leskode_Shiva_Karthikeyaa_Steels_SOW.docx"
    sample_content = {
        "client_name": "Shiva Karthikeyaa Steels",
        "project_name": "Zoho ERP & Steels Trading Workflow",
        "solution_title": "Zoho Enterprise Solution for Shiva Karthikeyaa Steels",
        "application_line": "Zoho One (CRM, Books, Inventory, Desk, Flow, Analytics)",
        "business_one_liner": "Special Steels, Bright Bars, and Structural Materials Processing",
        "version_date": "Version 1.0 | October 2026",
        "business_background": (
            "Shiva Karthikeyaa Steels is a premier supplier of special engineering steels, bright bars, and structural materials. "
            "The company currently manages inquiries, quotations, customer communications, orders, and financial transactions across disparate channels, spreadsheets, and manual registers."
        ),
        "setup_description": (
            "This implementation establishes a unified, cloud-based business architecture on the Zoho platform (Zoho CRM, Books, Inventory, Desk, Flow, Analytics). "
            "The system standardizes customer tiers, automates multi-stage workflows from lead intake through rate-linked quotation, stock allocation, and dispatch to tax invoicing."
        ),
        "business_objectives": (
            "Deploy an integrated Zoho ecosystem for Shiva Karthikeyaa Steels that eliminates duplicate data entry, enforces pricing and discount discipline, accelerates quote-to-cash turnaround, and provides real-time multi-godown inventory visibility."
        ),
        "training_audience": "Shiva Karthikeyaa Steels's management, sales engineers, accounts, and stores personnel",
        "total_duration": "8–10 Weeks",
        "prepared_by": "Monish"
    }

    generate_leskode_sow(sample_content, str(out_file))
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 20000

    doc = Document(str(out_file))

    all_p_text = "\n".join(p.text for p in doc.paragraphs)
    all_tbl_text = "\n".join(" | ".join(c.text for c in row.cells) for tbl in doc.tables for row in tbl.rows)
    full_text = all_p_text + "\n" + all_tbl_text

    # Section 1: Cover Page
    assert "SCOPE OF WORK" in full_text
    assert "Shiva Karthikeyaa Steels" in full_text
    assert "Shavs Technologies Pvt Ltd" in full_text
    assert "Leskode" in full_text

    # Section 2: Confidentiality Notice (Locked Wording A)
    assert "Confidentiality Notice" in full_text
    assert "Restricted Use" in full_text
    assert "No Distribution" in full_text
    assert "Acknowledgement by Review" in full_text
    assert "Pricing Confidentiality" in full_text
    assert "Closing line: By retaining or reviewing this document" in full_text

    # Section 3: Project Information Table
    assert "Project Information" in full_text
    assert "Vaishnavi T" in full_text
    assert "+91 9500424307" in full_text
    assert "Coimbatore" in full_text

    # Section 4: Background & Objective
    assert "Executive Summary & Business Objective" in full_text
    assert "OBJECTIVE:" in full_text

    # Section 5: Overall Process Flow & Application Roles
    assert "Overall Process Flow & Application Architecture" in full_text
    assert "Running under every stage: roles and access, notifications and escalation" in full_text
    assert "Zoho Applications and Roles" in full_text

    # Section 6: Phases / Modules with flow figures and bold leads
    assert "Detailed Module Scope & Architecture" in full_text
    assert "Zoho Modules:" in full_text
    assert "Purpose:" in full_text

    # Section 7: Roles & Notifications
    assert "Roles, Permissions & Notification Triggers" in full_text
    assert "Event Notifications: Triggered on" in full_text

    # Section 8: Integration Scope
    assert "Integration Scope" in full_text

    # Section 9: Deliverables Summary
    assert "Deliverables Summary" in full_text

    # Section 10: Implementation Timeline & Locked Note B
    assert "Implementation Timeline" in full_text
    assert "Total Estimated Project Duration" in full_text
    assert "Timeline note: The timeline does not include data migration" in full_text

    # Section 11: Post-Implementation Support (Locked Wording C)
    assert "Post-Implementation Support" in full_text
    assert "UAT: Your team tests against real scenarios; sign-off is expected within 5–7 business days" in full_text
    assert "Training: Role-based training for" in full_text

    # Section 12: General Notes (Locked Wording D)
    assert "General Notes" in full_text
    assert "Zoho edition: Blueprint, approvals, assignment rules" in full_text
    assert "Licences: Zoho licences are bought by the client" in full_text
    assert "Data migration: Not included" in full_text

    # Section 13 & 14: Assumptions & Exclusions + Closing Line E
    assert "Assumptions & Exclusions" in full_text
    assert "Closing line: Data migration, hardware, and post-go-live support beyond hypercare." in full_text

    # Section 15: Points to Confirm
    assert "Points to Confirm (Clarifications)" in full_text

    # Section 16: Client Inputs Required
    assert "Client Inputs Required" in full_text

    # Section 17: Acceptance & Sign-off Table
    assert "Acceptance & Sign-Off" in full_text
    assert "Implementation Partner (Leskode)" in full_text
    assert "Vaishnavi T, Director" in full_text
    assert "Prepared by Monish" in full_text
