"""
ScopePilot AI — Database Models (SQLAlchemy ORM)
All tables with UUID PKs, timestamps, FK constraints, and indexes.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, DateTime,
    ForeignKey, JSON, Enum as SAEnum, Index, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    pass


def gen_uuid():
    return str(uuid.uuid4())


# ─── Enumerations ──────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CONSULTANT = "consultant"
    REVIEWER = "reviewer"

class ProjectStatus(str, enum.Enum):
    DRAFT = "Draft"
    DOCUMENTS_UPLOADED = "Documents Uploaded"
    ANALYSING = "Analysing"
    REQUIREMENTS_REVIEW = "Requirements Review"
    SCOPE_REVIEW = "Scope Review"
    AWAITING_CLARIFICATION = "Awaiting Clarification"
    READY_FOR_SOW = "Ready for SOW"
    SOW_DRAFT = "SOW Draft"
    UNDER_REVIEW = "Under Review"
    APPROVED = "Approved"
    ARCHIVED = "Archived"

class DocStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    FAILED = "failed"
    EXCLUDED = "excluded"

class RequirementCategory(str, enum.Enum):
    BACKGROUND = "Business Background"
    PROCESS = "Business Process"
    PROBLEM = "Business Problem"
    OBJECTIVE = "Business Objective"
    FUNCTIONAL = "Functional"
    NON_FUNCTIONAL = "Non-Functional"
    USERS_ROLES = "Users & Roles"
    EXISTING_SYSTEMS = "Existing Systems"
    DATA_MIGRATION = "Data Migration"
    INTEGRATION = "Integration"
    REPORTING = "Reporting"
    AUTOMATION = "Automation"
    SECURITY = "Security"
    CONSTRAINT = "Constraint"
    DEPENDENCY = "Dependency"
    RISK = "Risk"
    ASSUMPTION = "Assumption"
    EXCLUSION = "Exclusion"
    MISSING_INFO = "Missing Information"
    UNCLEAR = "Unclear/Contradictory"

class RequirementStatus(str, enum.Enum):
    CONFIRMED_FROM_SOURCE = "Confirmed from Source"
    NEEDS_REVIEW = "Needs Review"
    PENDING_CLIENT_CLARIFICATION = "Pending Client Clarification"
    APPROVED_BY_CONSULTANT = "Approved by Consultant"
    REJECTED = "Rejected"

class TaskType(str, enum.Enum):
    CONFIGURATION = "Configuration"
    CUSTOMISATION = "Customisation"
    AUTOMATION = "Automation"
    INTEGRATION = "Integration"
    DATA_MIGRATION = "Data Migration"
    REPORT = "Report"
    SECURITY = "Security & Access"
    TESTING = "Testing"

class TaskSource(str, enum.Enum):
    REQUIREMENT = "Requirement"
    CONSULTANT_ADDITION = "Consultant Addition"
    AI_RECOMMENDATION = "AI Recommendation"

class ClarificationStatus(str, enum.Enum):
    OPEN = "Open"
    ANSWERED = "Answered"
    DEFERRED = "Deferred"
    NOT_APPLICABLE = "Not Applicable"

class FeasibilityStatus(str, enum.Enum):
    CONFIRMED = "Confirmed"
    REQUIRES_VERIFICATION = "Requires Technical Verification"
    NOT_FEASIBLE = "Not Feasible"
    PENDING = "Pending Assessment"

class TemplateStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"

class SowStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"

class ValidationLevel(str, enum.Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


# ─── Tables ────────────────────────────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    settings = Column(JSON, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    users = relationship("UserProfile", back_populates="organization")
    projects = relationship("Project", back_populates="organization")
    templates = relationship("SowTemplate", back_populates="organization")


class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    supabase_user_id = Column(String(255), unique=True, nullable=False)
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    email = Column(String(255), nullable=False)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.CONSULTANT)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="users")
    projects = relationship("Project", back_populates="owner")

    __table_args__ = (Index("ix_user_profiles_supabase_id", "supabase_user_id"),)


class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("user_profiles.id"), nullable=False)
    client_name = Column(String(255), nullable=False)
    project_name = Column(String(255), nullable=False)
    industry = Column(String(100))
    description = Column(Text)
    existing_systems = Column(Text)
    proposed_zoho_apps = Column(JSON, default=[])
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.DRAFT)
    target_start_date = Column(DateTime(timezone=True))
    target_end_date = Column(DateTime(timezone=True))
    notes = Column(Text)
    active_template_id = Column(UUID(as_uuid=False), ForeignKey("sow_template_versions.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="projects")
    owner = relationship("UserProfile", back_populates="projects")
    documents = relationship("UploadedDocument", back_populates="project", cascade="all, delete-orphan")
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
    module_mappings = relationship("ProjectModuleMapping", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("ScopeTask", back_populates="project", cascade="all, delete-orphan")
    automations = relationship("AutomationItem", back_populates="project", cascade="all, delete-orphan")
    integrations = relationship("IntegrationItem", back_populates="project", cascade="all, delete-orphan")
    clarifications = relationship("ClarificationQuestion", back_populates="project", cascade="all, delete-orphan")
    assumptions = relationship("Assumption", back_populates="project", cascade="all, delete-orphan")
    exclusions = relationship("Exclusion", back_populates="project", cascade="all, delete-orphan")
    risks = relationship("Risk", back_populates="project", cascade="all, delete-orphan")
    sow_documents = relationship("SowDocument", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_projects_org", "organization_id"),
        Index("ix_projects_status", "status"),
    )


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50))
    file_size_bytes = Column(Integer)
    storage_path = Column(String(500))
    status = Column(SAEnum(DocStatus), default=DocStatus.UPLOADED)
    extraction_method = Column(String(50))
    extraction_error = Column(Text)
    page_count = Column(Integer)
    sheet_names = Column(JSON, default=[])
    ocr_performed = Column(Boolean, default=False)
    is_excluded = Column(Boolean, default=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    extracted_at = Column(DateTime(timezone=True))

    project = relationship("Project", back_populates="documents")
    sections = relationship("ExtractedSection", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_uploaded_docs_project", "project_id"),)


class ExtractedSection(Base):
    __tablename__ = "extracted_sections"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    document_id = Column(UUID(as_uuid=False), ForeignKey("uploaded_documents.id"), nullable=False)
    heading = Column(String(500))
    content = Column(Text, nullable=False)
    page_number = Column(Integer)
    sheet_name = Column(String(100))
    section_order = Column(Integer)
    is_excluded = Column(Boolean, default=False)
    char_count = Column(Integer)

    document = relationship("UploadedDocument", back_populates="sections")
    requirements = relationship("Requirement", back_populates="source_section")

    __table_args__ = (Index("ix_extracted_sections_doc", "document_id"),)


class Requirement(Base):
    __tablename__ = "requirements"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    source_section_id = Column(UUID(as_uuid=False), ForeignKey("extracted_sections.id"), nullable=True)
    req_id = Column(String(50), nullable=False)  # REQ-001, etc.
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(SAEnum(RequirementCategory))
    source_filename = Column(String(255))
    source_page = Column(Integer)
    source_heading = Column(String(500))
    supporting_excerpt = Column(Text)
    suggested_zoho_module = Column(String(100))
    confidence = Column(Float)  # 0.0 to 1.0
    is_ai_generated = Column(Boolean, default=False)
    review_status = Column(SAEnum(RequirementStatus), default=RequirementStatus.NEEDS_REVIEW)
    consultant_comments = Column(Text)
    conflict_ids = Column(JSON, default=[])  # IDs of conflicting requirements
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="requirements")
    source_section = relationship("ExtractedSection", back_populates="requirements")

    __table_args__ = (
        Index("ix_requirements_project", "project_id"),
        UniqueConstraint("project_id", "req_id", name="uq_req_id_per_project"),
    )


class ZohoModule(Base):
    __tablename__ = "zoho_modules"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    typical_use_cases = Column(JSON, default=[])
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project_mappings = relationship("ProjectModuleMapping", back_populates="module")


class ProjectModuleMapping(Base):
    __tablename__ = "project_module_mappings"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    module_id = Column(UUID(as_uuid=False), ForeignKey("zoho_modules.id"), nullable=False)
    business_purpose = Column(Text)
    recommendation_reason = Column(Text)
    linked_requirement_ids = Column(JSON, default=[])
    proposed_configuration = Column(Text)
    custom_fields = Column(JSON, default=[])
    workflow_rules = Column(JSON, default=[])
    approval_processes = Column(JSON, default=[])
    custom_dev_required = Column(Text)
    licensing_notes = Column(Text)
    feasibility_status = Column(SAEnum(FeasibilityStatus), default=FeasibilityStatus.PENDING)
    is_approved = Column(Boolean, default=False)
    is_ai_recommended = Column(Boolean, default=True)
    consultant_notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="module_mappings")
    module = relationship("ZohoModule", back_populates="project_mappings")
    tasks = relationship("ScopeTask", back_populates="module_mapping")

    __table_args__ = (
        Index("ix_proj_module_mappings_project", "project_id"),
        UniqueConstraint("project_id", "module_id", name="uq_project_module"),
    )


class ScopeTask(Base):
    __tablename__ = "scope_tasks"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    module_mapping_id = Column(UUID(as_uuid=False), ForeignKey("project_module_mappings.id"), nullable=True)
    parent_task_id = Column(UUID(as_uuid=False), ForeignKey("scope_tasks.id"), nullable=True)
    task_id_label = Column(String(50))  # T-001, T-001.1, etc.
    name = Column(String(500), nullable=False)
    description = Column(Text)
    task_type = Column(SAEnum(TaskType))
    priority = Column(String(20), default="Medium")
    source = Column(SAEnum(TaskSource), default=TaskSource.AI_RECOMMENDATION)
    requirement_ids = Column(JSON, default=[])
    dependencies = Column(JSON, default=[])
    estimated_effort = Column(String(100))
    proposed_owner = Column(String(100))
    acceptance_criteria = Column(Text)
    deliverables = Column(Text)
    exclusions = Column(Text)
    open_questions = Column(Text)
    is_approved = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="tasks")
    module_mapping = relationship("ProjectModuleMapping", back_populates="tasks")
    subtasks = relationship("ScopeTask", backref="parent", remote_side=[id])

    __table_args__ = (Index("ix_scope_tasks_project", "project_id"),)


class AutomationItem(Base):
    __tablename__ = "automation_items"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    automation_id_label = Column(String(50))  # AUTO-001
    name = Column(String(500), nullable=False)
    business_objective = Column(Text)
    zoho_module = Column(String(100))
    trigger_event = Column(String(500))
    trigger_conditions = Column(Text)
    action_performed = Column(Text)
    recipient_role = Column(String(200))
    timing = Column(String(200))
    exception_conditions = Column(Text)
    failure_handling = Column(Text)
    escalation_conditions = Column(Text)
    linked_requirement_ids = Column(JSON, default=[])
    dependencies = Column(JSON, default=[])
    feasibility_status = Column(SAEnum(FeasibilityStatus), default=FeasibilityStatus.PENDING)
    uat_scenario = Column(Text)
    pending_questions = Column(Text)
    is_approved = Column(Boolean, default=False)
    source = Column(SAEnum(TaskSource), default=TaskSource.AI_RECOMMENDATION)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="automations")

    __table_args__ = (Index("ix_automation_items_project", "project_id"),)


class IntegrationItem(Base):
    __tablename__ = "integration_items"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    integration_id_label = Column(String(50))  # INT-001
    source_app = Column(String(200), nullable=False)
    destination_app = Column(String(200), nullable=False)
    data_direction = Column(String(50))  # one-way, bidirectional
    data_exchanged = Column(Text)
    business_purpose = Column(Text)
    trigger_or_frequency = Column(String(200))
    auth_method = Column(String(100))
    api_connector = Column(String(200))
    error_handling = Column(Text)
    duplicate_handling = Column(Text)
    retry_strategy = Column(Text)
    ownership = Column(String(100))
    feasibility_status = Column(SAEnum(FeasibilityStatus), default=FeasibilityStatus.PENDING)
    testing_requirements = Column(Text)
    pending_questions = Column(Text)
    linked_requirement_ids = Column(JSON, default=[])
    is_approved = Column(Boolean, default=False)
    source = Column(SAEnum(TaskSource), default=TaskSource.AI_RECOMMENDATION)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="integrations")

    __table_args__ = (Index("ix_integration_items_project", "project_id"),)


class ClarificationQuestion(Base):
    __tablename__ = "clarification_questions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    question_id_label = Column(String(50))  # CLQ-001
    group = Column(String(100))
    question = Column(Text, nullable=False)
    why_it_matters = Column(Text)
    related_requirement_ids = Column(JSON, default=[])
    suggested_options = Column(JSON, default=[])
    answer = Column(Text)
    responsible_person = Column(String(200))
    status = Column(SAEnum(ClarificationStatus), default=ClarificationStatus.OPEN)
    impact_if_unanswered = Column(Text)
    source = Column(SAEnum(TaskSource), default=TaskSource.AI_RECOMMENDATION)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="clarifications")

    __table_args__ = (Index("ix_clarification_questions_project", "project_id"),)


class Assumption(Base):
    __tablename__ = "assumptions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=False)
    source = Column(String(200))
    impact = Column(Text)
    owner = Column(String(200))
    status = Column(String(50), default="Pending Validation")
    related_requirement_ids = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="assumptions")


class Exclusion(Base):
    __tablename__ = "exclusions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=False)
    exclusion_type = Column(String(100))  # Explicitly excluded | Recommended future phase | Pending decision
    source = Column(String(200))
    impact = Column(Text)
    related_requirement_ids = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="exclusions")


class Risk(Base):
    __tablename__ = "risks"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    description = Column(Text, nullable=False)
    impact = Column(Text)
    probability = Column(String(50))
    mitigation = Column(Text)
    owner = Column(String(200))
    status = Column(String(50), default="Open")
    related_requirement_ids = Column(JSON, default=[])
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="risks")


class SowTemplate(Base):
    __tablename__ = "sow_templates"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="templates")
    versions = relationship("SowTemplateVersion", back_populates="template", cascade="all, delete-orphan")


class SowTemplateVersion(Base):
    __tablename__ = "sow_template_versions"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    template_id = Column(UUID(as_uuid=False), ForeignKey("sow_templates.id"), nullable=False)
    version_number = Column(String(20), nullable=False)
    storage_path = Column(String(500))
    original_filename = Column(String(255))
    status = Column(SAEnum(TemplateStatus), default=TemplateStatus.DRAFT)
    section_map = Column(JSON, default={})     # detected sections with types
    placeholder_map = Column(JSON, default={}) # placeholder → section mapping
    extracted_structure = Column(JSON, default={})
    change_summary = Column(Text)
    published_by = Column(UUID(as_uuid=False), ForeignKey("user_profiles.id"), nullable=True)
    published_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    template = relationship("SowTemplate", back_populates="versions")
    sow_documents = relationship("SowDocument", back_populates="template_version")


class SowDocument(Base):
    __tablename__ = "sow_documents"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    template_version_id = Column(UUID(as_uuid=False), ForeignKey("sow_template_versions.id"), nullable=True)
    version_number = Column(Integer, default=1)
    status = Column(SAEnum(SowStatus), default=SowStatus.DRAFT)
    docx_storage_path = Column(String(500))
    pdf_storage_path = Column(String(500))
    content_snapshot = Column(JSON, default={})  # structured content at time of generation
    validation_result = Column(JSON, default={})
    unresolved_placeholders = Column(JSON, default=[])
    generated_at = Column(DateTime(timezone=True))
    generated_by = Column(UUID(as_uuid=False), ForeignKey("user_profiles.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True))
    approved_by = Column(UUID(as_uuid=False), ForeignKey("user_profiles.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project", back_populates="sow_documents")
    template_version = relationship("SowTemplateVersion", back_populates="sow_documents")


class ValidationResult(Base):
    __tablename__ = "validation_results"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    run_at = Column(DateTime(timezone=True), server_default=func.now())
    total_requirements = Column(Integer, default=0)
    confirmed_requirements = Column(Integer, default=0)
    unmapped_requirements = Column(Integer, default=0)
    pending_clarifications = Column(Integer, default=0)
    pending_ai_approvals = Column(Integer, default=0)
    feasibility_checks_needed = Column(Integer, default=0)
    missing_acceptance_criteria = Column(Integer, default=0)
    template_mapping_issues = Column(Integer, default=0)
    overall_level = Column(SAEnum(ValidationLevel), default=ValidationLevel.FAIL)
    issues = Column(JSON, default=[])
    warnings = Column(JSON, default=[])
    consultant_acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=True)
    user_id = Column(UUID(as_uuid=False), ForeignKey("user_profiles.id"), nullable=True)
    action = Column(String(200), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(255))
    details = Column(JSON, default={})
    ip_address = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_audit_logs_org", "organization_id"),)


class KnowledgeBaseRecord(Base):
    __tablename__ = "knowledge_base_records"
    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=False)
    category = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    tags = Column(JSON, default=[])
    zoho_modules = Column(JSON, default=[])
    is_approved = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=False), ForeignKey("user_profiles.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (Index("ix_kb_records_org_category", "organization_id", "category"),)
