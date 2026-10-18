import axios from 'axios'
import type {
  User, Project, UploadedDoc, Requirement, ModuleMapping,
  ScopeTask, AutomationItem, IntegrationItem, ClarificationQuestion,
  AssumptionItem, ExclusionItem, RiskItem, ValidationSummary,
  SowDocumentItem, SowTemplateItem, ZohoCatalogueModule, ExtractedSection
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Inject JWT token from localStorage
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('scopepilot_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto handle 401
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      // Don't auto clear if trying to login
      if (!err.config.url.includes('/auth/')) {
        localStorage.removeItem('scopepilot_token')
        localStorage.removeItem('scopepilot_user')
        window.dispatchEvent(new Event('auth_state_change'))
      }
    }
    return Promise.reject(err)
  }
)

export function formatApiError(err: any, fallback = 'An unexpected error occurred'): string {
  const detail = err?.response?.data?.detail ?? err?.message ?? err
  if (!detail) return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return (
      detail
        .map((item) => {
          if (typeof item === 'string') return item
          if (item && typeof item === 'object') {
            return item.msg || item.message || JSON.stringify(item)
          }
          return String(item)
        })
        .filter(Boolean)
        .join('; ') || fallback
    )
  }
  if (typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail)
  }
  return String(detail)
}

export const api = {
  // Auth
  async login(email: string, password: string):Promise<{ access_token: string; user: User }> {
    const res = await client.post('/auth/login', { email, password })
    localStorage.setItem('scopepilot_token', res.data.access_token)
    localStorage.setItem('scopepilot_user', JSON.stringify(res.data.user))
    return res.data
  },

  async register(data: { email: string; password: string; full_name: string; organization_name?: string }): Promise<{ access_token: string; user: User }> {
    const res = await client.post('/auth/register', data)
    localStorage.setItem('scopepilot_token', res.data.access_token)
    localStorage.setItem('scopepilot_user', JSON.stringify(res.data.user))
    return res.data
  },

  async getMe(): Promise<User> {
    const res = await client.get('/auth/me')
    return res.data
  },

  logout() {
    localStorage.removeItem('scopepilot_token')
    localStorage.removeItem('scopepilot_user')
    window.dispatchEvent(new Event('auth_state_change'))
  },

  // Projects
  async getProjects(params?: { status?: string; search?: string }): Promise<{ projects: Project[]; total: number }> {
    const res = await client.get('/projects', { params })
    const items = res.data.items || res.data.projects || []
    return { projects: items, total: res.data.total ?? items.length }
  },

  async getProject(id: string): Promise<Project> {
    const res = await client.get(`/projects/${id}`)
    return res.data
  },

  async createProject(data: { client_name: string; project_name: string; prepared_by?: string; primary_zoho_edition?: string; target_go_live_date?: string; description?: string }): Promise<Project> {
    const res = await client.post('/projects', data)
    return res.data
  },

  async updateProject(id: string, data: Partial<Project>): Promise<Project> {
    const res = await client.patch(`/projects/${id}`, data)
    return res.data
  },

  async deleteProject(id: string): Promise<{ message: string; deleted_id: string }> {
    const res = await client.delete(`/projects/${id}`)
    return res.data
  },

  // Documents
  async getDocuments(projectId: string): Promise<{ documents: UploadedDoc[] }> {
    const res = await client.get(`/documents/${projectId}`)
    const docs = Array.isArray(res.data) ? res.data : (res.data.documents || [])
    return { documents: docs }
  },

  async uploadDocument(projectId: string, file: File): Promise<UploadedDoc> {
    const formData = new FormData()
    formData.append('file', file)
    const res = await client.post(`/documents/${projectId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  async getSections(projectId: string, documentId?: string): Promise<{ sections: ExtractedSection[] }> {
    const res = await client.get(`/documents/${projectId}/sections`, {
      params: { document_id: documentId },
    })
    const sects = Array.isArray(res.data) ? res.data : (res.data.sections || [])
    return { sections: sects }
  },

  async deleteDocument(projectId: string, docId: string): Promise<void> {
    await client.delete(`/documents/${projectId}/${docId}`)
  },

  // Requirements
  async getRequirements(projectId: string, params?: { category?: string; status?: string }): Promise<{ requirements: Requirement[]; total: number }> {
    const res = await client.get(`/requirements/${projectId}`, { params })
    const items = Array.isArray(res.data) ? res.data : (res.data.items || res.data.requirements || [])
    return { requirements: items, total: res.data.total ?? items.length }
  },

  async runRequirementsAnalysis(projectId: string, documentIds?: string[]): Promise<{ message: string }> {
    const res = await client.post(`/requirements/${projectId}/analyse`, { document_ids: documentIds })
    return res.data
  },

  async updateRequirement(projectId: string, reqId: string, data: Partial<Requirement>): Promise<Requirement> {
    const res = await client.patch(`/requirements/${projectId}/${reqId}`, data)
    return res.data
  },

  async createRequirement(projectId: string, data: any): Promise<Requirement> {
    const res = await client.post(`/requirements/${projectId}`, data)
    return res.data
  },

  async deleteRequirement(projectId: string, reqId: string): Promise<void> {
    await client.delete(`/requirements/${projectId}/${reqId}`)
  },

  // Modules
  async getZohoCatalogue(): Promise<{ modules: ZohoCatalogueModule[] }> {
    const res = await client.get('/modules/catalogue')
    const mods = Array.isArray(res.data) ? res.data : (res.data.modules || [])
    return { modules: mods }
  },

  async getProjectModules(projectId: string): Promise<{ modules: ModuleMapping[] }> {
    const res = await client.get(`/modules/${projectId}`)
    const mods = Array.isArray(res.data) ? res.data : (res.data.modules || [])
    return { modules: mods }
  },

  async runModuleRecommendation(projectId: string): Promise<{ message: string }> {
    const res = await client.post(`/modules/${projectId}/recommend`)
    return res.data
  },

  async addProjectModule(projectId: string, moduleId: string, businessPurpose: string): Promise<ModuleMapping> {
    const res = await client.post(`/modules/${projectId}`, {
      module_id: moduleId,
      business_purpose: businessPurpose,
    })
    return res.data
  },

  async updateProjectModule(projectId: string, mappingId: string, data: Partial<ModuleMapping>): Promise<ModuleMapping> {
    const res = await client.patch(`/modules/${projectId}/${mappingId}`, data)
    return res.data
  },

  async removeModule(projectId: string, mappingId: string): Promise<void> {
    await client.delete(`/modules/${projectId}/${mappingId}`)
  },

  // Scope Tasks
  async getTasks(projectId: string, moduleMappingId?: string): Promise<{ tasks: ScopeTask[] }> {
    const res = await client.get(`/tasks/${projectId}`, {
      params: { module_mapping_id: moduleMappingId },
    })
    const ts = Array.isArray(res.data) ? res.data : (res.data.tasks || [])
    return { tasks: ts }
  },

  async runTaskGeneration(projectId: string, moduleMappingId: string): Promise<{ message: string }> {
    const res = await client.post(`/tasks/${projectId}/generate`, {
      module_mapping_id: moduleMappingId,
    })
    return res.data
  },

  async updateTask(projectId: string, taskId: string, data: Partial<ScopeTask>): Promise<ScopeTask> {
    const res = await client.patch(`/tasks/${projectId}/${taskId}`, data)
    return res.data
  },

  async createTask(projectId: string, data: any): Promise<ScopeTask> {
    const res = await client.post(`/tasks/${projectId}`, data)
    return res.data
  },

  async deleteTask(projectId: string, taskId: string): Promise<void> {
    await client.delete(`/tasks/${projectId}/${taskId}`)
  },

  // Automations
  async getAutomations(projectId: string): Promise<{ automations: AutomationItem[] }> {
    const res = await client.get(`/automations/${projectId}`)
    const autos = Array.isArray(res.data) ? res.data : (res.data.automations || [])
    return { automations: autos }
  },

  async runAutomationGeneration(projectId: string): Promise<{ message: string }> {
    const res = await client.post(`/automations/${projectId}/generate`)
    return res.data
  },

  async updateAutomation(projectId: string, automationId: string, data: Partial<AutomationItem>): Promise<AutomationItem> {
    const res = await client.patch(`/automations/${projectId}/${automationId}`, data)
    return res.data
  },

  async deleteAutomation(projectId: string, automationId: string): Promise<void> {
    await client.delete(`/automations/${projectId}/${automationId}`)
  },

  // Integrations & Clarifications
  async getIntegrations(projectId: string): Promise<{ integrations: IntegrationItem[] }> {
    const res = await client.get(`/integrations/${projectId}/integrations`)
    const ints = Array.isArray(res.data) ? res.data : (res.data.integrations || [])
    return { integrations: ints }
  },

  async runIntegrationGeneration(projectId: string): Promise<{ message: string }> {
    const res = await client.post(`/integrations/${projectId}/integrations/generate`)
    return res.data
  },

  async getClarifications(projectId: string): Promise<{ questions: ClarificationQuestion[] }> {
    const res = await client.get(`/integrations/${projectId}/clarifications`)
    const qs = Array.isArray(res.data) ? res.data : (res.data.questions || [])
    return { questions: qs }
  },

  async runClarificationGeneration(projectId: string): Promise<{ message: string }> {
    const res = await client.post(`/integrations/${projectId}/clarifications/generate`)
    return res.data
  },

  async answerClarification(projectId: string, questionId: string, answer: string): Promise<ClarificationQuestion> {
    const res = await client.patch(`/integrations/${projectId}/clarifications/${questionId}`, {
      answer,
    })
    return res.data
  },

  async deleteClarification(projectId: string, questionId: string): Promise<void> {
    await client.delete(`/integrations/${projectId}/clarifications/${questionId}`)
  },

  // Assumptions, Exclusions, Risks
  async getAssumptions(projectId: string): Promise<{ assumptions: AssumptionItem[]; exclusions: ExclusionItem[]; risks: RiskItem[] }> {
    const res = await client.get(`/assumptions/${projectId}`)
    return res.data
  },

  async runAssumptionsGeneration(projectId: string): Promise<{ message: string }> {
    const res = await client.post(`/assumptions/${projectId}/generate`)
    return res.data
  },

  // Validation
  async runValidation(projectId: string): Promise<ValidationSummary> {
    const res = await client.post(`/validation/${projectId}/run`)
    return res.data
  },

  async acknowledgeValidation(projectId: string): Promise<{ acknowledged: boolean }> {
    const res = await client.post(`/validation/${projectId}/acknowledge`)
    return res.data
  },

  // SOW
  async getSowHistory(projectId: string): Promise<{ documents: SowDocumentItem[] }> {
    const res = await client.get(`/sow/${projectId}`)
    const docs = Array.isArray(res.data) ? res.data : (res.data.documents || [])
    return { documents: docs }
  },

  async generateSow(projectId: string, templateVersionId?: string): Promise<SowDocumentItem> {
    const res = await client.post(`/sow/${projectId}/generate`, {
      template_version_id: templateVersionId,
    })
    return res.data
  },

  getSowDownloadUrl(projectId: string, docId: string): string {
    return `${API_BASE}/sow/${projectId}/download/${docId}`
  },

  async deleteSow(projectId: string, sowId: string): Promise<{ message: string; deleted_id: string }> {
    const res = await client.delete(`/sow/${projectId}/${sowId}`)
    return res.data
  },

  // Templates
  async getTemplates(): Promise<{ templates: SowTemplateItem[] }> {
    const res = await client.get('/templates')
    const tpls = Array.isArray(res.data) ? res.data : (res.data.templates || res.data.items || [])
    return { templates: tpls }
  },

  async uploadTemplate(file: File, name: string, description?: string): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('name', name)
    if (description) formData.append('description', description)
    const res = await client.post('/templates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return res.data
  },

  async publishTemplateVersion(versionId: string): Promise<any> {
    const res = await client.post(`/templates/versions/${versionId}/publish`)
    return res.data
  },

  async deleteTemplate(templateId: string): Promise<{ message: string; deleted_id: string }> {
    const res = await client.delete(`/templates/${templateId}`)
    return res.data
  },
}
