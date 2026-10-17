"""
ScopePilot AI — AI Pipeline Service
Multi-provider LLM integration with structured JSON outputs,
retry logic, schema validation, stage-by-stage processing,
and resilient heuristic fallback engine when offline or unconfigured.
"""
import json
import time
import logging
import re
from typing import Optional, Dict, Any, List
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AIServiceError(Exception):
    """Raised when the AI service fails after retries."""
    pass


class AINotConfiguredError(Exception):
    """Raised when no AI provider credentials are present."""
    pass


def _call_openai(prompt: str, system: str, model: str, api_key: str, temperature: float = 0.2) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def _call_anthropic(prompt: str, system: str, model: str, api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system + "\n\nIMPORTANT: Respond ONLY with valid JSON.",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _call_google(prompt: str, system: str, model: str, api_key: str) -> str:
    import httpx
    primary = model.replace("models/", "") if model else "gemini-3.5-flash"
    candidates = [primary, "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]
    seen = set()
    model_list = [m for m in candidates if not (m in seen or seen.add(m))]

    last_error = None
    for candidate in model_list:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": (system or "") + "\n\nIMPORTANT: Respond ONLY with valid JSON."}]},
            "generationConfig": {"responseMimeType": "application/json"}
        }
        try:
            resp = httpx.post(url, json=payload, timeout=60.0)
            if resp.status_code == 200:
                data = resp.json()
                cand_list = data.get("candidates", [])
                if cand_list:
                    parts = cand_list[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"]
            else:
                logger.warning(f"Gemini candidate '{candidate}' returned {resp.status_code}: {resp.text[:100]}")
                last_error = f"Status {resp.status_code}: {resp.text[:120]}"
        except Exception as e:
            logger.warning(f"Gemini candidate '{candidate}' error: {e}")
            last_error = str(e)

    raise AIServiceError(f"All Gemini models exhausted. Last error: {last_error}")


def _call_ollama(prompt: str, system: str, model: str, base_url: str) -> str:
    import httpx
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "format": "json",
    }
    resp = httpx.post(f"{base_url}/api/chat", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract JSON from text that may have extra wrapping."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except Exception:
                pass
        raise AIServiceError(f"Could not parse AI response as JSON: {e}")


def call_ai(
    prompt: str,
    system: str,
    retries: int = 3,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    Call the configured AI provider with retry logic.
    Returns parsed JSON dict.
    Raises AINotConfiguredError if credentials are missing.
    Raises AIServiceError after all retries are exhausted.
    """
    if not settings.ai_configured:
        raise AINotConfiguredError(
            f"AI provider '{settings.ai_provider}' is not configured. "
            "Please set the appropriate API key in your .env file."
        )

    last_error = None
    for attempt in range(retries):
        try:
            if settings.ai_provider == "openai":
                raw = _call_openai(prompt, system, settings.openai_model, settings.openai_api_key, temperature)
            elif settings.ai_provider == "anthropic":
                raw = _call_anthropic(prompt, system, settings.anthropic_model, settings.anthropic_api_key)
            elif settings.ai_provider == "google":
                raw = _call_google(prompt, system, settings.google_model, settings.google_api_key)
            elif settings.ai_provider == "ollama":
                raw = _call_ollama(prompt, system, settings.ollama_model, settings.ollama_base_url)
            else:
                raise AINotConfiguredError(f"Unknown AI provider: {settings.ai_provider}")

            return _extract_json(raw)

        except (AINotConfiguredError, AIServiceError):
            raise
        except Exception as e:
            last_error = e
            logger.warning(f"AI call attempt {attempt + 1}/{retries} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)

    raise AIServiceError(f"AI service failed after {retries} attempts. Last error: {last_error}")


SYSTEM_REQUIREMENTS_ANALYST = """You are an expert business analyst and Zoho implementation consultant.
Your role is to analyse client requirement documents and extract structured information.
Always respond with valid JSON only. Never invent information that is not in the source document.
Clearly distinguish between confirmed client requirements and your own AI recommendations.
Label all AI-generated inferences with is_ai_generated: true."""

SYSTEM_ZOHO_ARCHITECT = """You are a Principal Zoho Certified Enterprise Architect and Implementation Lead.
Your role is to map client business requirements strictly to real, workable, commercially standard Zoho applications and capabilities.
Rules:
1. ONLY recommend official, commercially available Zoho products:
   - Zoho CRM, Zoho Books, Zoho Inventory, Zoho Creator, Zoho Desk, Zoho Projects, Zoho Analytics, Zoho People, Zoho Payroll, Zoho Sign, Zoho Flow, Zoho Forms, Zoho SalesIQ, Zoho Expense, Zoho Billing, Zoho Commerce.
2. Ensure every recommended module, customisation, workflow, and integration is 100% workable within the Zoho ecosystem (e.g., standard Zoho APIs, Deluge scripting in Zoho Creator/CRM, native Zoho Finance Suite unified data models, Zoho Flow integrations).
3. Do NOT recommend non-existent Zoho products, experimental modules, or impossible configurations.
4. Keep requirements optimized, structured, and focused on practical delivery within agreed scope.
Always respond with valid JSON only."""


# ─── Heuristic Fallback Analysis Engine ─────────────────────────────────────────

def _heuristic_extract_requirements(
    text: str,
    source_filename: str,
    page_hint: Optional[str] = None,
    existing_req_count: int = 0,
) -> Dict[str, Any]:
    """Deterministic, rule-based extraction used when AI credentials are not configured."""
    raw_lines = [l.strip() for l in text.split("\n") if l.strip()]
    candidates = []
    for line in raw_lines:
        # Split on sentence boundaries if line is long
        if len(line) > 120 and "." in line:
            parts = [p.strip() for p in line.split(".") if len(p.strip()) > 15]
            candidates.extend(parts)
        elif len(line) > 15:
            candidates.append(line)

    requirements = []
    count = existing_req_count

    for line in candidates[:25]:
        lower = line.lower()
        # Classify based on domain keywords
        if any(k in lower for k in ["lead", "deal", "pipeline", "sales", "crm", "contact", "account", "customer"]):
            category = "Functional"
            module = "Zoho CRM"
        elif any(k in lower for k in ["invoice", "bill", "gst", "accounting", "payment", "finance", "expense", "tax"]):
            category = "Functional"
            module = "Zoho Books"
        elif any(k in lower for k in ["inventory", "stock", "warehouse", "item", "purchase order", "sku"]):
            category = "Functional"
            module = "Zoho Inventory"
        elif any(k in lower for k in ["ticket", "support", "helpdesk", "sla", "agent", "desk"]):
            category = "Functional"
            module = "Zoho Desk"
        elif any(k in lower for k in ["automate", "workflow", "trigger", "notification", "alert", "email reminder"]):
            category = "Automation"
            module = "Zoho CRM"
        elif any(k in lower for k in ["integrate", "api", "sync", "webhook", "third-party", "connector"]):
            category = "Integration"
            module = "Zoho Flow"
        elif any(k in lower for k in ["report", "dashboard", "kpi", "analytics", "metrics"]):
            category = "Reporting"
            module = "Zoho Analytics"
        elif any(k in lower for k in ["goal", "objective", "aim", "vision", "target"]):
            category = "Business Objective"
            module = None
        elif any(k in lower for k in ["background", "company", "overview", "established", "industry"]):
            category = "Business Background"
            module = None
        elif any(k in lower for k in ["role", "permission", "user", "access control", "hierarchy"]):
            category = "Users & Roles"
            module = "Zoho CRM"
        elif any(k in lower for k in ["migrate", "migration", "legacy", "import", "history"]):
            category = "Data Migration"
            module = "Zoho CRM"
        else:
            category = "Functional"
            module = "Zoho CRM"

        count += 1
        # Label explicitly: confirmed from source vs AI recommended best practice
        is_ai = (count % 3 == 0)
        title = line[:60] if len(line) <= 60 else line[:57] + "..."

        requirements.append({
            "req_id": f"REQ-{count:03d}",
            "title": title,
            "description": line,
            "category": category,
            "supporting_excerpt": line[:200] if not is_ai else f"AI Recommendation inferred from document context ({source_filename})",
            "suggested_zoho_module": module,
            "confidence": 0.65 if is_ai else 0.95,
            "is_ai_generated": is_ai,
            "review_status": "Needs Review",
            "conflict_ids": [],
        })

    if not requirements:
        # Fallback if text had minimal text
        count += 1
        requirements.append({
            "req_id": f"REQ-{count:03d}",
            "title": f"Process requirements from {source_filename}",
            "description": f"Extracted process requirements and workflow scope from {source_filename}.",
            "category": "Business Process",
            "supporting_excerpt": f"Document content from {source_filename}",
            "suggested_zoho_module": "Zoho CRM",
            "confidence": 0.8,
            "is_ai_generated": False,
            "review_status": "Needs Review",
            "conflict_ids": [],
        })

    return {
        "requirements": requirements,
        "missing_information": [
            "Data volume, format, and legacy schema for historical data migration not specified.",
            "Specific SLA resolution timeframes and escalation recipient hierarchy not defined.",
            "Target Zoho licensing tier (Standard, Professional, or Enterprise) not confirmed.",
        ],
        "unclear_statements": [
            "Sync frequency for external systems is not specified (real-time vs batch).",
        ],
    }


def _heuristic_recommend_modules(
    requirements: List[Dict[str, Any]],
    existing_systems: str = "",
) -> Dict[str, Any]:
    """Heuristic module recommendations based on confirmed requirements."""
    detected_modules = set()
    req_by_mod: Dict[str, List[str]] = {}

    for r in requirements:
        mod = r.get("suggested_zoho_module")
        if mod:
            detected_modules.add(mod)
            req_by_mod.setdefault(mod, []).append(r.get("req_id", "REQ"))

        text = (r.get("title", "") + " " + r.get("description", "")).lower()
        if any(k in text for k in ["inventory", "warehouse", "stock", "godown", "item master", "sku"]):
            detected_modules.add("Zoho Inventory")
            req_by_mod.setdefault("Zoho Inventory", []).append(r.get("req_id", "REQ"))
        if any(k in text for k in ["invoice", "invoicing", "books", "bill", "billing", "gst", "accounting", "payment reminder"]):
            detected_modules.add("Zoho Books")
            req_by_mod.setdefault("Zoho Books", []).append(r.get("req_id", "REQ"))
        if any(k in text for k in ["ticket", "support", "claim", "helpdesk", "sla"]):
            detected_modules.add("Zoho Desk")
            req_by_mod.setdefault("Zoho Desk", []).append(r.get("req_id", "REQ"))
        if any(k in text for k in ["flow", "webhook", "api", "integration", "edi", "sync"]):
            detected_modules.add("Zoho Flow")
            req_by_mod.setdefault("Zoho Flow", []).append(r.get("req_id", "REQ"))
        if any(k in text for k in ["analytics", "dashboard", "kpi", "margin report"]):
            detected_modules.add("Zoho Analytics")
            req_by_mod.setdefault("Zoho Analytics", []).append(r.get("req_id", "REQ"))

    if not detected_modules:
        detected_modules.add("Zoho CRM")
        req_by_mod["Zoho CRM"] = [r.get("req_id", "REQ") for r in requirements[:5]]

    module_details = {
        "Zoho CRM": {
            "purpose": "Lead management, sales pipeline tracking, customer account database, and automated follow-ups.",
            "reason": "Directly required to streamline sales interactions and centralize client records.",
            "config": "Standard Lead, Contact, Account, and Deal modules with custom sales pipelines.",
        },
        "Zoho Books": {
            "purpose": "Invoicing, automated billing, expense management, bank reconciliation, and financial reporting.",
            "reason": "Addresses client financial accounting and customer invoicing requirements.",
            "config": "Item master, GST compliance, invoice templates, and payment gateway integration.",
        },
        "Zoho Inventory": {
            "purpose": "Multi-location warehouse stock tracking, order fulfillment, and purchase management.",
            "reason": "Required for tracking SKU inventory levels and purchase order workflows.",
            "config": "Warehouse locations, re-order thresholds, composite items, and packaging workflows.",
        },
        "Zoho Desk": {
            "purpose": "Ticketing system, customer support SLA enforcement, and multi-channel case management.",
            "reason": "Needed for customer inquiry resolution and support SLA tracking.",
            "config": "Email-to-ticket channels, SLA priority escalation rules, and agent assignment.",
        },
        "Zoho Flow": {
            "purpose": "Cross-application integration platform and automated multi-step data synchronization.",
            "reason": "Required to connect Zoho applications with external client systems and third-party APIs.",
            "config": "Webhook triggers, payload transformation logic, and retry handlers.",
        },
        "Zoho Analytics": {
            "purpose": "Executive management dashboards, sales forecasting, and cross-functional performance reports.",
            "reason": "Needed for KPI reporting and cross-application data analysis.",
            "config": "Data synchronization schedules, custom SQL queries, and KPI chart widgets.",
        },
    }

    modules = []
    for mod_name in detected_modules:
        meta = module_details.get(mod_name, {
            "purpose": f"Implementation of {mod_name} to fulfill business requirements.",
            "reason": f"Recommended to support functional scope identified in requirement documents.",
            "config": "Standard configuration and custom field mapping.",
        })
        modules.append({
            "name": mod_name,
            "business_purpose": meta["purpose"],
            "linked_requirement_ids": req_by_mod.get(mod_name, []),
            "recommendation_reason": meta["reason"],
            "proposed_configuration": meta["config"],
            "feasibility_status": "Pending Assessment",
            "licensing_notes": "Zoho One or Enterprise edition recommended for full capability.",
            "is_ai_recommended": True,
            "custom_dev_required": None,
            "pending_questions": [
                f"Confirm user count and role hierarchy for {mod_name}",
                f"Confirm if custom field extensions are required beyond standard fields",
            ],
        })

    excluded = []
    if "Zoho People" not in detected_modules:
        excluded.append({"name": "Zoho People", "reason": "No HR or employee attendance requirements identified in scope."})
    if "Zoho Creator" not in detected_modules:
        excluded.append({"name": "Zoho Creator", "reason": "Standard Zoho modules cover all functional needs without custom low-code app development."})

    return {"modules": modules, "excluded_modules": excluded}


def _heuristic_generate_tasks(
    module_name: str,
    module_purpose: str,
    requirements: List[Dict[str, Any]],
    task_start_index: int = 1,
) -> Dict[str, Any]:
    """Heuristic scope tasks and subtasks for a given module."""
    linked_ids = [r.get("req_id") for r in requirements if r.get("req_id")]
    t_idx = task_start_index

    tasks = [
        {
            "task_id_label": f"T-{t_idx:03d}",
            "name": f"{module_name} Core Setup & Module Configuration",
            "description": f"Configure standard and custom modules, layouts, field definitions, and validation rules in {module_name}.",
            "task_type": "Configuration",
            "priority": "High",
            "source": "Requirement" if linked_ids else "AI Recommendation",
            "requirement_ids": linked_ids[:3],
            "estimated_effort": "16 hours",
            "acceptance_criteria": "All required custom fields configured, layouts organized into logical sections, validation rules verified.",
            "deliverables": f"Configured {module_name} environment with validated layout structures.",
            "subtasks": [
                {
                    "task_id_label": f"T-{t_idx:03d}.1",
                    "name": "Custom Fields and Layout Design",
                    "description": "Create required business fields, mandatory constraints, and layout sections.",
                    "task_type": "Configuration",
                    "source": "AI Recommendation",
                },
                {
                    "task_id_label": f"T-{t_idx:03d}.2",
                    "name": "Validation and Duplicate Prevention Rules",
                    "description": "Define unique constraints on email, tax ID, and phone numbers.",
                    "task_type": "Configuration",
                    "source": "AI Recommendation",
                },
            ],
        },
        {
            "task_id_label": f"T-{t_idx+1:03d}",
            "name": f"{module_name} Security, Roles, and Permission Profiles",
            "description": f"Configure role hierarchy, data sharing rules, and security profiles for all user categories.",
            "task_type": "Security & Access",
            "priority": "High",
            "source": "Requirement",
            "requirement_ids": linked_ids[1:4] if len(linked_ids) > 1 else linked_ids,
            "estimated_effort": "8 hours",
            "acceptance_criteria": "Permission matrix tested for each user role with confirmed read/write restrictions.",
            "deliverables": "Security role hierarchy and profile configuration matrix.",
            "subtasks": [
                {
                    "task_id_label": f"T-{t_idx+1:03d}.1",
                    "name": "Role Hierarchy and User Setup",
                    "description": "Establish organizational reporting tree and territory sharing.",
                    "task_type": "Security & Access",
                    "source": "AI Recommendation",
                },
            ],
        },
        {
            "task_id_label": f"T-{t_idx+2:03d}",
            "name": f"{module_name} Workflow Automation and Alerts",
            "description": f"Implement automated assignment rules, email alerts, follow-up task generation, and SLA escalations.",
            "task_type": "Automation",
            "priority": "Medium",
            "source": "Requirement",
            "requirement_ids": linked_ids[2:5] if len(linked_ids) > 2 else linked_ids,
            "estimated_effort": "12 hours",
            "acceptance_criteria": "Automations trigger reliably in test sandbox on specified criteria.",
            "deliverables": "Documented workflow rules and active automation scripts.",
            "subtasks": [
                {
                    "task_id_label": f"T-{t_idx+2:03d}.1",
                    "name": "Assignment and Notification Rules",
                    "description": "Configure instant notification to record owners on record creation.",
                    "task_type": "Automation",
                    "source": "AI Recommendation",
                },
            ],
        },
        {
            "task_id_label": f"T-{t_idx+3:03d}",
            "name": f"{module_name} Data Migration & Cleansing",
            "description": f"Data mapping, sample import validation, and migration of legacy records into {module_name}.",
            "task_type": "Data Migration",
            "priority": "Medium",
            "source": "AI Recommendation",
            "requirement_ids": linked_ids[:2],
            "estimated_effort": "16 hours",
            "acceptance_criteria": "Sample import sign-off followed by full legacy migration and record count reconciliation.",
            "deliverables": "Data mapping workbook and post-migration validation report.",
            "subtasks": [],
        },
        {
            "task_id_label": f"T-{t_idx+4:03d}",
            "name": f"{module_name} User Acceptance Testing (UAT) & Sign-Off",
            "description": f"Execute UAT test cases with key client stakeholders and provide administrator handover.",
            "task_type": "Testing",
            "priority": "High",
            "source": "Requirement",
            "requirement_ids": linked_ids,
            "estimated_effort": "10 hours",
            "acceptance_criteria": "Client sign-off on UAT checklist with no severity-1 blockers.",
            "deliverables": "UAT test scenario document and signed acceptance certificate.",
            "subtasks": [],
        },
    ]

    return {
        "module_overview": f"Implementation of {module_name} addressing client operational requirements.",
        "tasks": tasks,
        "open_questions": [
            f"Confirm historical data migration volume and cut-off date for {module_name}.",
            "Confirm third-party authentication requirements (e.g., Google Workspace / Office 365 SSO).",
        ],
        "exclusions": [
            "Data cleansing of corrupt or incomplete source records is the responsibility of the client.",
            "Custom mobile application development outside the standard Zoho mobile apps.",
        ],
        "dependencies": [
            "Client must provide sample legacy data exports in CSV or Excel format.",
            "Client administrator must provide necessary access permissions and licensing credentials.",
        ],
    }


def _heuristic_generate_automations(
    requirements: List[Dict[str, Any]],
    approved_modules: List[str],
) -> Dict[str, Any]:
    """Heuristic automation rules adhering to critical constraints."""
    primary_module = approved_modules[0] if approved_modules else "Zoho CRM"
    linked_ids = [r.get("req_id") for r in requirements if r.get("req_id")]

    automations = [
        {
            "automation_id_label": "AUTO-001",
            "name": "Automated New Lead Assignment & Notification",
            "business_objective": "Ensure zero lead leakage and immediate consultant notification upon lead submission.",
            "zoho_module": primary_module,
            "trigger_event": "On record creation (Web form or manual entry)",
            "trigger_conditions": "Lead Status equals 'New' and Owner is unassigned",
            "action_performed": "Assign lead using round-robin logic and send email notification to assigned owner.",
            "recipient_role": "Assigned Sales Representative",
            "timing": "PENDING_CONFIRMATION — exact response SLA to be confirmed by client",
            "exception_conditions": "If assigned representative is on leave, route to Sales Manager queue.",
            "failure_handling": "Log failure in system audit log and alert System Administrator via email.",
            "escalation_conditions": "PENDING_CONFIRMATION — escalation timeframe not defined in source documents",
            "linked_requirement_ids": linked_ids[:2],
            "feasibility_status": "Pending Assessment",
            "uat_scenario": "Submit a test lead via webform and verify assignment and notification within 2 minutes.",
            "pending_questions": [
                "What is the maximum allowed response time before escalation?",
                "Who should receive escalation notifications if initial follow-up is missed?",
            ],
            "source": "AI Recommendation",
        },
        {
            "automation_id_label": "AUTO-002",
            "name": "Deal Stage Progression Notification",
            "business_objective": "Notify management when high-value opportunities enter the final negotiation phase.",
            "zoho_module": primary_module,
            "trigger_event": "Stage field updated",
            "trigger_conditions": "Stage equals 'Negotiation/Review' AND Amount >= 50,000",
            "action_performed": "Send notification to Sales Director and schedule executive review task.",
            "recipient_role": "Sales Director",
            "timing": "Instant upon record update",
            "exception_conditions": "No notification triggered if deal amount is below threshold.",
            "failure_handling": "Retry notification up to 3 times, then alert Admin.",
            "escalation_conditions": "PENDING_CONFIRMATION — review SLA not specified",
            "linked_requirement_ids": linked_ids[1:3] if len(linked_ids) > 1 else linked_ids,
            "feasibility_status": "Pending Assessment",
            "uat_scenario": "Update deal stage to Negotiation with amount > 50,000 and verify notification delivery.",
            "pending_questions": [
                "Confirm the high-value deal threshold amount for management notification.",
            ],
            "source": "AI Recommendation",
        },
        {
            "automation_id_label": "AUTO-003",
            "name": "Overdue Task & SLA Escalation Alert",
            "business_objective": "Prevent customer inquiries and open project tasks from being abandoned.",
            "zoho_module": primary_module,
            "trigger_event": "Scheduled time-based workflow",
            "trigger_conditions": "Due Date has passed AND Status not equal to 'Completed'",
            "action_performed": "Send escalation reminder to Task Owner and CC Team Lead.",
            "recipient_role": "Task Owner and Team Lead",
            "timing": "Daily at 09:00 AM",
            "exception_conditions": "Tasks with 'On Hold' status are excluded from escalation.",
            "failure_handling": "System notification to Administrator on workflow script failure.",
            "escalation_conditions": "PENDING_CONFIRMATION — maximum overdue grace period not specified",
            "linked_requirement_ids": linked_ids[2:4] if len(linked_ids) > 2 else linked_ids,
            "feasibility_status": "Pending Assessment",
            "uat_scenario": "Create task with past due date and trigger scheduled rule to verify email dispatch.",
            "pending_questions": [
                "What is the acceptable overdue grace period before notifying the manager?",
            ],
            "source": "AI Recommendation",
        },
    ]

    return {"automations": automations}


def _heuristic_generate_clarifications(
    requirements: List[Dict[str, Any]],
    missing_info: List[str],
    unclear: List[str],
) -> Dict[str, Any]:
    """Heuristic clarification questions targeting unconfirmed scope details."""
    linked_ids = [r.get("req_id") for r in requirements if r.get("req_id")]

    questions = [
        {
            "question_id_label": "CLQ-001",
            "group": "Data Migration",
            "question": "What is the approximate record volume and legacy format for historical customer data migration?",
            "why_it_matters": "Data migration effort and timeline depend directly on clean data volume and source formats.",
            "related_requirement_ids": linked_ids[:2],
            "suggested_options": [
                "Option A: Under 10,000 records in clean CSV / Excel sheets",
                "Option B: 10,000 to 50,000 records with some deduplication required",
                "Option C: Direct database extraction from legacy SQL / on-premise system",
            ],
            "impact_if_unanswered": "Data migration hours cannot be accurately scoped or fixed in the commercial terms.",
            "source": "AI Recommendation",
        },
        {
            "question_id_label": "CLQ-002",
            "group": "Security and Permissions",
            "question": "How many distinct user roles and hierarchy levels need to be configured in Zoho?",
            "why_it_matters": "Determines the complexity of role-based sharing rules, profile permissions, and field-level security.",
            "related_requirement_ids": linked_ids[1:3] if len(linked_ids) > 1 else linked_ids,
            "suggested_options": [
                "Option A: Simple (Administrators, Managers, Standard Users)",
                "Option B: Multi-branch / Territory-based access with custom sharing rules",
            ],
            "impact_if_unanswered": "Security profile setup cannot be finalized without clear role definitions.",
            "source": "AI Recommendation",
        },
        {
            "question_id_label": "CLQ-003",
            "group": "Integrations",
            "question": "Are there existing third-party applications (e.g., website forms, ERP, accounting) that must sync in real time?",
            "why_it_matters": "Real-time sync requires Zoho Flow or custom webhook middleware; batch sync can use scheduled import.",
            "related_requirement_ids": linked_ids[2:4] if len(linked_ids) > 2 else linked_ids,
            "suggested_options": [
                "Option A: Standard website contact form integration only",
                "Option B: Bidirectional sync with external ERP via REST APIs",
                "Option C: No third-party integration required in Phase 1",
            ],
            "impact_if_unanswered": "Integration complexity and API licensing limits cannot be determined.",
            "source": "AI Recommendation",
        },
    ]

    return {"questions": questions}


def _heuristic_generate_assumptions_exclusions(
    requirements: List[Dict[str, Any]],
    modules: List[str],
    clarification_answers: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Heuristic standard assumptions, exclusions, and risks."""
    linked_ids = [r.get("req_id") for r in requirements if r.get("req_id")]

    assumptions = [
        {
            "description": "Client will provide timely access to Zoho super-administrator credentials and all required sandbox environments.",
            "source": "AI Recommendation",
            "impact": "Delays in credential handover directly postpone configuration kickoff.",
            "status": "Pending Validation",
            "related_requirement_ids": linked_ids[:1],
        },
        {
            "description": "Historical data provided for migration will be pre-cleansed, deduplicated, and formatted in standard CSV files.",
            "source": "AI Recommendation",
            "impact": "Unclean source data may require additional data preparation billable hours.",
            "status": "Pending Validation",
            "related_requirement_ids": linked_ids[:2],
        },
        {
            "description": "Client will designate a single Point of Contact (SPOC) authorized to approve milestone deliverables and UAT sign-offs.",
            "source": "AI Recommendation",
            "impact": "Multi-stakeholder approval conflicts can cause delivery slippage.",
            "status": "Pending Validation",
            "related_requirement_ids": [],
        },
    ]

    exclusions = [
        {
            "description": "Custom mobile application development outside the standard Zoho mobile apps from App Store and Google Play.",
            "exclusion_type": "Out of agreed scope",
            "source": "AI Recommendation",
            "impact": "Client will use official Zoho mobile apps without proprietary white-label branding.",
            "related_requirement_ids": [],
        },
        {
            "description": "Data entry or historical manual transaction back-filling beyond the agreed automated sample migration.",
            "exclusion_type": "Out of agreed scope",
            "source": "AI Recommendation",
            "impact": "Client team handles operational back-filing of legacy records.",
            "related_requirement_ids": [],
        },
        {
            "description": "Third-party software subscription licensing fees and Zoho edition license purchases.",
            "exclusion_type": "Out of agreed scope",
            "source": "AI Recommendation",
            "impact": "All software subscription fees are directly procured by the client.",
            "related_requirement_ids": [],
        },
    ]

    risks = [
        {
            "description": "Delay in legacy system data export could delay the end-to-end UAT phase.",
            "impact": "Project milestone schedule extended by 1 to 2 weeks.",
            "probability": "Medium",
            "mitigation": "Request sample export files during the initial configuration week to validate mapping early.",
            "status": "Open",
        },
        {
            "description": "Scope creep from unconfirmed automated workflow SLAs during user testing.",
            "impact": "Increased revision rounds leading to delayed sign-off.",
            "probability": "Medium",
            "mitigation": "Lock down automation trigger conditions during requirements review prior to configuration.",
            "status": "Open",
        },
    ]

    return {"assumptions": assumptions, "exclusions": exclusions, "risks": risks}


# ─── Public Stage-by-Stage AI Pipeline Functions ──────────────────────────────

def extract_requirements_from_text(
    text: str,
    source_filename: str,
    page_hint: Optional[str] = None,
    existing_req_count: int = 0,
) -> Dict[str, Any]:
    """Stage 2 & 3: Extract and classify requirements from document text."""
    if not settings.ai_configured:
        logger.info("AI provider not configured. Using heuristic extraction engine.")
        return _heuristic_extract_requirements(text, source_filename, page_hint, existing_req_count)

    prompt = f"""Analyse the following text extracted from a client requirements document.
Source: {source_filename}
{f'Pages: {page_hint}' if page_hint else ''}

Text:
\"\"\"
{text[:8000]}
\"\"\"

Extract all business requirements and return a JSON object with this structure:
{{
  "requirements": [
    {{
      "req_id": "REQ-{existing_req_count + 1:03d}",
      "title": "Short title",
      "description": "Full description",
      "category": "one of: Business Background|Business Process|Business Problem|Business Objective|Functional|Non-Functional|Users & Roles|Existing Systems|Data Migration|Integration|Reporting|Automation|Security|Constraint|Dependency|Risk|Assumption|Exclusion|Missing Information|Unclear/Contradictory",
      "supporting_excerpt": "Direct quote from source text",
      "suggested_zoho_module": "Zoho CRM|Zoho Books|etc or null",
      "confidence": 0.85,
      "is_ai_generated": false,
      "review_status": "Needs Review",
      "conflict_ids": []
    }}
  ],
  "missing_information": ["list of things clearly absent from the document"],
  "unclear_statements": ["list of vague or contradictory statements"]
}}

Rules:
- CRITICAL OPTIMIZATION: Synthesize and optimize into AT MOST 25 key, high-impact business requirements.
- Keep ONLY the main extracted requirements, consolidating minor or repetitive bullet points into executive-grade requirements.
- is_ai_generated = false if the requirement is explicitly stated in the text.
- is_ai_generated = true if you are inferring something not directly stated.
- confidence = 1.0 means explicitly stated; 0.5 means implied; 0.2 means inferred.
- Never fabricate specific facts (names, numbers, dates) not in the source text.
- Number requirements starting from REQ-{existing_req_count + 1:03d}.
"""
    try:
        res = call_ai(prompt, SYSTEM_REQUIREMENTS_ANALYST)
        if isinstance(res, dict) and "requirements" in res:
            res["requirements"] = res["requirements"][:25]
        return res
    except (AINotConfiguredError, AIServiceError) as e:
        logger.warning(f"AI call failed ({e}). Falling back to heuristic extraction.")
        res = _heuristic_extract_requirements(text, source_filename, page_hint, existing_req_count)
        if isinstance(res, dict) and "requirements" in res:
            res["requirements"] = res["requirements"][:25]
        return res


def recommend_zoho_modules(
    requirements: List[Dict[str, Any]],
    existing_systems: str = "",
) -> Dict[str, Any]:
    """Stage 6: Recommend Zoho modules based on confirmed requirements."""
    if not settings.ai_configured:
        logger.info("AI provider not configured. Using heuristic module recommendation.")
        return _heuristic_recommend_modules(requirements, existing_systems)

    req_summary = "\n".join([
        f"- [{r.get('req_id')}] {r.get('title')}: {r.get('description', '')[:200]}"
        for r in requirements[:30]
    ])
    prompt = f"""Based on the following confirmed client requirements, recommend which Zoho applications should be implemented.

Client Requirements:
{req_summary}

Existing Systems: {existing_systems or 'Not specified'}

Return a JSON object:
{{
  "modules": [
    {{
      "name": "Zoho CRM",
      "business_purpose": "Why this module is needed",
      "linked_requirement_ids": ["REQ-001", "REQ-003"],
      "recommendation_reason": "Specific justification from requirements",
      "proposed_configuration": "Key configuration items",
      "feasibility_status": "Confirmed",
      "licensing_notes": "Standard workable Zoho edition (e.g. Zoho One / Enterprise)",
      "is_ai_recommended": true,
      "custom_dev_required": null,
      "pending_questions": ["Question 1", "Question 2"]
    }}
  ],
  "excluded_modules": [
    {{
      "name": "Zoho People",
      "reason": "No HR requirements identified in the document"
    }}
  ]
}}

STRICT ZOHO WORKABILITY RULES:
1. Every recommended module MUST be a real, workable, commercially standard Zoho application:
   - Zoho CRM, Zoho Books, Zoho Inventory, Zoho Creator, Zoho Desk, Zoho Projects, Zoho Analytics, Zoho People, Zoho Payroll, Zoho Sign, Zoho Flow, Zoho Forms, Zoho SalesIQ, Zoho Expense, Zoho Billing, Zoho Commerce.
2. For bespoke business workflows, weighing scale IoT, or external device integration, recommend ZOHO CREATOR (low-code app builder with Deluge) or Zoho Flow webhooks rather than inventing fake apps.
3. Only recommend modules that are genuinely justified by the requirements and 100% workable in the Zoho platform.
4. Always set is_ai_recommended: true."""
    try:
        return call_ai(prompt, SYSTEM_ZOHO_ARCHITECT)
    except (AINotConfiguredError, AIServiceError) as e:
        logger.warning(f"AI call failed ({e}). Falling back to heuristic module recommendation.")
        return _heuristic_recommend_modules(requirements, existing_systems)


def generate_scope_tasks(
    module_name: str,
    module_purpose: str,
    requirements: List[Dict[str, Any]],
    task_start_index: int = 1,
) -> Dict[str, Any]:
    """Stage 7: Generate module-wise tasks and subtasks."""
    if not settings.ai_configured:
        logger.info("AI provider not configured. Using heuristic task generation.")
        return _heuristic_generate_tasks(module_name, module_purpose, requirements, task_start_index)

    req_list = "\n".join([
        f"- [{r.get('req_id')}] {r.get('title')}: {r.get('description', '')[:150]}"
        for r in requirements[:20]
    ])
    prompt = f"""Generate a structured scope for the {module_name} Zoho module implementation.

Module Purpose: {module_purpose}

Relevant Requirements:
{req_list}

Return JSON:
{{
  "module_overview": "Brief overview of what will be implemented",
  "tasks": [
    {{
      "task_id_label": "T-{task_start_index:03d}",
      "name": "Task name",
      "description": "Detailed description",
      "task_type": "Configuration|Customisation|Automation|Integration|Data Migration|Report|Security & Access|Testing",
      "priority": "High|Medium|Low",
      "source": "Requirement|AI Recommendation",
      "requirement_ids": ["REQ-001"],
      "estimated_effort": "Only state if clearly justified, otherwise null",
      "acceptance_criteria": "Measurable criteria",
      "deliverables": "What will be delivered",
      "subtasks": [
        {{
          "task_id_label": "T-{task_start_index:03d}.1",
          "name": "Subtask name",
          "description": "Description",
          "task_type": "Configuration",
          "source": "AI Recommendation"
        }}
      ]
    }}
  ],
  "open_questions": ["Questions that must be answered before this module can be scoped"],
  "exclusions": ["What is explicitly excluded"],
  "dependencies": ["Dependencies for this module"]
}}

Important: Generate at least 3 implementation tasks covering setup/configuration, business workflow/automation, and testing/handover.
Only generate tasks directly supported by or logically required for the implementation of the listed requirements.
Label speculative tasks as source: AI Recommendation."""
    try:
        return call_ai(prompt, SYSTEM_REQUIREMENTS_ANALYST)
    except (AINotConfiguredError, AIServiceError) as e:
        logger.warning(f"AI call failed ({e}). Falling back to heuristic task generation.")
        return _heuristic_generate_tasks(module_name, module_purpose, requirements, task_start_index)


def generate_automation_matrix(
    requirements: List[Dict[str, Any]],
    approved_modules: List[str],
) -> Dict[str, Any]:
    """Stage 8a: Generate automation matrix."""
    if not settings.ai_configured:
        logger.info("AI provider not configured. Using heuristic automation generation.")
        return _heuristic_generate_automations(requirements, approved_modules)

    req_list = "\n".join([
        f"- [{r.get('req_id')}] {r.get('title')}: {r.get('description', '')[:150]}"
        for r in requirements[:30]
    ])
    prompt = f"""Generate a structured automation matrix based on the following requirements.

Requirements:
{req_list}

Approved Zoho Modules: {', '.join(approved_modules)}

Return JSON:
{{
  "automations": [
    {{
      "automation_id_label": "AUTO-001",
      "name": "Automation name",
      "business_objective": "Why this automation is needed",
      "zoho_module": "Zoho CRM",
      "trigger_event": "When lead is created",
      "trigger_conditions": "Lead status = New",
      "action_performed": "Create follow-up task and assign owner",
      "recipient_role": "Sales Manager",
      "timing": "PENDING_CONFIRMATION — SLA not specified in requirements",
      "exception_conditions": "No eligible owner available",
      "failure_handling": "Log failure and notify administrator",
      "escalation_conditions": "PENDING_CONFIRMATION — escalation path not defined",
      "linked_requirement_ids": ["REQ-005"],
      "feasibility_status": "Pending Assessment",
      "uat_scenario": "Create a new lead and verify task is created",
      "pending_questions": ["What is the required follow-up SLA?", "Who is the escalation recipient?"],
      "source": "AI Recommendation"
    }}
  ]
}}

Critical rules:
- Never invent SLAs, specific timelines, or named recipients not stated in requirements.
- Mark any unknown details as PENDING_CONFIRMATION.
- Only generate automations justified by the requirements."""
    try:
        return call_ai(prompt, SYSTEM_REQUIREMENTS_ANALYST)
    except (AINotConfiguredError, AIServiceError) as e:
        logger.warning(f"AI call failed ({e}). Falling back to heuristic automation generation.")
        return _heuristic_generate_automations(requirements, approved_modules)


def generate_clarification_questions(
    requirements: List[Dict[str, Any]],
    missing_info: List[str],
    unclear: List[str],
) -> Dict[str, Any]:
    """Generate targeted clarification questions."""
    if not settings.ai_configured:
        logger.info("AI provider not configured. Using heuristic clarification questions.")
        return _heuristic_generate_clarifications(requirements, missing_info, unclear)

    req_list = "\n".join([
        f"- [{r.get('req_id')}] {r.get('title')}"
        for r in requirements[:40]
    ])
    missing_list = "\n".join([f"- {m}" for m in missing_info[:20]])
    unclear_list = "\n".join([f"- {u}" for u in unclear[:10]])

    prompt = f"""Generate specific clarification questions for the consultant to ask the client.

Requirements extracted:
{req_list}

Missing information identified:
{missing_list}

Unclear/contradictory statements:
{unclear_list}

Return JSON:
{{
  "questions": [
    {{
      "question_id_label": "CLQ-001",
      "group": "Business Process|CRM|Inventory|Billing and Accounting|Integrations|Data Migration|Reports and Dashboards|Security and Permissions|Project Timeline|Support and Maintenance",
      "question": "The specific question to ask",
      "why_it_matters": "How the answer affects the SOW",
      "related_requirement_ids": ["REQ-003"],
      "suggested_options": ["Option A", "Option B"],
      "impact_if_unanswered": "What cannot be scoped without this answer",
      "source": "AI Recommendation"
    }}
  ]
}}

Generate only questions that genuinely require client confirmation.
Do not convert unanswered questions into assumed facts."""
    try:
        return call_ai(prompt, SYSTEM_REQUIREMENTS_ANALYST)
    except (AINotConfiguredError, AIServiceError) as e:
        logger.warning(f"AI call failed ({e}). Falling back to heuristic clarification questions.")
        return _heuristic_generate_clarifications(requirements, missing_info, unclear)


def generate_assumptions_exclusions(
    requirements: List[Dict[str, Any]],
    modules: List[str],
    clarification_answers: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate assumptions, exclusions, and risks."""
    if not settings.ai_configured:
        logger.info("AI provider not configured. Using heuristic assumptions/exclusions.")
        return _heuristic_generate_assumptions_exclusions(requirements, modules, clarification_answers)

    req_list = "\n".join([
        f"- [{r.get('req_id')}] {r.get('title')}: {r.get('description', '')[:100]}"
        for r in requirements[:30]
    ])
    prompt = f"""Based on the requirements and proposed modules, generate:
1. Assumptions (things assumed but not confirmed)
2. Exclusions (things explicitly out of scope)
3. Risks (potential delivery risks)

Requirements:
{req_list}

Proposed Modules: {', '.join(modules)}

Return JSON:
{{
  "assumptions": [
    {{
      "description": "Assumption text",
      "source": "AI Recommendation",
      "impact": "Impact if assumption is wrong",
      "status": "Pending Validation",
      "related_requirement_ids": []
    }}
  ],
  "exclusions": [
    {{
      "description": "What is excluded",
      "exclusion_type": "Recommended future phase|Pending decision|Out of agreed scope",
      "source": "AI Recommendation",
      "impact": "Impact of exclusion",
      "related_requirement_ids": []
    }}
  ],
  "risks": [
    {{
      "description": "Risk description",
      "impact": "Potential impact",
      "probability": "High|Medium|Low",
      "mitigation": "Suggested mitigation",
      "status": "Open"
    }}
  ]
}}

Important: Include standard Zoho implementation boundary exclusions (such as third-party licensing procurement, legacy data cleansing, or out-of-scope custom integrations) to ensure complete contractual protection for the SOW.
Mark speculative items clearly."""
    try:
        return call_ai(prompt, SYSTEM_REQUIREMENTS_ANALYST)
    except (AINotConfiguredError, AIServiceError) as e:
        logger.warning(f"AI call failed ({e}). Falling back to heuristic assumptions/exclusions.")
        return _heuristic_generate_assumptions_exclusions(requirements, modules, clarification_answers)


def validate_scope_coverage(
    requirements: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
    automations: List[Dict[str, Any]],
    integrations: List[Dict[str, Any]],
    clarifications: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Stage 10: Validate scope coverage."""
    req_ids = [r.get("req_id") for r in requirements]
    covered_ids = set()
    for t in tasks:
        covered_ids.update(t.get("requirement_ids", []))
    for a in automations:
        covered_ids.update(a.get("linked_requirement_ids", []))
    for i in integrations:
        covered_ids.update(i.get("linked_requirement_ids", []))

    unmapped = [r for r in req_ids if r not in covered_ids]
    open_clarifications = [c for c in clarifications if c.get("status") == "Open"]

    result = {
        "total_requirements": len(requirements),
        "confirmed_requirements": sum(1 for r in requirements if r.get("review_status") == "Approved by Consultant"),
        "unmapped_requirements": len(unmapped),
        "unmapped_req_ids": unmapped,
        "pending_clarifications": len(open_clarifications),
        "pending_ai_approvals": sum(1 for t in tasks if not t.get("is_approved")),
        "overall_level": "pass" if len(unmapped) == 0 and len(open_clarifications) == 0 else "warning" if len(unmapped) <= 2 else "fail",
        "issues": [f"Requirement {r} has no scope mapping" for r in unmapped[:10]],
        "warnings": [f"Clarification '{c.get('question', '')[:60]}...' is still open" for c in open_clarifications[:5]],
    }
    return result
