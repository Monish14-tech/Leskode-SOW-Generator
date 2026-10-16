"""
ScopePilot AI — Template-Preserving DOCX Generator
Generates SOW documents by populating a copy of the master DOCX template.
Preserves all formatting, styles, tables, headers, footers, and static text.
"""
import os
import re
import copy
import logging
import shutil
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class GenerationError(Exception):
    pass


def _replace_text_in_run(run, placeholder: str, value: str):
    """Replace placeholder in a run without destroying character formatting."""
    if placeholder in run.text:
        run.text = run.text.replace(placeholder, value)


def _replace_text_in_paragraph(para, replacements: Dict[str, str]):
    """
    Replace placeholders in a paragraph.
    Handles cases where placeholders are split across runs by reconstructing
    the full paragraph text, performing replacement, then redistributing.
    """
    full_text = "".join(run.text for run in para.runs)
    if not any(k in full_text for k in replacements):
        return

    new_text = full_text
    for placeholder, value in replacements.items():
        new_text = new_text.replace(placeholder, str(value) if value else "")

    # Redistribute text back to runs, preserving formatting of first run
    if para.runs:
        para.runs[0].text = new_text
        for run in para.runs[1:]:
            run.text = ""


def _replace_in_table(table, replacements: Dict[str, str]):
    """Replace placeholders in all table cells."""
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                _replace_text_in_paragraph(para, replacements)


def _add_table_rows_for_list(table, data_rows: List[Dict[str, Any]], template_row_idx: int = -1):
    """
    Duplicate the last row of a table for each data item.
    Used to populate repeatable sections like task lists.
    """
    from docx.oxml.ns import qn
    from copy import deepcopy

    if not table.rows:
        return

    # Use the last row as the template row
    template_row = table.rows[template_row_idx]
    template_tr = template_row._tr

    for data in data_rows:
        # Deep copy the template row
        new_tr = deepcopy(template_tr)
        new_row_para_texts = [
            tc.text for tc in new_tr.findall(f".//{qn('w:tc')}")
        ]
        # Replace cell content in the new row
        cells = new_tr.findall(f".//{qn('w:tc')}")
        keys = list(data.keys())
        for idx, cell in enumerate(cells):
            if idx < len(keys):
                # Clear and set text
                for p in cell.findall(f".//{qn('w:p')}"):
                    for r in p.findall(f".//{qn('w:r')}"):
                        for t in r.findall(f".//{qn('w:t')}"):
                            t.text = str(data[keys[idx]] or "")
                            break
                        break
                    break

        # Insert after the last row
        table._tbl.append(new_tr)


def generate_sow_docx(
    template_path: str,
    output_path: str,
    content: Dict[str, Any],
    placeholder_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Generate a SOW DOCX by populating a copy of the master template.

    Args:
        template_path: Path to the original master template DOCX.
        output_path: Where to save the generated DOCX.
        content: Dict mapping content keys to values.
        placeholder_map: Optional override mapping {{PLACEHOLDER}} → content_key.

    Returns:
        dict with status, output_path, unresolved_placeholders, warnings.
    """
    try:
        from docx import Document
    except ImportError:
        raise GenerationError("python-docx not installed. Run: pip install python-docx")

    if not os.path.exists(template_path):
        raise GenerationError(f"Master template not found: {template_path}")

    # Make a working copy of the template
    shutil.copy2(template_path, output_path)

    try:
        doc = Document(output_path)
    except Exception as e:
        raise GenerationError(f"Cannot open template copy: {e}")

    # Build replacement dictionary from content and placeholder_map
    replacements = _build_replacements(content, placeholder_map or {})

    # Track which placeholders were resolved
    found_placeholders = set()
    unresolved = []

    # Replace in all paragraphs
    for para in doc.paragraphs:
        full_text = "".join(run.text for run in para.runs)
        for ph in re.findall(r"\{\{[A-Z_]+\}\}", full_text):
            found_placeholders.add(ph)
        _replace_text_in_paragraph(para, replacements)

    # Replace in all tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    full_text = "".join(run.text for run in para.runs)
                    for ph in re.findall(r"\{\{[A-Z_]+\}\}", full_text):
                        found_placeholders.add(ph)
                _replace_in_table(table, replacements)

    # Replace in headers and footers
    for section in doc.sections:
        for para in section.header.paragraphs:
            _replace_text_in_paragraph(para, replacements)
        for para in section.footer.paragraphs:
            _replace_text_in_paragraph(para, replacements)

    # Find any remaining unresolved placeholders
    for para in doc.paragraphs:
        full_text = "".join(run.text for run in para.runs)
        remaining = re.findall(r"\{\{[A-Z_]+\}\}", full_text)
        unresolved.extend(remaining)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    full_text = "".join(run.text for run in para.runs)
                    remaining = re.findall(r"\{\{[A-Z_]+\}\}", full_text)
                    unresolved.extend(remaining)

    unresolved = list(set(unresolved))

    try:
        doc.save(output_path)
    except Exception as e:
        raise GenerationError(f"Failed to save generated DOCX: {e}")

    # Verify the file was actually written
    if not os.path.exists(output_path):
        raise GenerationError("Generated file was not saved successfully.")

    file_size = os.path.getsize(output_path)
    if file_size < 1000:
        raise GenerationError(f"Generated file is suspiciously small ({file_size} bytes). Check template.")

    return {
        "status": "success",
        "output_path": output_path,
        "file_size_bytes": file_size,
        "unresolved_placeholders": unresolved,
        "found_placeholders": list(found_placeholders),
        "warnings": [
            f"Placeholder {ph} was not populated — marked as pending." for ph in unresolved
        ],
    }


def _build_replacements(content: Dict[str, Any], placeholder_map: Dict[str, str]) -> Dict[str, str]:
    """Build the final {{KEY}} → value replacement dictionary."""
    # Default placeholder mappings
    default_map = {
        "{{CLIENT_NAME}}": "client_name",
        "{{PROJECT_NAME}}": "project_name",
        "{{PROJECT_DATE}}": "project_date",
        "{{BUSINESS_BACKGROUND}}": "business_background",
        "{{BUSINESS_OBJECTIVES}}": "business_objectives",
        "{{CURRENT_PROCESS}}": "current_process",
        "{{PROPOSED_SOLUTION}}": "proposed_solution",
        "{{MODULE_SCOPE}}": "module_scope",
        "{{TASKS_AND_SUBTASKS}}": "tasks_and_subtasks",
        "{{AUTOMATION_MATRIX}}": "automation_matrix",
        "{{INTEGRATION_MATRIX}}": "integration_matrix",
        "{{DELIVERABLES}}": "deliverables",
        "{{ACCEPTANCE_CRITERIA}}": "acceptance_criteria",
        "{{PROJECT_TIMELINE}}": "project_timeline",
        "{{ASSUMPTIONS}}": "assumptions",
        "{{EXCLUSIONS}}": "exclusions",
        "{{RISKS}}": "risks",
        "{{PENDING_CLARIFICATIONS}}": "pending_clarifications",
        "{{PREPARED_BY}}": "prepared_by",
        "{{PREPARED_DATE}}": "prepared_date",
        "{{VERSION}}": "version",
    }

    # Override with custom mapping
    default_map.update(placeholder_map)

    result = {}
    today = datetime.now().strftime("%d %B %Y")

    for placeholder, content_key in default_map.items():
        if content_key in content:
            value = content[content_key]
            if isinstance(value, list):
                # Format lists as numbered or bulleted text
                value = _format_list(value)
            elif isinstance(value, dict):
                value = _format_dict(value)
            result[placeholder] = str(value) if value else ""
        elif placeholder == "{{PROJECT_DATE}}" or placeholder == "{{PREPARED_DATE}}":
            result[placeholder] = content.get("project_date", today)

    return result


def _format_list(items: List[Any]) -> str:
    """Format a list of items as numbered text for document insertion."""
    if not items:
        return "[None specified]"
    formatted = []
    for i, item in enumerate(items, 1):
        if isinstance(item, dict):
            # Format dict items like tasks
            name = item.get("name", item.get("title", str(item)))
            desc = item.get("description", "")
            formatted.append(f"{i}. {name}" + (f"\n   {desc}" if desc else ""))
        else:
            formatted.append(f"{i}. {item}")
    return "\n".join(formatted)


def _format_dict(d: Dict[str, Any]) -> str:
    """Format a dict as readable text."""
    lines = []
    for k, v in d.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)
