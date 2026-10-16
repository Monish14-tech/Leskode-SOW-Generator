"""
Seed and generate the official Leskode Master SOW Template DOCX and register in DB.
"""
import os
import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.document.leskode_template import generate_leskode_sow
from app.db.database import SessionLocal, init_db
from app.db.models import Organization, SowTemplate, SowTemplateVersion, TemplateStatus, UserProfile

templates_dir = backend_dir / "templates"
templates_dir.mkdir(exist_ok=True)
master_docx_path = templates_dir / "Leskode_Master_SOW_Template.docx"

print(f"Generating Leskode Master SOW Template at: {master_docx_path}")

sample_content = {
    "client_name": "Shiva Karthikeyaa Steels",
    "project_name": "Zoho Implementation for Steel Trading & Operations",
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
    "total_duration": "8–10 Weeks"
}

generate_leskode_sow(sample_content, str(master_docx_path))
print(f"[OK] Generated template successfully! File size: {os.path.getsize(master_docx_path)} bytes")

# Ensure tables exist
init_db()

# Register in DB
db = SessionLocal()
try:
    org = db.query(Organization).first()
    if not org:
        org = Organization(name="Leskode Technologies", slug="leskode")
        db.add(org)
        db.commit()
        db.refresh(org)

    user = db.query(UserProfile).first()

    template = db.query(SowTemplate).filter(SowTemplate.organization_id == org.id).first()
    if not template:
        template = SowTemplate(
            organization_id=org.id,
            name="Leskode Master SOW Flow Template",
            description="Official 17-section SOW template for Zoho implementations strictly adhering to Leskode brand standards, locked legal wording, and modular architecture."
        )
        db.add(template)
        db.commit()
        db.refresh(template)
    else:
        template.name = "Leskode Master SOW Flow Template"
        db.commit()

    # Create or update active version
    version = db.query(SowTemplateVersion).filter(
        SowTemplateVersion.template_id == template.id,
        SowTemplateVersion.version_number == "1.0"
    ).first()

    relative_storage_path = str(master_docx_path.relative_to(backend_dir)) if master_docx_path.is_relative_to(backend_dir) else str(master_docx_path)

    if not version:
        version = SowTemplateVersion(
            template_id=template.id,
            version_number="1.0",
            original_filename="Leskode_Master_SOW_Template.docx",
            storage_path=relative_storage_path,
            status=TemplateStatus.ACTIVE,
            change_summary="Initial Leskode 17-Section Master Flow Template seeded.",
            published_by=user.id if user else None,
        )
        db.add(version)
    else:
        version.status = TemplateStatus.ACTIVE
        version.storage_path = relative_storage_path
        version.original_filename = "Leskode_Master_SOW_Template.docx"

    db.commit()
    print(f"[OK] Master Template registered in DB: Template ID {template.id}, Version ID {version.id}")

finally:
    db.close()
