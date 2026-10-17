"""
ScopePilot AI — Leskode Master SOW Document Generator
Strictly implements the official 4-page "Leskode | Zoho Implementation SOW Flow Template"
and the 23-page Shiva Karthikeyaa Steels reference SOW.

Implements all 17 sections in exact order:
1. Cover Page (Logo/Brand, Shavs Technologies Pvt Ltd, SCOPE OF WORK, Prepared for, Solution title, application line, client, one line on business, version and date)
2. Confidentiality Notice (Locked Wording Part 4, A)
3. Project Information Table (Leskode block with Coimbatore, Vaishnavi T, +91 9500424307 vs Client)
4. Background & Objective (Three parts: client does, being set up, objective callout)
5. Overall Process Flow (Part 3 Master Process Flow Spine, Running under every stage note, Zoho Apps & Roles)
6. Phases or Modules (Repeating Part 2 blocks with Heading, Modules line, Purpose, 5-col Flow figure, 3-5 Bullets with bold leads, optional Table, optional Note)
7. Roles, Access & Notifications Table (Role, Access, Level + Notified Events line)
8. Integration Scope Table (Integration, Direction, Purpose/Method, Feasibility/Condition)
9. Deliverables Summary Table (Phase-wise deliverables)
10. Implementation Timeline Table (Stages, Description, Duration, Total must add up + Locked Timeline Note B)
11. Post-Implementation Support (Locked Wording Part 4, C with {audience} & hypercare)
12. Notes & Exclusions (Core Locked Clauses Part 4, D)
13. Assumptions (Licences in place, coordinator for decisions/UAT, client-specific assumptions)
14. Exclusions (Client exclusions + Locked Closing Line E + Optional enhancements line F)
15. Points to Confirm Table (Point, Why It Matters)
16. Client Inputs Required Table (Input, Used for Phase)
17. Acceptance & Sign-off Table (Leskode block with Vaishnavi T & Monish vs Customer)
"""
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

# Leskode Brand Colors
COLOR_PRIMARY = RGBColor(16, 44, 87)       # Deep Corporate Navy #102C57
COLOR_SECONDARY = RGBColor(53, 89, 142)    # Slate Steel Blue #35598E
COLOR_ACCENT = RGBColor(235, 87, 87)       # Coral Accent
COLOR_MUTED = RGBColor(100, 116, 139)      # Slate Gray
COLOR_DARK = RGBColor(15, 23, 42)          # Text dark
COLOR_WHITE = RGBColor(255, 255, 255)

HEX_NAVY = "102C57"
HEX_LIGHT_BLUE = "F0F4F8"
HEX_BORDER = "CBD5E1"
HEX_CALLOUT_BG = "F8FAFC"
HEX_CALLOUT_BORDER = "35598E"


def set_cell_background(cell, hex_color: str):
    """Set background color of a table cell."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    tc_pr.append(shd)


def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    """Set inner padding for a table cell (in twips/dxa)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tc_pr.append(tc_mar)


def create_callout_box(doc, heading: str, text: str, border_hex="102C57", bg_hex="F8FAFC"):
    """Create a stylized callout box (single-cell table with left thick border)."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, bg_hex)
    set_cell_margins(cell, top=160, bottom=160, left=200, right=200)

    tc_pr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="36" w:space="0" w:color="{border_hex}"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tc_pr.append(borders)

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    if heading:
        run_h = p.add_run(f"{heading.upper()}: ")
        run_h.bold = True
        run_h.font.color.rgb = COLOR_PRIMARY
        run_h.font.size = Pt(10)
    run_t = p.add_run(text)
    run_t.font.size = Pt(9.5)
    run_t.font.color.rgb = COLOR_DARK
    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def create_flow_figure(doc, steps: List[Dict[str, str]]):
    """
    Renders Part 2(d) 5-column flow figure:
    Start -> Process -> Decision -> Warning/Action -> End
    """
    if not steps:
        return

    cols = len(steps)
    tbl = doc.add_table(rows=1, cols=cols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

    for idx, step in enumerate(steps):
        cell = tbl.cell(0, idx)
        b_type = step.get("type", "PROCESS").upper()
        label = step.get("label", "")
        detail = step.get("detail", "")

        if b_type == "START":
            bg_col = "E6F4EA"
            border_col = "137333"
            tag = "START"
        elif b_type == "DECISION":
            bg_col = "FEF7E0"
            border_col = "F2994A"
            tag = "DECISION"
        elif b_type in ["WARNING", "CHECK"]:
            bg_col = "FCE8E6"
            border_col = "D93025"
            tag = "CHECK"
        elif b_type == "END":
            bg_col = "E8F0FE"
            border_col = "1A73E8"
            tag = "END / OUTCOME"
        else:
            bg_col = "F1F3F4"
            border_col = "35598E"
            tag = "PROCESS"

        set_cell_background(cell, bg_col)
        set_cell_margins(cell, top=100, bottom=100, left=80, right=80)

        tc_pr = cell._tc.get_or_add_tcPr()
        borders = parse_xml(
            f'<w:tcBorders {nsdecls("w")}>'
            f'<w:top w:val="single" w:sz="12" w:space="0" w:color="{border_col}"/>'
            f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{border_col}"/>'
            f'<w:bottom w:val="single" w:sz="12" w:space="0" w:color="{border_col}"/>'
            f'<w:right w:val="single" w:sz="12" w:space="0" w:color="{border_col}"/>'
            f'</w:tcBorders>'
        )
        tc_pr.append(borders)

        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)

        r_tag = p.add_run(f"[{tag}]\n")
        r_tag.bold = True
        r_tag.font.size = Pt(7)
        r_tag.font.color.rgb = COLOR_SECONDARY

        r_lbl = p.add_run(label)
        r_lbl.bold = True
        r_lbl.font.size = Pt(8.5)
        r_lbl.font.color.rgb = COLOR_DARK

        if detail:
            r_det = p.add_run(f"\n{detail}")
            r_det.font.size = Pt(7.5)
            r_det.font.italic = True
            r_det.font.color.rgb = COLOR_MUTED

    doc.add_paragraph().paragraph_format.space_after = Pt(6)


def format_table_header(row, titles: List[str], hex_bg=HEX_NAVY):
    """Format row as a stylized table header."""
    for idx, cell in enumerate(row.cells):
        cell.text = ""
        set_cell_background(cell, hex_bg)
        set_cell_margins(cell, top=140, bottom=140, left=140, right=140)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(titles[idx])
        run.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = COLOR_WHITE


def format_table_cells(table, zebra=True):
    """Apply borders and font styling across standard table rows."""
    for r_idx, row in enumerate(table.rows[1:]):
        bg = HEX_LIGHT_BLUE if (zebra and r_idx % 2 == 1) else "FFFFFF"
        for cell in row.cells:
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
            for p in cell.paragraphs:
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                p.paragraph_format.line_spacing = 1.15
                for run in p.runs:
                    run.font.size = Pt(9)
                    run.font.color.rgb = COLOR_DARK


def generate_leskode_sow(content: Dict[str, Any], output_path: str) -> str:
    """
    Generate an authentic, complete Leskode SOW document from structured project content,
    strictly adhering to the 4-page SOW Flow Template and 23-page reference SOW.
    """
    doc = Document()

    # Set page margins: 0.8 inch
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

        # Header
        header_p = section.header.paragraphs[0]
        header_p.text = "Leskode | Zoho Advanced Partner"
        header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        header_p.style.font.size = Pt(8.5)
        header_p.style.font.color.rgb = COLOR_MUTED

        # Footer
        footer_p = section.footer.paragraphs[0]
        footer_p.text = "Confidential — Leskode | Prepared by Monish | Contact: +91 9500424307"
        footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_p.style.font.size = Pt(8.5)
        footer_p.style.font.color.rgb = COLOR_MUTED

    client_name = content.get("client_name", "Valued Client")
    project_name = content.get("project_name", "Zoho Implementation")
    solution_title = content.get("solution_title", "Zoho Business Management Implementation")
    app_line = content.get("application_line", "Zoho One (CRM, Books, Inventory, Desk, Flow, Analytics)")
    business_one_liner = content.get("business_one_liner", "Enterprise Operations & Business Automation")
    version_date = content.get("version_date", "Version 1.0 | October 2026")
    prepared_by = content.get("prepared_by") or "Leskode Solutions Team"
    contact_phone = "+91 9500424307"

    # ─── SECTION 1: COVER PAGE ──────────────────────────────────────────────────
    doc.add_paragraph().paragraph_format.space_before = Pt(70)

    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_after = Pt(8)
    title_run = title_p.add_run("SCOPE OF WORK")
    title_run.font.size = Pt(32)
    title_run.font.bold = True
    title_run.font.color.rgb = COLOR_PRIMARY
    title_p.alignment = WD_ALIGN_PARAGRAPH.LEFT

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(28)
    sub_run = sub_p.add_run(solution_title)
    sub_run.font.size = Pt(18)
    sub_run.font.color.rgb = COLOR_SECONDARY
    sub_run.font.bold = True

    prep_p = doc.add_paragraph()
    prep_p.paragraph_format.space_after = Pt(4)
    prep_run = prep_p.add_run("Prepared for")
    prep_run.font.size = Pt(11)
    prep_run.font.color.rgb = COLOR_MUTED

    client_p = doc.add_paragraph()
    client_p.paragraph_format.space_after = Pt(8)
    client_run = client_p.add_run(client_name)
    client_run.font.size = Pt(22)
    client_run.font.bold = True
    client_run.font.color.rgb = COLOR_PRIMARY

    desc_p = doc.add_paragraph()
    desc_p.paragraph_format.space_after = Pt(36)
    desc_run = desc_p.add_run(business_one_liner)
    desc_run.font.size = Pt(11)
    desc_run.font.italic = True
    desc_run.font.color.rgb = COLOR_MUTED

    by_p = doc.add_paragraph()
    by_p.paragraph_format.space_after = Pt(4)
    by_run = by_p.add_run("Implemented by")
    by_run.font.size = Pt(11)
    by_run.font.color.rgb = COLOR_MUTED

    leskode_p = doc.add_paragraph()
    leskode_p.paragraph_format.space_after = Pt(6)
    leskode_run = leskode_p.add_run("Leskode")
    leskode_run.font.size = Pt(24)
    leskode_run.font.bold = True
    leskode_run.font.color.rgb = COLOR_PRIMARY

    shavs_p = doc.add_paragraph()
    shavs_p.paragraph_format.space_after = Pt(60)
    shavs_run = shavs_p.add_run("Shavs Technologies Pvt Ltd  |  Zoho Advanced Partner")
    shavs_run.font.size = Pt(10)
    shavs_run.font.bold = True
    shavs_run.font.color.rgb = COLOR_SECONDARY

    meta_p = doc.add_paragraph()
    meta_p.paragraph_format.space_after = Pt(0)
    meta_run = meta_p.add_run(f"{version_date}  •  Prepared by {prepared_by}  •  Contact: {contact_phone}")
    meta_run.font.size = Pt(9.5)
    meta_run.font.color.rgb = COLOR_MUTED

    doc.add_page_break()

    # ─── SECTION 2: CONFIDENTIALITY NOTICE (LOCKED WORDING PART 4, A) ───────────
    h2 = doc.add_heading("Confidentiality Notice", level=1)
    h2.runs[0].font.color.rgb = COLOR_PRIMARY

    notice_p = doc.add_paragraph()
    notice_p.paragraph_format.space_after = Pt(8)
    notice_p.paragraph_format.line_spacing = 1.15
    notice_p.add_run(
        f'This document and its contents are confidential and constitute the proprietary information of Leskode ("Leskode," '
        f'"we," or "us"). It has been prepared exclusively for {client_name} (the "Customer") for the sole purpose of describing the '
        f'proposed Zoho implementation scope, approach, and commercial basis for the Customer\'s engagement. No part of this '
        f'document may be used for any purpose other than the evaluation of the proposed engagement, nor may it be copied, '
        f'reproduced, disclosed, or distributed, in whole or in part, to any third party without Leskode\'s prior written consent.'
    )

    bullets = [
        ("Restricted Use", "The contents of this document are intended solely for internal review by the Customer's authorised personnel in connection with the evaluation of this proposal."),
        ("No Distribution", "This document, or any information derived from it, shall not be disclosed, published, or shared with any third party without Leskode's prior written authorisation."),
        ("Acknowledgement by Review", "Any recipient who reviews this document is deemed to have accepted the confidentiality obligations set out herein."),
        ("Pricing Confidentiality", "The costing, rate, and effort information contained in this proposal is commercially sensitive and must not be shared with any third party, including other vendors, without Leskode's prior written consent.")
    ]
    for bold_prefix, text in bullets:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(4)
        r_bold = bp.add_run(f"{bold_prefix}: ")
        r_bold.bold = True
        r_bold.font.color.rgb = COLOR_PRIMARY
        r_text = bp.add_run(text)
        r_text.font.size = Pt(9.5)

    cp = doc.add_paragraph()
    cp.paragraph_format.space_before = Pt(8)
    cp.paragraph_format.space_after = Pt(18)
    cr = cp.add_run("Closing line: By retaining or reviewing this document, the recipient acknowledges and agrees to the terms of this Confidentiality Notice.")
    cr.font.italic = True
    cr.font.size = Pt(9)
    cr.font.color.rgb = COLOR_MUTED

    # ─── SECTION 3: PROJECT INFORMATION TABLE ───────────────────────────────────
    h3 = doc.add_heading("Project Information", level=1)
    h3.runs[0].font.color.rgb = COLOR_PRIMARY

    info_tbl = doc.add_table(rows=5, cols=2)
    info_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    format_table_header(info_tbl.rows[0], ["Implementation Parameter", "Project Details"])

    rows_info = [
        ("Project Name", project_name),
        ("Client Organization", f"{client_name} ({business_one_liner})"),
        ("Zoho Applications in Scope", app_line),
        ("Implementation Partner", "Leskode (Shavs Technologies Pvt Ltd), Coimbatore\nLead Contact: Vaishnavi T, +91 9500424307\nPrepared by: Monish"),
    ]
    for idx, (param, val) in enumerate(rows_info, start=1):
        info_tbl.rows[idx].cells[0].text = param
        info_tbl.rows[idx].cells[0].paragraphs[0].runs[0].bold = True
        info_tbl.rows[idx].cells[1].text = val
    format_table_cells(info_tbl, zebra=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # ─── SECTION 4: BACKGROUND & OBJECTIVE (THREE PARTS + OBJECTIVE CALLOUT) ────
    h4 = doc.add_heading("1. Executive Summary & Business Objective", level=1)
    h4.runs[0].font.color.rgb = COLOR_PRIMARY

    # Part 1: What client does
    bg_text = content.get(
        "business_background",
        f"{client_name} is a leading enterprise engaged in commercial operations, manufacturing, and distribution. "
        "The organization currently manages inquiries, quotations, customer communications, orders, and financial transactions across disparate channels, spreadsheets, and legacy tools."
    )
    p_bg = doc.add_paragraph(bg_text)
    p_bg.paragraph_format.space_after = Pt(8)
    p_bg.paragraph_format.line_spacing = 1.15

    # Part 2: What is being set up
    setup_text = content.get(
        "setup_description",
        f"This implementation establishes a unified, cloud-based business architecture on the Zoho platform ({app_line}). "
        "The system standardizes master records, automates multi-stage workflows from lead intake through quotation, order fulfillment, invoicing, and inventory control, providing management with real-time operational visibility."
    )
    p_setup = doc.add_paragraph(setup_text)
    p_setup.paragraph_format.space_after = Pt(12)
    p_setup.paragraph_format.line_spacing = 1.15

    # Part 3: Objective callout box
    obj_text = content.get(
        "business_objectives",
        f"Deploy an integrated Zoho ecosystem for {client_name} that eliminates duplicate data entry, enforces pricing discipline, accelerates order-to-cash velocity, and delivers accurate real-time inventory and financial reporting."
    )
    create_callout_box(doc, "Objective", obj_text, border_hex="102C57", bg_hex="F0F4F8")

    # ─── SECTION 5: OVERALL PROCESS FLOW (PART 3 MASTER FLOW & APPS TABLE) ──────
    h5 = doc.add_heading("2. Overall Process Flow & Application Architecture", level=1)
    h5.runs[0].font.color.rgb = COLOR_PRIMARY

    doc.add_paragraph(
        "The following master process flow defines the spine of operations across the Zoho ecosystem. "
        "Fixed stages appear in all standard implementations; optional and variable stages are tailored to "
        f"{client_name}'s specific business model:"
    ).paragraph_format.space_after = Pt(6)

    # Part 3 Master Process Flow Spine
    spine_stages = content.get("master_flow_spine", [
        ("1", "Lead source", "Variable", "Google Ads, FB Ads, Website Forms, WhatsApp, Walk-in, Dealer / Referral ('Lead Chain' where ads/forms feed CRM)"),
        ("2", "Lead captured in Zoho CRM", "Fixed", "Field validation, duplicate deduplication, automated classification & sales rep assignment rules"),
        ("3", "Follow-up and qualification", "Fixed", "First call / site visit checklist, client profiling, requirement capture"),
        ("4", "Contact / Account & Deal created", "Fixed", "Account master creation, contact persons, multi-stage opportunity pipeline"),
        ("5", "Pre-sale step", "Optional", "Technical site survey, BOQ estimation, branch assignment"),
        ("6", "Quotation and approval", "Optional", "Standard & tiered price books, margin verification, discount floor approval limits"),
        ("7", "Conversion", "Fixed", "Closed Won / order confirmed event triggers downstream Books and Inventory flows"),
        ("8", "Fulfilment", "Variable", "Production execution, mill batch / heat tracking, dispatch & delivery notes (Core Operational Flow)"),
        ("9", "Procurement and stock", "Optional", "Vendor POs, inward Goods Receipts (GRN), multi-godown stock updates, low-stock triggers"),
        ("10", "Invoicing and payments", "Optional", "Tax invoicing from accepted orders, GST e-invoicing/e-way bill, automated payment reminders"),
        ("11", "After-sales", "Optional", "Warranty tracking, customer support tickets, service SLAs & AMC renewals"),
        ("12", "Dashboards and reports", "Fixed", "Executive management dashboards, pipeline velocity, accounts aging, stock turnover")
    ])

    spine_tbl = doc.add_table(rows=len(spine_stages) + 1, cols=4)
    spine_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    format_table_header(spine_tbl.rows[0], ["#", "Master Process Stage", "Type", "Scope & Client Variable Configuration"])
    for i, (num, stg, stype, detail) in enumerate(spine_stages, start=1):
        spine_tbl.rows[i].cells[0].text = num
        spine_tbl.rows[i].cells[1].text = stg
        spine_tbl.rows[i].cells[1].paragraphs[0].runs[0].bold = True
        spine_tbl.rows[i].cells[2].text = stype
        spine_tbl.rows[i].cells[3].text = detail
    format_table_cells(spine_tbl, zebra=True)

    # Locked Running Note under every stage
    p_run = doc.add_paragraph()
    p_run.paragraph_format.space_before = Pt(6)
    p_run.paragraph_format.space_after = Pt(12)
    r_run = p_run.add_run("Running under every stage: roles and access, notifications and escalation, integrations, approvals, audit trail, mobile access and documents.")
    r_run.font.italic = True
    r_run.font.size = Pt(8.5)
    r_run.font.color.rgb = COLOR_MUTED

    # Table of Zoho Applications and their Roles
    doc.add_heading("2.1 Zoho Applications and Roles", level=2)
    app_roles = content.get("application_roles", [
        ("Zoho CRM", "Sales pipeline, lead intake, quotation management, customer communication history"),
        ("Zoho Books", "Statutory financial accounting, GST e-invoicing, vendor billing, banking reconciliation, receivables"),
        ("Zoho Inventory", "Multi-warehouse stock visibility, batch tracking, purchase orders, goods receipt notes (GRN)"),
        ("Zoho Desk / Service", "Customer support inquiries, warranty handling, ticketing SLAs, service technician assignment"),
        ("Zoho Flow", "Automated real-time event triggers and bidirectional webhooks between Zoho and third-party apps"),
        ("Zoho Analytics", "Cross-application business intelligence, executive dashboarding, margin & cash flow KPIs")
    ])
    app_tbl = doc.add_table(rows=len(app_roles) + 1, cols=2)
    app_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    format_table_header(app_tbl.rows[0], ["Zoho Application", "Role in Customer Architecture"])
    for i, (app_name, role_desc) in enumerate(app_roles, start=1):
        app_tbl.rows[i].cells[0].text = app_name
        app_tbl.rows[i].cells[0].paragraphs[0].runs[0].bold = True
        app_tbl.rows[i].cells[1].text = role_desc
    format_table_cells(app_tbl, zebra=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ─── SECTION 6: PHASES OR MODULES (REPEATING PART 2 BLOCKS) ─────────────────
    h6 = doc.add_heading("3. Detailed Module Scope & Architecture", level=1)
    h6.runs[0].font.color.rgb = COLOR_PRIMARY

    modules_data = content.get("module_blocks", [
        {
            "name": "Lead Intake & Sales Pipeline Management",
            "modules_line": "Zoho CRM (Leads, Contacts, Accounts, Deals, Quotation, Activities)",
            "purpose": "Captures inbound enquiries across digital and offline channels, tracks them through the pipeline to a confirmed order, and initiates fulfillment without manual handoff.",
            "flow_steps": [
                {"type": "START", "label": "Enquiry Received", "detail": "Webform / Ads / WhatsApp"},
                {"type": "PROCESS", "label": "De-duplication & Assign", "detail": "Round-robin assignment"},
                {"type": "DECISION", "label": "Qualified Lead?", "detail": "Yes / No condition"},
                {"type": "WARNING", "label": "Quote & Approval", "detail": "Check margin floor"},
                {"type": "END", "label": "Order Confirmed", "detail": "Convert to Books SO"}
            ],
            "bullets": [
                ("Lead Sources", "Captures website forms, social ads, WhatsApp enquiries, and direct phone calls with automated source tagging."),
                ("Duplicate Prevention", "Checks incoming mobile numbers and email addresses against active leads and accounts to prevent duplicate records."),
                ("Pipeline Stages", "Configures stages (New, Contacted, Qualified, Quote Sent, Negotiation, Won/Lost) with mandatory exit criteria."),
                ("Rate-Linked Quotation", "Generates standardized quotes pulling approved price lists and enforces approval thresholds for special discounts."),
                ("Order Conversion", "Marking a deal 'Closed Won' automatically creates the corresponding Sales Order in Zoho Books.")
            ],
            "note": "WhatsApp Business integration requires client-procured Meta Business credentials and approved message templates."
        },
        {
            "name": "Financial Accounting & Invoicing",
            "modules_line": "Zoho Books (Invoicing, Bills, Banking, GST, Landed Cost)",
            "purpose": "Acts as the financial and compliance backbone, handling tax invoicing, three-way vendor matching, banking feeds, and statutory GST reporting.",
            "flow_steps": [
                {"type": "START", "label": "Sales Order Synced", "detail": "From Zoho CRM"},
                {"type": "PROCESS", "label": "Tax Invoice Generated", "detail": "HSN & GST auto-applied"},
                {"type": "DECISION", "label": "Credit Limit OK?", "detail": "Overdue balance check"},
                {"type": "PROCESS", "label": "Dispatch & e-Way Bill", "detail": "NIC portal push"},
                {"type": "END", "label": "Payment Reconciled", "detail": "Bank statement matched"}
            ],
            "bullets": [
                ("Automated Invoicing", "Invoices created directly from accepted sales orders with automatic GST calculation, TCS/TDS rules, and e-invoice generation."),
                ("Vendor PO & Bills", "Three-way matching between Purchase Orders, Goods Receipt Notes, and Vendor Bills to prevent invoice leakage."),
                ("Receivables Follow-up", "Automated email and SMS payment reminder escalations for overdue customer accounts."),
                ("Banking Reconciliation", "Direct bank statement import and automated transaction matching rules."),
                ("Financial Statements", "Real-time generation of Trial Balance, Profit & Loss statements, Balance Sheet, and GST audit returns.")
            ],
            "note": "Direct automated bank feed depends on individual financial institution API availability."
        },
        {
            "name": "Inventory & Warehouse Management",
            "modules_line": "Zoho Inventory (Items, Warehouses, Stock Adjustments, Goods Receipt)",
            "purpose": "Controls physical inventory across godowns, manages stock adjustments, batch/heat numbers, and provides accurate cost valuation.",
            "flow_steps": [
                {"type": "START", "label": "Purchase Order Raised", "detail": "Procurement team"},
                {"type": "PROCESS", "label": "Goods Receipt (GRN)", "detail": "Physical inspection"},
                {"type": "CHECK", "label": "Batch / Quality Check", "detail": "Mill test certificates"},
                {"type": "PROCESS", "label": "Godown Bin Allocation", "detail": "Stock inward entry"},
                {"type": "END", "label": "Available for Sale", "detail": "Real-time sync to CRM"}
            ],
            "bullets": [
                ("Item Master", "Standardized SKU catalog with multi-unit conversions (units, packets, metric tonnes) and reorder thresholds."),
                ("Multi-Godown Visibility", "Location-wise stock tracking across main yards and processing centers with inter-godown transfer orders."),
                ("Batch / Heat Traceability", "Tracking manufacturer heat numbers, test certificate references, and aging on stock inward."),
                ("Reorder Automation", "Automatic alerts to procurement managers when inventory falls below minimum safety thresholds."),
                ("Dispatch Documentation", "Generation of Packing Slips and Delivery Challans linked directly to Books invoices.")
            ],
            "note": "Hardware procurement (barcode scanners, label printers, mobile rugged terminals) is outside software implementation scope."
        }
    ])

    for m_idx, mod in enumerate(modules_data, start=1):
        # Heading bar: PHASE n – {Name} (Part 2, a)
        doc.add_heading(f"PHASE {m_idx} – {mod['name']}", level=2)

        # Modules line: Zoho Modules: {applications and modules used} (Part 2, b)
        p_line = doc.add_paragraph()
        r_line_label = p_line.add_run("Zoho Modules: ")
        r_line_label.bold = True
        r_line_label.font.color.rgb = COLOR_SECONDARY
        r_line_val = p_line.add_run(mod["modules_line"])
        r_line_val.font.size = Pt(9.5)

        # Purpose: One or two sentences (Part 2, c)
        p_purp = doc.add_paragraph()
        p_purp.paragraph_format.space_after = Pt(6)
        r_purp_l = p_purp.add_run("Purpose: ")
        r_purp_l.bold = True
        p_purp.add_run(mod["purpose"])

        # Flow figure (Part 2, d)
        if mod.get("flow_steps"):
            create_flow_figure(doc, mod["flow_steps"])

        # Bullets: 3 to 5, each with bold lead word and one sentence (Part 2, e)
        for bold_lead, sentence in mod["bullets"]:
            bp = doc.add_paragraph(style='List Bullet')
            bp.paragraph_format.space_after = Pt(2)
            r_lead = bp.add_run(f"{bold_lead}: ")
            r_lead.bold = True
            r_lead.font.color.rgb = COLOR_PRIMARY
            bp.add_run(sentence)

        # Note: One callout for anything excluded or dependent on edition (Part 2, g)
        if mod.get("note"):
            create_callout_box(doc, "Note", mod["note"], border_hex="35598E", bg_hex="F8FAFC")
        else:
            doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ─── SECTION 7: ROLES, ACCESS & NOTIFICATIONS ───────────────────────────────
    h7 = doc.add_heading("4. Roles, Permissions & Notification Triggers", level=1)
    h7.runs[0].font.color.rgb = COLOR_PRIMARY

    doc.add_paragraph(
        "User permissions follow a strict role-based access matrix. Each role accesses only designated modules and data:"
    ).paragraph_format.space_after = Pt(4)

    roles_data = content.get("roles", [
        ("Administrator / Owner", "Full Access across all applications, rate approvals, user administration", "Super Admin"),
        ("Sales Executive", "Lead creation, Deal pipeline, Quotation generation", "Standard Read/Write (CRM)"),
        ("Accounts Manager", "Invoicing, Vendor Bills, Bank Reconciliation, GST Reports", "Finance Admin (Books)"),
        ("Warehouse / Stores Supervisor", "Stock receiving (GRN), dispatch confirmation, inventory adjustments", "Operations (Inventory)"),
    ])

    role_tbl = doc.add_table(rows=len(roles_data) + 1, cols=3)
    role_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    format_table_header(role_tbl.rows[0], ["Role", "System Access Scope", "Permission Level"])
    for i, (r, acc, lvl) in enumerate(roles_data, start=1):
        role_tbl.rows[i].cells[0].text = r
        role_tbl.rows[i].cells[0].paragraphs[0].runs[0].bold = True
        role_tbl.rows[i].cells[1].text = acc
        role_tbl.rows[i].cells[2].text = lvl
    format_table_cells(role_tbl, zebra=True)

    notif_p = doc.add_paragraph()
    notif_p.paragraph_format.space_before = Pt(8)
    notif_p.paragraph_format.space_after = Pt(14)
    r_notif = notif_p.add_run(
        "Event Notifications: Triggered on New Deal Confirmation, Below-Floor Discount Request, Low Stock Alert, Overdue Invoice, and Quality Inspection Rejection."
    )
    r_notif.font.size = Pt(9)
    r_notif.font.italic = True
    r_notif.font.color.rgb = COLOR_MUTED

    # ─── SECTION 8: INTEGRATION SCOPE TABLE ─────────────────────────────────────
    h8 = doc.add_heading("5. Integration Scope", level=1)
    h8.runs[0].font.color.rgb = COLOR_PRIMARY

    doc.add_paragraph(
        "The following integrations will be configured as part of this engagement. Native connectors are used where available; Zoho Flow or REST APIs otherwise:"
    ).paragraph_format.space_after = Pt(6)

    int_data = content.get("integrations", [
        ("CRM ↔ Books", "Bidirectional", "Native Zoho Integration", "Available — standard synchronization of accounts, contacts, and transactions"),
        ("Books ↔ Inventory", "Bidirectional", "Native Zoho Integration", "Available — real-time stock sync and purchase receive inwarding"),
        ("Website Forms → CRM", "Inbound", "Zoho Forms / Webhooks", "Available — website lead capture with instant attribution"),
        ("Books → GST Portal", "Outbound", "Native Zoho Books e-Way / e-Invoice", "Available — requires client GST portal API credentials"),
        ("CRM / Books → Analytics", "Outbound", "Native Zoho Analytics Connectors", "Available — automated periodic synchronization"),
        ("WhatsApp Business ↔ CRM", "Bidirectional", "WhatsApp Business Integration", "Subject to client Meta WhatsApp Business API credentials")
    ])

    int_tbl = doc.add_table(rows=len(int_data) + 1, cols=4)
    int_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    format_table_header(int_tbl.rows[0], ["Integration", "Direction", "Method", "Condition / Purpose"])
    for i, (it, d, m, c) in enumerate(int_data, start=1):
        int_tbl.rows[i].cells[0].text = it
        int_tbl.rows[i].cells[0].paragraphs[0].runs[0].bold = True
        int_tbl.rows[i].cells[1].text = d
        int_tbl.rows[i].cells[2].text = m
        int_tbl.rows[i].cells[3].text = c
    format_table_cells(int_tbl, zebra=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ─── SECTION 9: DELIVERABLES SUMMARY TABLE ──────────────────────────────────
    h9 = doc.add_heading("6. Deliverables Summary", level=1)
    h9.runs[0].font.color.rgb = COLOR_PRIMARY

    deliv_data = content.get("deliverables", [
        ("Phase 1: Discovery & Architecture", "Architecture blueprint, field schema dictionary, pipeline stages definition, and UAT acceptance criteria."),
        ("Phase 2: Zoho CRM Setup", "Configured lead-to-deal pipeline, customer tiers, rate-linked quotes, activity management, and executive sales reports."),
        ("Phase 3: Zoho Books Setup", "Chart of accounts, GST invoicing with e-invoice/e-way bill, category price lists, vendor POs, banking, and P&L statements."),
        ("Phase 4: Zoho Inventory Setup", "Standardized item master, multi-godown stock tracking, reorder thresholds, and goods receipt note (GRN) workflow."),
        ("Phase 5: Integrations & Testing", "Native synchronization across CRM, Books, Inventory, and Analytics plus configured website intake forms."),
        ("Phase 6: Training & Handover", "Role-based training sessions for sales, accounts, and stores teams with recorded training videos and SOP guide.")
    ])

    deliv_tbl = doc.add_table(rows=len(deliv_data) + 1, cols=2)
    deliv_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    format_table_header(deliv_tbl.rows[0], ["Phase / Deliverable", "Description"])
    for i, (d, desc) in enumerate(deliv_data, start=1):
        deliv_tbl.rows[i].cells[0].text = d
        deliv_tbl.rows[i].cells[0].paragraphs[0].runs[0].bold = True
        deliv_tbl.rows[i].cells[1].text = desc
    format_table_cells(deliv_tbl, zebra=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ─── SECTION 10: IMPLEMENTATION TIMELINE + LOCKED NOTE B ────────────────────
    h10 = doc.add_heading("7. Implementation Timeline", level=1)
    h10.runs[0].font.color.rgb = COLOR_PRIMARY

    doc.add_paragraph(
        f"The implementation is scheduled over an estimated duration of 8–10 weeks from project kickoff. "
        "Work proceeds in structured stages as outlined below:"
    ).paragraph_format.space_after = Pt(6)

    timeline_data = content.get("timeline", [
        ("Stage 1", "Requirement Discovery & Process Mapping", "1–2 Weeks", "Process review, field schema finalization, price rule definition, and UAT plan"),
        ("Stage 2", "Zoho CRM & Intake Setup", "2–3 Weeks", "Lead stages, deal pipeline, quote templates, user permissions, and webform integration"),
        ("Stage 3", "Zoho Books & Accounting Setup", "2–3 Weeks", "Chart of accounts, GST configuration, invoice formats, landed cost, and bank sync"),
        ("Stage 4", "Zoho Inventory & Warehouse Setup", "2 Weeks", "Item master, godown locations, stock adjustment rules, and PO-to-GRN flow"),
        ("Stage 5", "Integration Testing & Validation", "1–2 Weeks", "End-to-end data flow validation, API regression checks, and notification tests"),
        ("Stage 6", "UAT, Team Training & Go-Live", "1–2 Weeks", "User acceptance testing, role-based training sessions, SOP review, and production rollout")
    ])

    time_tbl = doc.add_table(rows=len(timeline_data) + 2, cols=4)
    time_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    format_table_header(time_tbl.rows[0], ["Stage", "Stage Description", "Duration", "Key Activities"])
    for i, (st, p_desc, dur, act) in enumerate(timeline_data, start=1):
        time_tbl.rows[i].cells[0].text = st
        time_tbl.rows[i].cells[1].text = p_desc
        time_tbl.rows[i].cells[1].paragraphs[0].runs[0].bold = True
        time_tbl.rows[i].cells[2].text = dur
        time_tbl.rows[i].cells[3].text = act

    # Summary Total Row (Part 1, #10: "the total must add up")
    total_row = time_tbl.rows[len(timeline_data) + 1]
    total_row.cells[0].text = "TOTAL"
    total_row.cells[1].text = "Total Estimated Project Duration"
    total_row.cells[2].text = content.get("total_duration", "8–10 Weeks")
    total_row.cells[3].text = "Execution across discovery, module build, validation, and rollout"
    for c in total_row.cells:
        set_cell_background(c, HEX_LIGHT_BLUE)
        c.paragraphs[0].runs[0].bold = True
    format_table_cells(time_tbl, zebra=False)

    # Locked Timeline Note B
    p_tn = doc.add_paragraph()
    p_tn.paragraph_format.space_before = Pt(8)
    p_tn.paragraph_format.space_after = Pt(14)
    r_tn = p_tn.add_run(
        "Timeline note: The timeline does not include data migration. It assumes timely client inputs, availability of the "
        "client team for workshops and UAT, and timely UAT feedback. Delays or scope changes will be assessed and communicated formally."
    )
    r_tn.font.italic = True
    r_tn.font.size = Pt(9)
    r_tn.font.color.rgb = COLOR_MUTED

    # ─── SECTION 11: POST-IMPLEMENTATION SUPPORT (LOCKED WORDING PART 4, C) ─────
    h11 = doc.add_heading("8. Post-Implementation Support", level=1)
    h11.runs[0].font.color.rgb = COLOR_PRIMARY

    support_audience = content.get("training_audience", f"{client_name}'s management, sales, accounts, and operations personnel")
    support_items = [
        ("Testing", "End-to-end tests across the applications before UAT."),
        ("UAT", "Your team tests against real scenarios; sign-off is expected within 5–7 business days of test delivery."),
        ("Training", f"Role-based training for {support_audience}, and a user guide."),
        ("Go-live and hypercare", "Issue resolution during go-live and the hypercare period of [length to be decided]. Support beyond hypercare is available under a separate support agreement / AMC.")
    ]
    for b_lead, b_text in support_items:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(4)
        r_l = bp.add_run(f"{b_lead}: ")
        r_l.bold = True
        r_l.font.color.rgb = COLOR_PRIMARY
        bp.add_run(b_text)
    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # ─── SECTION 12: NOTES (LOCKED WORDING PART 4, D) ───────────────────────────
    h12 = doc.add_heading("9. General Notes", level=1)
    h12.runs[0].font.color.rgb = COLOR_PRIMARY

    notes = [
        ("Zoho edition", "Blueprint, approvals, assignment rules, validation rules and field-level security are Enterprise edition features. Where the edition lacks a feature, an equivalent is set up as far as possible. The edition is confirmed in the licence advisory."),
        ("Licences", "Zoho licences are bought by the client before the build starts."),
        ("Third-party tools", "{Lead Chain, WhatsApp, payment gateway and similar} are arranged by the client; their subscriptions and charges are not included."),
        ("Dashboards", "Only the default dashboards are included. A specific dashboard is added only after its feasibility is checked with our developer and the timeline is confirmed."),
        ("Data migration", "Not included. Once development is complete, the timeline and estimate for migration are shared based on the final fields and development, and migration is taken up as a change request."),
        ("Regulatory matters", "Registrations, disclosures, contracts and compliance with applicable rules and data protection are the client's responsibility; Leskode does not give legal or regulatory advice."),
        ("Change requests", "Changes to this scope are handled through a formal Change Request and may affect timeline and cost.")
    ]
    for b_lead, b_text in notes:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(4)
        r_l = bp.add_run(f"{b_lead}: ")
        r_l.bold = True
        r_l.font.color.rgb = COLOR_PRIMARY
        bp.add_run(b_text)
    doc.add_paragraph().paragraph_format.space_after = Pt(10)

    # ─── SECTION 13 & 14: ASSUMPTIONS & EXCLUSIONS ──────────────────────────────
    h13 = doc.add_heading("10. Assumptions & Exclusions", level=1)
    h13.runs[0].font.color.rgb = COLOR_PRIMARY

    doc.add_heading("10.1 Assumptions", level=2)
    assumptions_list = content.get("assumptions", [
        "Licences in place; one coordinator for decisions and UAT.",
        "Existing master data (customers, vendors, items) will be provided in agreed CSV/Excel templates.",
        "Zoho application licences will be procured by the client prior to the start of each phase.",
        "API credentials for payment gateway, WhatsApp, and banking providers will be arranged by the client.",
        "UAT sign-off will be provided within 5–7 business days of test delivery."
    ])
    for item in assumptions_list:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        bp.add_run(item)

    doc.add_heading("10.2 Exclusions", level=2)
    exclusions_list = content.get("exclusions", [
        "Custom mobile app development outside standard Zoho mobile apps.",
        "Direct integration with proprietary weighbridge or on-premise legacy hardware.",
        "Hardware procurement (barcode scanners, label printers, biometric devices, workstations).",
        "Export invoicing and multi-currency accounting configuration.",
        "Post-go-live support beyond the agreed hypercare period (available under separate AMC)."
    ])
    for item in exclusions_list:
        bp = doc.add_paragraph(style='List Bullet')
        bp.paragraph_format.space_after = Pt(3)
        bp.add_run(item)

    # Locked Exclusions closing line E (Part 4, E)
    p_ex_close = doc.add_paragraph()
    p_ex_close.paragraph_format.space_before = Pt(4)
    p_ex_close.paragraph_format.space_after = Pt(4)
    r_ex_c = p_ex_close.add_run("Closing line: Data migration, hardware, and post-go-live support beyond hypercare.")
    r_ex_c.font.bold = True
    r_ex_c.font.color.rgb = COLOR_MUTED
    r_ex_c.font.size = Pt(9)

    # Optional enhancements line F (Part 4, F)
    enhancements_str = content.get("optional_enhancements", "WhatsApp Business automation, customer self-service portal, biometric attendance sync")
    p_opt = doc.add_paragraph()
    p_opt.paragraph_format.space_after = Pt(12)
    r_opt = p_opt.add_run(f"Optional enhancements line: Optional enhancements that can be added later through a change request: {enhancements_str}.")
    r_opt.font.italic = True
    r_opt.font.color.rgb = COLOR_MUTED
    r_opt.font.size = Pt(8.5)

    # ─── SECTION 15: POINTS TO CONFIRM ──────────────────────────────────────────
    h15 = doc.add_heading("11. Points to Confirm (Clarifications)", level=1)
    h15.runs[0].font.color.rgb = COLOR_PRIMARY

    doc.add_paragraph(
        "The following operational points require client confirmation prior to development kickoff:"
    ).paragraph_format.space_after = Pt(6)

    ptc_data = content.get("points_to_confirm", [
        ("Historical Data Volume", "Determines data cleansing and migration hours required if added via Change Request."),
        ("User Role Hierarchy & Approvers", "Defines the exact approval chains and discount floor authorization rules in CRM and Books."),
        ("Third-Party API Endpoints", "Determines Zoho Flow connector requirements versus custom Deluge webhook scripts."),
        ("GST / Invoicing Multi-Branch Setup", "Dictates the chart of accounts complexity and branch prefix configurations in Zoho Books.")
    ])

    ptc_tbl = doc.add_table(rows=len(ptc_data) + 1, cols=2)
    ptc_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    format_table_header(ptc_tbl.rows[0], ["Point to Confirm", "Why It Matters (Impact on SOW)"])
    for i, (pt, why) in enumerate(ptc_data, start=1):
        ptc_tbl.rows[i].cells[0].text = pt
        ptc_tbl.rows[i].cells[0].paragraphs[0].runs[0].bold = True
        ptc_tbl.rows[i].cells[1].text = why
    format_table_cells(ptc_tbl, zebra=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(14)

    # ─── SECTION 16: CLIENT INPUTS REQUIRED ─────────────────────────────────────
    h16 = doc.add_heading("12. Client Inputs Required", level=1)
    h16.runs[0].font.color.rgb = COLOR_PRIMARY

    inputs_data = content.get("client_inputs", [
        ("Zoho Super Admin Credentials", "Phase 1 & 2 (Initial Setup & Tenant Configuration)"),
        ("Item Master & Price Lists (Excel/CSV)", "Phase 2 & 4 (Item Master Configuration)"),
        ("Customer & Vendor Master Templates", "Phase 2 & 3 (CRM & Books Master Setup)"),
        ("Standard Quotation & Invoice Layouts / Logo", "Phase 2 & 3 (Template Customization)"),
        ("Designated Module Leads for Workshops", "All Phases (Requirement Review & UAT)")
    ])

    inp_tbl = doc.add_table(rows=len(inputs_data) + 1, cols=2)
    inp_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    format_table_header(inp_tbl.rows[0], ["Client Input / Artefact", "Used For (Phase)"])
    for i, (inp, ph) in enumerate(inputs_data, start=1):
        inp_tbl.rows[i].cells[0].text = inp
        inp_tbl.rows[i].cells[0].paragraphs[0].runs[0].bold = True
        inp_tbl.rows[i].cells[1].text = ph
    format_table_cells(inp_tbl, zebra=True)
    doc.add_paragraph().paragraph_format.space_after = Pt(16)

    # ─── SECTION 17: ACCEPTANCE & SIGN-OFF TABLE ────────────────────────────────
    h17 = doc.add_heading("13. Acceptance & Sign-Off", level=1)
    h17.runs[0].font.color.rgb = COLOR_PRIMARY

    doc.add_paragraph(
        "This Scope of Work is agreed and accepted by both parties. Any changes to the scope described in this "
        "document will be managed through a formal Change Request process and may affect timeline and cost."
    ).paragraph_format.space_after = Pt(8)

    sign_tbl = doc.add_table(rows=5, cols=2)
    sign_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    format_table_header(sign_tbl.rows[0], ["Implementation Partner (Leskode)", f"Customer ({client_name})"])

    sign_rows = [
        ("Authorized Signatory", ""),
        ("Name & Designation: Vaishnavi T, Director", "Name & Designation:"),
        ("Date:", "Date:"),
        ("Contact: +91 9500424307", "Contact:"),
    ]
    for idx, (les, cli) in enumerate(sign_rows, start=1):
        sign_tbl.rows[idx].cells[0].text = les
        sign_tbl.rows[idx].cells[0].paragraphs[0].runs[0].bold = True
        sign_tbl.rows[idx].cells[1].text = cli
        if idx == 1:
            sign_tbl.rows[idx].cells[0].paragraphs[0].paragraph_format.space_before = Pt(20)
            sign_tbl.rows[idx].cells[1].paragraphs[0].paragraph_format.space_before = Pt(20)

    format_table_cells(sign_tbl, zebra=False)

    p_sign_note = doc.add_paragraph()
    p_sign_note.paragraph_format.space_before = Pt(12)
    r_sn = p_sign_note.add_run(f"Confidential — Leskode  |  Prepared by {prepared_by}  |  Shavs Technologies Pvt Ltd, Coimbatore")
    r_sn.font.size = Pt(8.5)
    r_sn.font.color.rgb = COLOR_MUTED

    doc.save(output_path)
    return output_path
