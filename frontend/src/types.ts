export interface User {
  id: string
  email: string
  full_name: string
  role: 'admin' | 'consultant' | 'reviewer'
  organization_id: string
  is_active: boolean
}

export interface Project {
  id: string
  organization_id: string
  owner_id: string
  client_name: string
  project_name: string
  prepared_by?: string
  status: string
  primary_zoho_edition?: string
  target_go_live_date?: string
  description?: string
  created_at: string
  updated_at?: string
  stats?: {
    document_count: number
    requirement_count: number
    module_count: number
    task_count: number
    automation_count: number
    open_clarifications_count: number
  }
}

export interface UploadedDoc {
  id: string
  original_filename: string
  file_format: string
  file_size_bytes: number
  status: string
  extraction_method?: string
  page_count?: number
  ocr_performed?: boolean
  is_excluded: boolean
  section_count?: number
  created_at: string
}

export interface ExtractedSection {
  id: string
  document_id: string
  heading?: string
  content: string
  section_order: number
  char_count: number
  page_number?: number
  is_excluded: boolean
}

export interface Requirement {
  id: string
  project_id: string
  req_id: string
  title: string
  description: string
  category: string
  source_filename?: string
  source_page?: string
  source_heading?: string
  supporting_excerpt?: string
  suggested_zoho_module?: string
  confidence: number
  is_ai_generated: boolean
  review_status: string
  consultant_comments?: string
  conflict_ids: string[]
  created_at: string
}

export interface ZohoCatalogueModule {
  id: string
  name: string
  display_name: string
  category: string
  description: string
}

export interface ModuleMapping {
  id: string
  project_id: string
  module_id: string
  module_name: string
  module_slug: string
  business_purpose: string
  recommendation_reason: string
  linked_requirement_ids: string[]
  proposed_configuration?: string
  feasibility_status: string
  is_approved: boolean
  is_ai_recommended: boolean
  consultant_notes?: string
  licensing_notes?: string
  custom_dev_required?: string
  created_at: string
}

export interface ScopeTask {
  id: string
  project_id: string
  module_mapping_id?: string
  task_id_label: string
  name: string
  description: string
  task_type: string
  priority: string
  source: string
  requirement_ids: string[]
  estimated_effort?: string
  acceptance_criteria?: string
  deliverables?: string
  is_approved: boolean
  subtasks: ScopeTask[]
}

export interface AutomationItem {
  id: string
  project_id: string
  automation_id_label: string
  name: string
  business_objective: string
  zoho_module?: string
  trigger_event?: string
  trigger_conditions?: string
  action_performed?: string
  recipient_role?: string
  timing?: string
  exception_conditions?: string
  failure_handling?: string
  escalation_conditions?: string
  linked_requirement_ids: string[]
  feasibility_status?: string
  uat_scenario?: string
  pending_questions?: string[]
  source?: string
  is_approved?: boolean
}

export interface IntegrationItem {
  id: string
  project_id: string
  integration_id_label: string
  source_app: string
  destination_app: string
  data_direction: string
  data_exchanged: string
  integration_method?: string
  business_purpose?: string
  feasibility_status?: string
  api_connector?: string
  trigger_or_frequency?: string
  auth_method?: string
  linked_requirement_ids: string[]
}

export interface ClarificationQuestion {
  id: string
  project_id: string
  question_id_label: string
  category?: string
  question: string
  why_it_matters?: string
  related_requirement_ids: string[]
  suggested_options?: string[]
  impact_if_unanswered?: string
  client_response?: string
  status: string
  resolved_at?: string
}

export interface AssumptionItem {
  id: string
  project_id: string
  description: string
  source: string
  impact?: string
  status: string
  related_requirement_ids: string[]
}

export interface ExclusionItem {
  id: string
  project_id: string
  description: string
  exclusion_type: string
  source: string
  impact?: string
}

export interface RiskItem {
  id: string
  project_id: string
  description: string
  impact: string
  probability: string
  mitigation?: string
  status: string
}

export interface ValidationSummary {
  total_requirements: number
  confirmed_requirements: number
  unmapped_requirements: number
  unmapped_req_ids: string[]
  pending_clarifications: number
  pending_ai_approvals: number
  overall_level: 'pass' | 'warning' | 'fail'
  issues: string[]
  warnings: string[]
  consultant_acknowledged?: boolean
}

export interface SowDocumentItem {
  id: string
  project_id: string
  version_number: number
  status: string
  docx_available: boolean
  pdf_available: boolean
  unresolved_placeholders: string[]
  validation_result: any
  generated_at?: string
  created_at: string
}

export interface SowTemplateItem {
  id: string
  name: string
  description?: string
  active_version?: {
    id: string
    version_number: string | number
    status: string
    original_filename?: string
    detected_placeholders?: string[]
  }
  versions?: Array<{
    id: string
    template_id: string
    version_number: string
    original_filename?: string
    status: string
    placeholder_map?: Record<string, string>
    change_summary?: string
    created_at?: string
  }>
}
