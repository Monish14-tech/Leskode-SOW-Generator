"""
ScopePilot AI — Template-Preserving DOCX Generator
Generates SOW documents by populating a copy of the master DOCX template.
Preserves all formatting, styles, embedded logos, images, tables, headers, footers, and layout.
"""
import os
import re
import copy
import logging
import shutil
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    pass


def _normalize_token(token: str) -> str:
    """Normalize a placeholder token by stripping punctuation, whitespace, and lowercasing."""
    cleaned = re.sub(r"[\{\}\<\>\[\]_\-\s]", "", token)
    return cleaned.lower().strip()


def _resolve_canonical_key(norm: str) -> Optional[str]:
    """Map normalized placeholder token to canonical content key."""
    mappings = {
        # Client name
        "clientname": "client_name",
        "client": "client_name",
        "customername": "client_name",
        "customer": "client_name",
        "companyname": "client_name",
        "company": "client_name",
        "accountname": "client_name",

        # Prepared by
        "preparedby": "prepared_by",
        "preparedbyname": "prepared_by",
        "author": "prepared_by",
        "authorname": "prepared_by",
        "consultant": "prepared_by",
        "consultantname": "prepared_by",
        "preparedfor": "client_name",

        # Project name
        "projectname": "project_name",
        "projecttitle": "project_name",
        "project": "project_name",
        "title": "project_name",

        # Dates
        "projectdate": "project_date",
        "date": "project_date",
        "prepareddate": "prepared_date",
        "today": "project_date",

        # Solution & Setup
        "solutiontitle": "solution_title",
        "solution": "solution_title",
        "proposedsolution": "setup_description",
        "setupdescription": "setup_description",
        "setup": "setup_description",
        "businessoneliner": "business_one_liner",
        "oneliner": "business_one_liner",

        # Application line
        "applicationline": "application_line",
        "zohoapplications": "application_line",
        "zohoapps": "application_line",
        "modulesline": "application_line",

        # Background & Objectives
        "businessbackground": "business_background",
        "background": "business_background",
        "executivesummary": "business_background",
        "businessobjectives": "business_objectives",
        "objectives": "business_objectives",
        "projectobjectives": "business_objectives",

        # Modules & Scope
        "modulescope": "module_scope",
        "modules": "module_scope",
        "moduleblocks": "module_scope",
        "scopeofwork": "module_scope",
        "scope": "module_scope",
        "tasks": "module_scope",
        "tasksandsubtasks": "module_scope",
        "zohomodules": "module_scope",

        # Integrations
        "integrations": "integrations",
        "integrationmatrix": "integrations",
        "integration": "integrations",

        # Deliverables
        "deliverables": "deliverables",
        "projectdeliverables": "deliverables",
        "deliverablesmatrix": "deliverables",
        "acceptancecriteria": "acceptance_criteria",

        # Assumptions & Exclusions
        "assumptions": "assumptions",
        "projectassumptions": "assumptions",
        "exclusions": "exclusions",
        "projectexclusions": "exclusions",
        "pointstoconfirm": "points_to_confirm",
        "clarifications": "points_to_confirm",
        "pendingclarifications": "points_to_confirm",

        # Timeline & Audience
        "trainingaudience": "training_audience",
        "audience": "training_audience",
        "totalduration": "total_duration",
        "projecttimeline": "total_duration",
        "timeline": "total_duration",
        "duration": "total_duration",

        # Version
        "version": "version_date",
        "versiondate": "version_date",
    }
    return mappings.get(norm)


def _format_module_blocks(module_blocks: List[Any]) -> str:
    """Format module blocks into clear, bulleted scope text."""
    if not module_blocks:
        return "1. Zoho CRM: Customer relationship management, lead pipeline tracking, and sales communication.\n2. Zoho Books: Chart of accounts, GST invoicing, and financial reconciliation."

    lines = []
    for idx, mb in enumerate(module_blocks, 1):
        if isinstance(mb, dict):
            name = mb.get("name") or mb.get("modules_line") or f"Module {idx}"
            purpose = mb.get("purpose", "")
            lines.append(f"{idx}. {name}: {purpose}")
            for lead, detail in mb.get("bullets", []):
                lines.append(f"   • {lead}: {detail}")
        else:
            lines.append(f"{idx}. {mb}")
    return "\n".join(lines)


def _format_integrations(integrations: List[Any]) -> str:
    """Format integrations into bulleted text."""
    if not integrations:
        return "• Zoho CRM ↔ Zoho Books: Native synchronization for customer, item, and sales order data.\n• Website Forms → Zoho CRM: Instant lead capture with attribution tracking."

    lines = []
    for item in integrations:
        if isinstance(item, (list, tuple)) and len(item) >= 4:
            lines.append(f"• {item[0]} ({item[1]} via {item[2]}): {item[3]}")
        else:
            lines.append(f"• {item}")
    return "\n".join(lines)


def _format_deliverables(deliverables: List[Any]) -> str:
    """Format deliverables into numbered text."""
    if not deliverables:
        return "1. Configured Zoho Environment (Format: Live System) — Validated against agreed modules.\n2. User Acceptance Sign-off (Format: DOCX/PDF) — Formally accepted by client SPOC."

    lines = []
    for item in deliverables:
        if isinstance(item, (list, tuple)) and len(item) >= 4:
            lines.append(f"{item[0]}. {item[1]} (Format: {item[2]}) — {item[3]}")
        else:
            lines.append(f"• {item}")
    return "\n".join(lines)


def _format_list(items: List[Any]) -> str:
    """Format a list of strings as bullet points."""
    if not items:
        return "• All Zoho subscriptions procured directly by the client."
    return "\n".join([f"• {item}" if not str(item).startswith("•") else str(item) for item in items])


def _format_points_to_confirm(ptc: List[Any]) -> str:
    """Format clarifications into bullet points."""
    if not ptc:
        return "• Historical Data Volume: Determines migration scope.\n• Approval Roles: Dictates discount floor authorization."
    lines = []
    for item in ptc:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            lines.append(f"• {item[0]}: {item[1]}")
        else:
            lines.append(f"• {item}")
    return "\n".join(lines)


def _build_replacements(content: Dict[str, Any], placeholder_map: Dict[str, str]) -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Build comprehensive replacements dictionary supporting:
    - Double braces {{KEY}}
    - Angle brackets <<KEY>>
    - Square brackets [KEY]
    - Single braces {KEY}
    - Case variations and sample SOW text replacements.
    """
    today = datetime.now().strftime("%d %B %Y")
    client_name = content.get("client_name") or "Valued Client"
    prepared_by = content.get("prepared_by") or "Leskode Solutions Team"
    project_name = content.get("project_name") or "Zoho Business Management Solution"
    project_date = content.get("project_date") or today
    prepared_date = content.get("prepared_date") or today
    solution_title = content.get("solution_title") or f"Zoho Business Management Solution for {client_name}"
    app_line = content.get("application_line") or "Zoho One (CRM, Books, Inventory, Desk, Flow, Analytics)"
    business_one_liner = content.get("business_one_liner") or "Enterprise Operations & Business Automation"
    version_date = content.get("version_date") or f"Version 1.0 | {datetime.now().strftime('%B %Y')}"
    business_background = content.get("business_background") or f"{client_name} is implementing a modern Zoho architecture to streamline sales and finance."
    setup_description = content.get("setup_description") or f"The solution connects core Zoho applications ({app_line}) into a unified business system."
    business_objectives = content.get("business_objectives") or f"Deploy an integrated Zoho ecosystem for {client_name}."
    training_audience = content.get("training_audience") or f"{client_name}'s management, sales, accounts, and operations personnel"
    total_duration = content.get("total_duration") or "8–10 Weeks"

    module_scope_text = _format_module_blocks(content.get("module_blocks", []))
    integrations_text = _format_integrations(content.get("integrations", []))
    deliverables_text = _format_deliverables(content.get("deliverables", []))
    assumptions_text = _format_list(content.get("assumptions", []))
    exclusions_text = _format_list(content.get("exclusions", []))
    ptc_text = _format_points_to_confirm(content.get("points_to_confirm", []))

    canonical_values = {
        "client_name": client_name,
        "prepared_by": prepared_by,
        "project_name": project_name,
        "project_date": project_date,
        "prepared_date": prepared_date,
        "solution_title": solution_title,
        "application_line": app_line,
        "business_one_liner": business_one_liner,
        "version_date": version_date,
        "business_background": business_background,
        "setup_description": setup_description,
        "business_objectives": business_objectives,
        "module_scope": module_scope_text,
        "integrations": integrations_text,
        "deliverables": deliverables_text,
        "assumptions": assumptions_text,
        "exclusions": exclusions_text,
        "points_to_confirm": ptc_text,
        "training_audience": training_audience,
        "total_duration": total_duration,
        "acceptance_criteria": "Deliverables will be formally accepted upon successful demonstration in UAT matching the agreed criteria.",
    }

    # Generate multi-syntax replacement tokens
    replacements: Dict[str, str] = {}

    for key, val in canonical_values.items():
        str_val = str(val) if val is not None else ""
        upper_k = key.upper()
        title_k = key.replace("_", " ").title()
        space_upper_k = key.replace("_", " ").upper()

        # Syntax variations
        variations = [
            f"{{{{{upper_k}}}}}",
            f"{{{{{key}}}}}",
            f"{{{{{title_k}}}}}",
            f"{{{{{space_upper_k}}}}}",
            f"<<{upper_k}>>",
            f"<<{key}>>",
            f"<<{title_k}>>",
            f"<<{space_upper_k}>>",
            f"[{upper_k}]",
            f"[{title_k}]",
            f"[{space_upper_k}]",
            f"{{{upper_k}}}",
        ]
        for var in variations:
            replacements[var] = str_val

    # Additional custom placeholder map
    if placeholder_map:
        for ph, content_key in placeholder_map.items():
            if content_key in canonical_values:
                replacements[ph] = str(canonical_values[content_key])
            elif content_key in content:
                replacements[ph] = str(content[content_key])

    # Sample SOW text replacements (for sample SOW uploads)
    sample_replacements = {
        "Shiva Karthikeyaa Steels": client_name,
        "Shiva Karthikeyaa": client_name,
        "Prepared by Monish": f"Prepared by {prepared_by}",
        "Prepared by: Monish": f"Prepared by: {prepared_by}",
        "Prepared By: Monish": f"Prepared By: {prepared_by}",
    }

    return replacements, sample_replacements


def _replace_text_in_paragraph(
    para,
    replacements: Dict[str, str],
    sample_replacements: Optional[Dict[str, str]] = None,
):
    """
    Replace placeholders and sample text in a paragraph.
    Preserves run styling when possible.
    """
    full_text = "".join(run.text for run in para.runs)
    if not full_text.strip():
        return

    # Check for direct matches in individual runs first
    modified = False
    for run in para.runs:
        for ph, val in replacements.items():
            if ph in run.text:
                run.text = run.text.replace(ph, val)
                modified = True
        if sample_replacements:
            for s_old, s_new in sample_replacements.items():
                if s_old in run.text:
                    run.text = run.text.replace(s_old, s_new)
                    modified = True

    # Re-check full text for split tokens across runs or regex tokens
    full_text = "".join(run.text for run in para.runs)

    # Regex for remaining placeholders like {{...}}, <<...>>, [...]
    token_pattern = re.compile(r"\{\{([^}]+)\}\}|<<([^>]+)>>|\[([A-Za-z0-9_\s\-]+)\]")
    matches = token_pattern.findall(full_text)

    needs_reconstruct = False
    new_text = full_text

    if matches:
        for m in token_pattern.finditer(full_text):
            raw_match = m.group(0)
            inner_token = m.group(1) or m.group(2) or m.group(3)
            norm = _normalize_token(inner_token)
            canonical = _resolve_canonical_key(norm)
            if canonical and canonical in replacements.values():
                pass
            # Check if raw_match is in replacements
            if raw_match in replacements:
                new_text = new_text.replace(raw_match, replacements[raw_match])
                needs_reconstruct = True
            elif canonical:
                # Find matching value from canonical key
                val = next((v for k, v in replacements.items() if f"{{{{{canonical.upper()}}}}}" == k), None)
                if val:
                    new_text = new_text.replace(raw_match, val)
                    needs_reconstruct = True

    # Also check if any replacement or sample replacement is split across runs
    for ph, val in replacements.items():
        if ph in new_text:
            new_text = new_text.replace(ph, val)
            needs_reconstruct = True

    if sample_replacements:
        for s_old, s_new in sample_replacements.items():
            if s_old in new_text:
                new_text = new_text.replace(s_old, s_new)
                needs_reconstruct = True

    if needs_reconstruct and para.runs:
        # Re-assign to first run, clear subsequent runs to preserve paragraph styling
        para.runs[0].text = new_text
        for run in para.runs[1:]:
            run.text = ""


def _replace_in_table(
    table,
    replacements: Dict[str, str],
    sample_replacements: Optional[Dict[str, str]] = None,
):
    """Replace placeholders in all table cells."""
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                _replace_text_in_paragraph(para, replacements, sample_replacements)


def _populate_dynamic_tables(doc, content: Dict[str, Any]):
    """
    Detect tables with deliverable or integration headers and populate rows
    while preserving table styling and borders.
    """
    client_name = content.get("client_name") or "Valued Client"
    prepared_by = content.get("prepared_by") or "Leskode Solutions Team"
    deliverables = content.get("deliverables", [])
    integrations = content.get("integrations", [])

    for table in doc.tables:
        if not table.rows:
            continue

        header_texts = [cell.text.lower().strip() for cell in table.rows[0].cells]
        header_line = " ".join(header_texts)

        # 1. Sign-off / Acceptance table
        if any(k in header_line for k in ["acceptance", "sign-off", "signoff", "prepared by", "customer acceptance"]):
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        if "prepared by" in para.text.lower() and prepared_by not in para.text:
                            para.text = f"Prepared by: {prepared_by}"
                        elif "customer" in para.text.lower() and client_name not in para.text and "name" in para.text.lower():
                            para.text = f"Customer Name: {client_name}"

        # 2. Deliverables Table
        elif any(k in header_line for k in ["deliverable", "criteria", "acceptance"]) and len(table.rows[0].cells) >= 3 and deliverables:
            # If table only has 1 row (header) or sample rows, populate with actual deliverables
            if len(table.rows) > 1 and len(deliverables) > 0:
                # Update existing rows or add deliverables
                template_row = table.rows[-1]
                # Replace placeholders in existing rows
                for r_idx, d in enumerate(deliverables):
                    if r_idx + 1 < len(table.rows):
                        row = table.rows[r_idx + 1]
                        cells = row.cells
                        if len(cells) >= 4 and isinstance(d, (list, tuple)) and len(d) >= 4:
                            cells[0].text = str(d[0])
                            cells[1].text = str(d[1])
                            cells[2].text = str(d[2])
                            cells[3].text = str(d[3])
                        elif len(cells) >= 2 and isinstance(d, (list, tuple)):
                            cells[0].text = str(d[0])
                            cells[1].text = str(d[1])

        # 3. Integrations Table
        elif any(k in header_line for k in ["integration", "data flow", "connector", "direction"]) and len(table.rows[0].cells) >= 3 and integrations:
            if len(table.rows) > 1 and len(integrations) > 0:
                for r_idx, item in enumerate(integrations):
                    if r_idx + 1 < len(table.rows):
                        row = table.rows[r_idx + 1]
                        cells = row.cells
                        if len(cells) >= 4 and isinstance(item, (list, tuple)) and len(item) >= 4:
                            cells[0].text = str(item[0])
                            cells[1].text = str(item[1])
                            cells[2].text = str(item[2])
                            cells[3].text = str(item[3])


def generate_sow_docx(
    template_path: str,
    output_path: str,
    content: Dict[str, Any],
    placeholder_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Generate an authentic SOW DOCX by cloning and populating any master template or sample SOW.
    Preserves 100% of the original logo, font design, headers, footers, margins, tables, and colors.
    """
    try:
        from docx import Document
    except ImportError:
        raise GenerationError("python-docx not installed. Run: pip install python-docx")

    if not os.path.exists(template_path):
        raise GenerationError(f"Master template file not found: {template_path}")

    # Step 1: Make a physical copy of the template so all images, logos, headers, footers are preserved
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    shutil.copy2(template_path, output_path)

    try:
        doc = Document(output_path)
    except Exception as e:
        raise GenerationError(f"Cannot open cloned master template: {e}")

    # Step 2: Build replacements
    replacements, sample_replacements = _build_replacements(content, placeholder_map or {})

    # Step 3: Replace in all body paragraphs
    for para in doc.paragraphs:
        _replace_text_in_paragraph(para, replacements, sample_replacements)

    # Step 4: Replace in all body tables and populate dynamic tables
    for table in doc.tables:
        _replace_in_table(table, replacements, sample_replacements)
    _populate_dynamic_tables(doc, content)

    # Step 5: Replace in headers, footers, and header/footer tables (preserving logos)
    for section in doc.sections:
        # Header
        if section.header:
            for para in section.header.paragraphs:
                _replace_text_in_paragraph(para, replacements, sample_replacements)
            for table in section.header.tables:
                _replace_in_table(table, replacements, sample_replacements)

        # Footer
        if section.footer:
            for para in section.footer.paragraphs:
                _replace_text_in_paragraph(para, replacements, sample_replacements)
            for table in section.footer.tables:
                _replace_in_table(table, replacements, sample_replacements)

    # Step 6: Scan for remaining unresolved tokens
    unresolved = []
    token_pattern = re.compile(r"\{\{([A-Z_]+)\}\}")
    for para in doc.paragraphs:
        for match in token_pattern.findall("".join(r.text for r in para.runs)):
            unresolved.append(f"{{{{{match}}}}}")
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for match in token_pattern.findall(" ".join(p.text for p in cell.paragraphs)):
                    unresolved.append(f"{{{{{match}}}}}")

    unresolved = list(set(unresolved))

    # Step 7: Save output
    try:
        doc.save(output_path)
    except Exception as e:
        raise GenerationError(f"Failed to save populated DOCX: {e}")

    file_size = os.path.getsize(output_path)
    logger.info(f"Generated DOCX via master template: {output_path} ({file_size} bytes)")

    return {
        "status": "success",
        "output_path": output_path,
        "file_size_bytes": file_size,
        "unresolved_placeholders": unresolved,
        "warnings": [f"Placeholder {ph} was not populated." for ph in unresolved],
    }
