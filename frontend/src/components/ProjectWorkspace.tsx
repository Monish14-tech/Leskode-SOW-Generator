import React, { useState, useEffect } from 'react'
import {
  FileText, CheckSquare, Layers, ListTodo, Zap, HelpCircle,
  ShieldAlert, CheckCircle2, Download, RefreshCw, Upload,
  Plus, ChevronRight, AlertTriangle, ArrowLeft, Eye, Edit3, Check
} from 'lucide-react'
import { api } from '../api'
import type {
  Project, UploadedDoc, ExtractedSection, Requirement,
  ModuleMapping, ScopeTask, AutomationItem, IntegrationItem,
  ClarificationQuestion, AssumptionItem, ExclusionItem, RiskItem,
  ValidationSummary, SowDocumentItem, ZohoCatalogueModule
} from '../types'

interface ProjectWorkspaceProps {
  project: Project
  onBack: () => void
  onProjectUpdated: (p: Project) => void
}

type TabType =
  | 'docs'
  | 'requirements'
  | 'modules'
  | 'tasks'
  | 'automations'
  | 'integrations'
  | 'assumptions'
  | 'validation'
  | 'sow'

export const ProjectWorkspace: React.FC<ProjectWorkspaceProps> = ({
  project,
  onBack,
  onProjectUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('docs')
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [alert, setAlert] = useState<{ text: string; isError?: boolean } | null>(null)

  // Data states
  const [docs, setDocs] = useState<UploadedDoc[]>([])
  const [sections, setSections] = useState<ExtractedSection[]>([])
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [reqs, setReqs] = useState<Requirement[]>([])
  const [modules, setModules] = useState<ModuleMapping[]>([])
  const [catalogue, setCatalogue] = useState<ZohoCatalogueModule[]>([])
  const [selectedCatalogueId, setSelectedCatalogueId] = useState('')
  const [tasks, setTasks] = useState<ScopeTask[]>([])
  const [automations, setAutomations] = useState<AutomationItem[]>([])
  const [integrations, setIntegrations] = useState<IntegrationItem[]>([])
  const [clarifications, setClarifications] = useState<ClarificationQuestion[]>([])
  const [assumptions, setAssumptions] = useState<AssumptionItem[]>([])
  const [exclusions, setExclusions] = useState<ExclusionItem[]>([])
  const [risks, setRisks] = useState<RiskItem[]>([])
  const [validation, setValidation] = useState<ValidationSummary | null>(null)
  const [sowDocs, setSowDocs] = useState<SowDocumentItem[]>([])

  // Clarification reply state
  const [replyText, setReplyText] = useState<{ [key: string]: string }>({})

  // Category filter for requirements
  const [reqCategoryFilter, setReqCategoryFilter] = useState('ALL')
  const [reqTypeFilter, setReqTypeFilter] = useState('ALL') // ALL, CONFIRMED, AI

  useEffect(() => {
    loadAllData()
  }, [project.id])

  const loadAllData = async () => {
    setLoading(true)
    try {
      const [
        docsRes,
        reqsRes,
        modulesRes,
        catalogueRes,
        tasksRes,
        autoRes,
        intRes,
        clqRes,
        assumpRes,
        sowRes,
      ] = await Promise.all([
        api.getDocuments(project.id).catch(() => ({ documents: [] })),
        api.getRequirements(project.id).catch(() => ({ requirements: [] })),
        api.getProjectModules(project.id).catch(() => ({ modules: [] })),
        api.getZohoCatalogue().catch(() => ({ modules: [] })),
        api.getTasks(project.id).catch(() => ({ tasks: [] })),
        api.getAutomations(project.id).catch(() => ({ automations: [] })),
        api.getIntegrations(project.id).catch(() => ({ integrations: [] })),
        api.getClarifications(project.id).catch(() => ({ questions: [] })),
        api.getAssumptions(project.id).catch(() => ({ assumptions: [], exclusions: [], risks: [] })),
        api.getSowHistory(project.id).catch(() => ({ documents: [] })),
      ])

      setDocs(docsRes.documents || [])
      setReqs(reqsRes.requirements || [])
      setModules(modulesRes.modules || [])
      setCatalogue(catalogueRes.modules || [])
      setTasks(tasksRes.tasks || [])
      setAutomations(autoRes.automations || [])
      setIntegrations(intRes.integrations || [])
      setClarifications(clqRes.questions || [])
      setAssumptions(assumpRes.assumptions || [])
      setExclusions(assumpRes.exclusions || [])
      setRisks(assumpRes.risks || [])
      setSowDocs(sowRes.documents || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const showNotice = (text: any, isError = false) => {
    let msg = text
    if (typeof text !== 'string') {
      if (Array.isArray(text)) {
        msg = text.map((t) => (typeof t === 'string' ? t : (t?.msg || JSON.stringify(t)))).join('; ')
      } else if (text && typeof text === 'object') {
        msg = text.msg || text.message || JSON.stringify(text)
      } else {
        msg = String(text)
      }
    }
    setAlert({ text: msg, isError })
    setTimeout(() => setAlert(null), 5000)
  }

  // 1. Upload Doc
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setActionLoading(true)
    try {
      const doc = await api.uploadDocument(project.id, file)
      showNotice(`Document "${doc.original_filename}" uploaded and processed!`)
      loadAllData()
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'Upload failed', true)
    } finally {
      setActionLoading(false)
    }
  }

  // Load Monish Enterprises / Project Sample Requirements
  const handleLoadSampleRequirements = async () => {
    setActionLoading(true)
    try {
      const clientTitle = project.client_name || 'Monish Enterprises'
      const sampleText = `${clientTitle.toUpperCase()} — ZOHO ONE IMPLEMENTATION SPECIFICATION
1. Executive Summary & Business Background:
${clientTitle} is an industrial distributor and dealer of steel products, pipes, roofing sheets, fasteners, and hardware components based in Coimbatore, Tamil Nadu.
Currently, operations are handled through manual registers, offline spreadsheets, and disconnected phone/WhatsApp messages, leading to quote delays, inventory discrepancies, and lack of real-time margin visibility.
The objective is to deploy an end-to-end connected Zoho ecosystem connecting customer inquiry through pricing, quotation, inventory allocation, dispatch, GST invoicing, and executive margin dashboards.

2. Lead Intake & Sales Pipeline (Zoho CRM):
• Centralize inbound inquiries from IndiaMART, website contact forms, WhatsApp Business, phone calls, and walk-in trade customers into Zoho CRM Leads.
• Automated round-robin lead assignment to sales coordinators with deduplication on GST number, mobile, and email.
• Follow-up activity scheduling, call logs, and SLA alert to General Manager if a lead is untouched for more than 45 minutes.
• Deal pipeline stages: Lead Qualified -> Site / Requirement Analysis -> Quotation Submitted -> Price Negotiation -> Order Confirmed -> Closed Won / Lost.
• Order Confirmed status triggers automated Sales Order creation in Zoho Books and cross-team project creation in Zoho Projects.

3. Quotation & Daily Price Engine (Zoho Creator & CRM):
• In the steel and industrial hardware trade, purchase rates change daily from mills and manufacturers.
• Daily Market Price Board built in Zoho Creator where daily mill rates, landed freight costs, and category margins (Retail, Builder, Fabricator, Wholesale Dealer) are set each morning and approved by the Owner.
• CRM Quotations automatically pull today's approved rate for the selected customer price category.
• Margin Guard: Any quotation discount below the configured margin floor requires mobile approval from the Owner.

4. Financial Accounting & Invoicing (Zoho Books):
• Generation of statutory GST-compliant invoices with automatic HSN codes, e-invoice (IRN), and e-way bill from confirmed Sales Orders.
• Vendor Purchase Orders linked to mill accounts, three-way matching (PO -> Goods Receipt Note -> Vendor Bill) before payment release.
• Customer credit limits, payment terms, and automated payment reminder notifications for overdue accounts.
• Automated bank feed reconciliation and monthly statutory GST return summaries.

5. Inventory & Multi-Godown Stock Management (Zoho Inventory):
• Centralized item master organized into item groups (Structural Steel, TMT Bars, Roofing Sheets, Bolts & Fasteners, Industrial Tools).
• Multi-unit handling with automatic unit conversion (metric tonnes, kilograms, bundles, pieces, square feet).
• Multi-godown tracking across Main Central Yard, Processing Warehouse, and City Trade Branch with inter-godown transfer orders.
• Heat number, batch number, and mill test certificate (MTC) tracking upon stock inwarding.
• Automated reorder alerts when inventory levels breach minimum safety stock thresholds.

6. Fulfillment, Weighbridge & Gate Management (Zoho Creator & Inventory):
• Fulfillment orders created upon Deal confirmation in CRM.
• Vehicle Inward Gate Entry referencing Purchase Order and capturing weighbridge slip gross/tare weight.
• Vehicle Outward Gate Pass referencing Sales Order with loaded weight vs billed weight verification. Dispatches exceeding tolerance held for supervisor approval.
• Accepted GRN quantities update Zoho Inventory physical stock in real time.

7. Human Resources & Payroll (Zoho People & Zoho Payroll):
• Employee records, department hierarchy, shift schedules, and geofenced attendance tracking for yard and field sales staff in Zoho People.
• Leave management with approval workflows (Employee -> Manager -> HR).
• Monthly attendance and LOP data synchronized to Zoho Payroll for automated salary calculation, statutory deductions (PF, ESI, PT), and payslip generation.
• Completed pay run posts journal entries directly to Zoho Books.

8. Cross-Module Collaboration & Executive Intelligence (Zoho Projects & Analytics):
• Automated Zoho Projects workspace created for confirmed high-value and custom fabrication orders.
• Executive Dashboards in Zoho Analytics: Daily Realized Margin vs Replacement Margin, Sales Rep Conversion Ratios, Stock Ageing & Revaluation Report, and Customer Outstanding Ageing.

9. Project Assumptions & Exclusions:
• Client will provide single Point of Contact (SPOC) and master data in CSV format.
• Zoho licenses and third-party WhatsApp Business API fees are procured directly by ${clientTitle}.
• Weighbridge hardware and barcode printer procurement is outside software scope.`

      const blob = new Blob([sampleText], { type: 'text/plain' })
      const file = new File([blob], `${clientTitle.toLowerCase().replace(/\\s+/g, '_')}_requirements.txt`, { type: 'text/plain' })
      const doc = await api.uploadDocument(project.id, file)
      showNotice(`Requirements specification loaded successfully!`)
      await loadAllData()
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'Failed to load sample specification', true)
    } finally {
      setActionLoading(false)
    }
  }

  // View sections
  const handleViewSections = async (docId: string) => {
    setSelectedDocId(docId)
    try {
      const res = await api.getSections(project.id, docId)
      setSections(res.sections || [])
    } catch (err) {
      console.error(err)
    }
  }

  // 2. Run AI Requirements Analysis
  const handleRunRequirementsAnalysis = async () => {
    setActionLoading(true)
    try {
      const res = await api.runRequirementsAnalysis(project.id)
      showNotice(res.message || 'Requirements analysis completed!')
      await loadAllData()
      setActiveTab('requirements')
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'Analysis failed', true)
    } finally {
      setActionLoading(false)
    }
  }

  // Requirement status change
  const handleRequirementStatus = async (reqId: string, status: string) => {
    try {
      await api.updateRequirement(project.id, reqId, { review_status: status })
      setReqs((prev) =>
        prev.map((r) => (r.id === reqId ? { ...r, review_status: status } : r))
      )
      showNotice(`Requirement updated to "${status}"`)
    } catch (err) {
      showNotice('Failed to update requirement', true)
    }
  }

  // 3. Recommend Zoho Modules
  const handleRecommendModules = async () => {
    setActionLoading(true)
    try {
      const res = await api.runModuleRecommendation(project.id)
      showNotice(res.message || 'Module recommendations generated!')
      await loadAllData()
      setActiveTab('modules')
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'Module recommendation failed', true)
    } finally {
      setActionLoading(false)
    }
  }

  // Add Catalogue Module
  const handleAddCatalogueModule = async () => {
    if (!selectedCatalogueId) return
    try {
      const res = await api.addProjectModule(
        project.id,
        selectedCatalogueId,
        'Consultant added module to project scope'
      )
      showNotice(`Added ${res.module_name} to project modules`)
      setSelectedCatalogueId('')
      loadAllData()
    } catch (err) {
      showNotice('Failed to add module', true)
    }
  }

  // Approve Module
  const handleToggleModuleApprove = async (mappingId: string, current: boolean) => {
    try {
      await api.updateProjectModule(project.id, mappingId, { is_approved: !current })
      setModules((prev) =>
        prev.map((m) => (m.id === mappingId ? { ...m, is_approved: !current } : m))
      )
    } catch (err) {
      showNotice('Failed to update module approval', true)
    }
  }

  // Batch Approve All Modules
  const handleApproveAllModules = async () => {
    setActionLoading(true)
    try {
      await Promise.all(
        modules.map((m) =>
          m.is_approved ? Promise.resolve() : api.updateProjectModule(project.id, m.id, { is_approved: true })
        )
      )
      setModules((prev) => prev.map((m) => ({ ...m, is_approved: true })))
      showNotice('All recommended Zoho modules approved for SOW!')
    } catch (err) {
      showNotice('Failed to approve all modules', true)
    } finally {
      setActionLoading(false)
    }
  }

  // 4. Generate Scope Tasks
  const handleGenerateTasksForModule = async (moduleMappingId: string) => {
    setActionLoading(true)
    try {
      const res = await api.runTaskGeneration(project.id, moduleMappingId)
      showNotice(res.message || 'Scope tasks generated!')
      await loadAllData()
      setActiveTab('tasks')
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'Task generation failed', true)
    } finally {
      setActionLoading(false)
    }
  }

  // Batch Generate Tasks for All Approved Modules
  const handleGenerateTasksForAllModules = async () => {
    setActionLoading(true)
    try {
      const res = await api.runTaskGeneration(project.id, 'all')
      showNotice(res.message || 'Scope task generation started for all modules!')
      await loadAllData()
      setActiveTab('tasks')
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'Task generation failed', true)
    } finally {
      setActionLoading(false)
    }
  }

  // 5. Generate Automations
  const handleGenerateAutomations = async () => {
    setActionLoading(true)
    try {
      const res = await api.runAutomationGeneration(project.id)
      showNotice(res.message || 'Automation matrix generated!')
      await loadAllData()
      setActiveTab('automations')
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'Automation generation failed', true)
    } finally {
      setActionLoading(false)
    }
  }

  // 6. Generate Clarifications & Integrations
  const handleGenerateClarifications = async () => {
    setActionLoading(true)
    try {
      await api.runClarificationGeneration(project.id)
      await api.runIntegrationGeneration(project.id)
      showNotice('Clarification questions & integrations generated!')
      await loadAllData()
      setActiveTab('integrations')
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'Clarification generation failed', true)
    } finally {
      setActionLoading(false)
    }
  }

  // Answer Clarification
  const handleAnswerClarification = async (qId: string) => {
    const text = replyText[qId]
    if (!text) return
    try {
      await api.answerClarification(project.id, qId, text)
      showNotice('Client answer recorded!')
      setClarifications((prev) =>
        prev.map((c) => (c.id === qId ? { ...c, client_response: text, status: 'Answered' } : c))
      )
    } catch (err) {
      showNotice('Failed to save answer', true)
    }
  }

  // 7. Generate Assumptions / Exclusions
  const handleGenerateAssumptions = async () => {
    setActionLoading(true)
    try {
      await api.runAssumptionsGeneration(project.id)
      showNotice('Assumptions, exclusions & risks generated!')
      await loadAllData()
      setActiveTab('assumptions')
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'Generation failed', true)
    } finally {
      setActionLoading(false)
    }
  }

  // 8. Run Validation
  const handleRunValidation = async () => {
    setActionLoading(true)
    try {
      const res = await api.runValidation(project.id)
      setValidation(res)
      showNotice(`Scope coverage checked: Level is ${res.overall_level.toUpperCase()}`)
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'Validation failed', true)
    } finally {
      setActionLoading(false)
    }
  }

  // 9. Generate SOW DOCX
  const handleGenerateSOW = async () => {
    setActionLoading(true)
    try {
      const sow = await api.generateSow(project.id)
      showNotice(`SOW Document v${sow.version_number} generated successfully!`)
      await loadAllData()
      setActiveTab('sow')
    } catch (err: any) {
      showNotice(err.response?.data?.detail || 'SOW generation failed', true)
    } finally {
      setActionLoading(false)
    }
  }

  // Filtered requirements
  const filteredReqs = reqs.filter((r) => {
    const matchesCat = reqCategoryFilter === 'ALL' || r.category === reqCategoryFilter
    const matchesType =
      reqTypeFilter === 'ALL'
        ? true
        : reqTypeFilter === 'AI'
        ? r.is_ai_generated
        : !r.is_ai_generated
    return matchesCat && matchesType
  })

  const tabs: { id: TabType; label: string; icon: any; count?: number }[] = [
    { id: 'docs', label: '1. Documents', icon: FileText, count: docs.length },
    { id: 'requirements', label: '2. Requirements', icon: CheckSquare, count: reqs.length },
    { id: 'modules', label: '3. Zoho Modules', icon: Layers, count: modules.length },
    { id: 'tasks', label: '4. Scope Tasks', icon: ListTodo, count: tasks.length },
    { id: 'automations', label: '5. Automations', icon: Zap, count: automations.length },
    { id: 'integrations', label: '6. Clarifications', icon: HelpCircle, count: clarifications.length },
    { id: 'assumptions', label: '7. Assumptions & Risks', icon: ShieldAlert, count: assumptions.length + exclusions.length + risks.length },
    { id: 'validation', label: '8. Validation Audit', icon: CheckCircle2 },
    { id: 'sow', label: '9. SOW Generation', icon: Download, count: sowDocs.length },
  ]

  return (
    <div className="max-w-7xl mx-auto px-6 py-6 animate-fade-in">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <button
            onClick={onBack}
            className="inline-flex items-center space-x-1.5 text-xs text-slate-400 hover:text-white mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Dashboard</span>
          </button>
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold text-white tracking-tight">
              {project.client_name} — {project.project_name}
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800/80">
              {project.status}
            </span>
          </div>
          {project.description && (
            <p className="text-xs text-slate-400 mt-1 max-w-2xl">{project.description}</p>
          )}
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadAllData}
            title="Refresh workbench"
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:border-slate-700 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleGenerateSOW}
            disabled={actionLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition-all"
          >
            <Download className="w-4 h-4" />
            <span>Generate SOW (DOCX)</span>
          </button>
        </div>
      </div>

      {/* Global Notice Alert */}
      {alert && (
        <div
          className={`mt-4 p-3 rounded-xl text-xs flex items-center justify-between animate-fade-in ${
            alert.isError
              ? 'bg-red-950/60 border border-red-800 text-red-300'
              : 'bg-emerald-950/60 border border-emerald-800 text-emerald-300'
          }`}
        >
          <div className="flex items-center space-x-2">
            {alert.isError ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
            <span>{alert.text}</span>
          </div>
          <button onClick={() => setAlert(null)} className="text-slate-400 hover:text-white text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Stage Tab Navigation */}
      <div className="mt-6 flex space-x-1.5 overflow-x-auto pb-2 scrollbar-none border-b border-slate-800">
        {tabs.map((tab) => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/25'
                  : 'text-slate-400 hover:text-white hover:bg-slate-900'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
              {typeof tab.count === 'number' && (
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
                    isActive ? 'bg-indigo-800 text-indigo-100' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* TAB CONTENT AREAS */}
      <div className="mt-6">
        {/* TAB 1: DOCUMENTS */}
        {activeTab === 'docs' && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-6">
              <div>
                <h3 className="text-sm font-semibold text-white">Upload Client Requirements</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-lg">
                  Upload project requirement documents in DOCX, PDF, TXT, or Excel format. ScopePilot AI will extract section hierarchies and business statements automatically.
                </p>
              </div>

              <div className="flex items-center space-x-3 flex-wrap gap-2">
                <button
                  onClick={handleLoadSampleRequirements}
                  disabled={actionLoading}
                  className="flex items-center space-x-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700 transition-all"
                >
                  <FileText className="w-4 h-4 text-indigo-400" />
                  <span>Load Sample Specification</span>
                </button>

                <label className="flex items-center space-x-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-xl shadow-lg shadow-indigo-600/25 cursor-pointer transition-all">
                  <Upload className="w-4 h-4" />
                  <span>Upload Document (.docx, .pdf, .txt, .xlsx)</span>
                  <input
                    type="file"
                    accept=".docx,.pdf,.txt,.xlsx"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                </label>
              </div>
            </div>

            {/* Document List */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Uploaded Documents ({docs.length})
                </h4>
                {docs.length > 0 && (
                  <button
                    onClick={handleRunRequirementsAnalysis}
                    disabled={actionLoading}
                    className="flex items-center space-x-1.5 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg shadow-md transition-all"
                  >
                    <CheckSquare className="w-3.5 h-3.5" />
                    <span>Run AI Requirement Analysis</span>
                  </button>
                )}
              </div>

              {docs.length === 0 ? (
                <div className="p-8 text-center rounded-2xl bg-slate-900/30 border border-dashed border-slate-800 text-xs text-slate-400">
                  No documents uploaded yet. Upload a requirement document above or click "Run AI Requirement Analysis" if you have sample text.
                </div>
              ) : (
                docs.map((d) => (
                  <div
                    key={d.id}
                    className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-9 h-9 rounded-lg bg-indigo-950 flex items-center justify-center text-indigo-400 border border-indigo-800/40 font-mono text-xs uppercase font-bold">
                        {d.file_format}
                      </div>
                      <div>
                        <span className="font-semibold text-sm text-white block">
                          {d.original_filename}
                        </span>
                        <span className="text-[11px] text-slate-400 flex items-center space-x-2">
                          <span>{(d.file_size_bytes / 1024).toFixed(1)} KB</span>
                          <span>•</span>
                          <span>{d.page_count ? `${d.page_count} pages` : 'Plain text'}</span>
                          <span>•</span>
                          <span className="text-emerald-400 capitalize">{d.status}</span>
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleViewSections(d.id)}
                        className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5 text-slate-400" />
                        <span>View Sections</span>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Extracted Sections Drawer/Modal */}
            {selectedDocId && (
              <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 mt-6 animate-fade-in">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
                  <h4 className="text-sm font-semibold text-white">Extracted Sections ({sections.length})</h4>
                  <button
                    onClick={() => setSelectedDocId(null)}
                    className="text-xs text-slate-400 hover:text-white"
                  >
                    Close
                  </button>
                </div>
                <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
                  {sections.map((s, idx) => (
                    <div key={s.id || idx} className="p-3 rounded-lg bg-slate-900 border border-slate-800/80">
                      <span className="text-xs font-bold text-indigo-400 block mb-1">
                        {s.heading || `Section ${idx + 1}`}
                      </span>
                      <p className="text-xs text-slate-300 whitespace-pre-line leading-relaxed font-mono">
                        {s.content}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: REQUIREMENTS */}
        {activeTab === 'requirements' && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pb-2">
              <div className="flex items-center space-x-2 overflow-x-auto w-full sm:w-auto">
                {['ALL', 'CONFIRMED', 'AI'].map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setReqTypeFilter(tf)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold ${
                      reqTypeFilter === tf
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                    }`}
                  >
                    {tf === 'ALL' ? 'All Requirements' : tf === 'CONFIRMED' ? 'Confirmed from Source' : 'AI Inferred'}
                  </button>
                ))}
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={handleRecommendModules}
                  disabled={actionLoading}
                  className="flex items-center space-x-1.5 px-3.5 py-1.5 bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium rounded-xl shadow-md transition-all"
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>Recommend Zoho Modules →</span>
                </button>
              </div>
            </div>

            {filteredReqs.length === 0 ? (
              <div className="p-12 text-center rounded-2xl bg-slate-900/30 border border-dashed border-slate-800">
                <CheckSquare className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-xs text-slate-400">
                  No requirements extracted yet. Click "Run AI Requirement Analysis" on the Documents tab to analyze requirements.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-3.5">
                {filteredReqs.map((r) => (
                  <div
                    key={r.id}
                    className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-xs font-bold text-indigo-400">
                            {r.req_id}
                          </span>
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                              r.is_ai_generated ? 'badge-ai' : 'badge-source'
                            }`}
                          >
                            {r.is_ai_generated ? 'AI Recommendation' : 'Confirmed from Source'}
                          </span>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                            {r.category}
                          </span>
                          {r.suggested_zoho_module && (
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                              {r.suggested_zoho_module}
                            </span>
                          )}
                        </div>

                        <h4 className="text-sm font-semibold text-white mt-1">{r.title}</h4>
                        <p className="text-xs text-slate-300 leading-relaxed">{r.description}</p>

                        {r.supporting_excerpt && (
                          <div className="mt-2 p-2 rounded-lg bg-slate-950/80 border border-slate-800/80 text-[11px] text-slate-400 font-mono">
                            <span className="text-slate-500 font-sans block text-[10px] font-semibold uppercase">
                              Source Attribution:
                            </span>
                            "{r.supporting_excerpt}"
                          </div>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex flex-col items-end space-y-1.5 shrink-0">
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                            r.review_status === 'Approved by Consultant'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                              : r.review_status === 'Rejected'
                              ? 'bg-red-950 text-red-400 border border-red-800/60'
                              : 'bg-amber-950 text-amber-400 border border-amber-800/60'
                          }`}
                        >
                          {r.review_status}
                        </span>

                        <div className="flex items-center space-x-1 mt-1">
                          <button
                            onClick={() => handleRequirementStatus(r.id, 'Approved by Consultant')}
                            title="Approve Requirement"
                            className="p-1 rounded bg-emerald-950/80 hover:bg-emerald-800 text-emerald-300 border border-emerald-800/50 transition-colors"
                          >
                            <Check className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleRequirementStatus(r.id, 'Needs Review')}
                            title="Mark Needs Review"
                            className="p-1 rounded bg-amber-950/80 hover:bg-amber-800 text-amber-300 border border-amber-800/50 transition-colors"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: ZOHO MODULES */}
        {activeTab === 'modules' && (
          <div className="space-y-6">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="text-sm font-semibold text-white">Proposed Zoho Module Architecture</h3>
                <p className="text-xs text-slate-400">
                  Recommended applications justified by client requirements. Add or approve modules to drive task generation.
                </p>
              </div>

              <div className="flex items-center space-x-2">
                {modules.length > 0 && (
                  <button
                    onClick={handleApproveAllModules}
                    disabled={actionLoading}
                    className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow transition-all"
                  >
                    Approve All for SOW
                  </button>
                )}
                <select
                  value={selectedCatalogueId}
                  onChange={(e) => setSelectedCatalogueId(e.target.value)}
                  className="px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white"
                >
                  <option value="">Add Module from Catalogue...</option>
                  {catalogue.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.display_name} ({c.category})
                    </option>
                  ))}
                </select>
                <button
                  onClick={handleAddCatalogueModule}
                  disabled={!selectedCatalogueId}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg"
                >
                  Add
                </button>
              </div>
            </div>

            {modules.length === 0 ? (
              <div className="p-12 text-center rounded-2xl bg-slate-900/30 border border-dashed border-slate-800">
                <Layers className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                <p className="text-xs text-slate-400">
                  No modules mapped yet. Click "Recommend Zoho Modules" to let ScopePilot AI analyze requirements.
                </p>
                <button
                  onClick={handleRecommendModules}
                  className="mt-3 px-4 py-2 bg-indigo-600 text-white text-xs font-medium rounded-xl"
                >
                  Generate Recommendations
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {modules.map((m) => (
                  <div
                    key={m.id}
                    className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <h4 className="text-base font-bold text-white">{m.module_name}</h4>
                          {m.is_ai_recommended && (
                            <span className="badge-ai text-[10px] font-semibold px-2 py-0.5 rounded-full">
                              AI Recommended
                            </span>
                          )}
                        </div>

                        <button
                          onClick={() => handleToggleModuleApprove(m.id, m.is_approved)}
                          className={`text-xs px-2.5 py-1 rounded-lg font-medium border transition-colors ${
                            m.is_approved
                              ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                              : 'bg-slate-800 text-slate-400 border-slate-700 hover:text-white'
                          }`}
                        >
                          {m.is_approved ? 'Approved for SOW' : 'Click to Approve'}
                        </button>
                      </div>

                      <div className="mt-3 space-y-2 text-xs">
                        <div>
                          <span className="font-semibold text-slate-400">Business Purpose:</span>
                          <p className="text-slate-200 mt-0.5">{m.business_purpose}</p>
                        </div>
                        {m.recommendation_reason && (
                          <div>
                            <span className="font-semibold text-slate-400">Justification:</span>
                            <p className="text-slate-300 mt-0.5">{m.recommendation_reason}</p>
                          </div>
                        )}
                        {m.proposed_configuration && (
                          <div>
                            <span className="font-semibold text-slate-400">Configuration Scope:</span>
                            <p className="text-slate-400 mt-0.5 font-mono text-[11px]">
                              {m.proposed_configuration}
                            </p>
                          </div>
                        )}
                        {m.linked_requirement_ids?.length > 0 && (
                          <div className="flex items-center space-x-1.5 flex-wrap pt-1">
                            <span className="font-semibold text-slate-500 text-[10px]">Linked Reqs:</span>
                            {m.linked_requirement_ids.map((id) => (
                              <span key={id} className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-950 text-indigo-400 border border-slate-800">
                                {id}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="mt-5 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                      <span className="text-[11px] text-slate-500">
                        Status: <strong className="text-slate-300">{m.feasibility_status}</strong>
                      </span>
                      <button
                        onClick={() => handleGenerateTasksForModule(m.id)}
                        disabled={actionLoading}
                        className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center space-x-1"
                      >
                        <span>Generate Scope Tasks</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 4: SCOPE TASKS */}
        {activeTab === 'tasks' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Scope Tasks & Deliverables ({tasks.length})
              </h3>
              {modules.length > 0 && (
                <button
                  onClick={handleGenerateTasksForAllModules}
                  disabled={actionLoading}
                  className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-md transition-all"
                >
                  Generate Tasks for All Modules
                </button>
              )}
            </div>

            {tasks.length === 0 ? (
              <div className="p-12 text-center rounded-2xl bg-slate-900/30 border border-dashed border-slate-800 text-xs text-slate-400">
                No tasks generated yet. Approve modules on the Zoho Modules tab and click "Generate Scope Tasks".
              </div>
            ) : (
              <div className="space-y-3">
                {tasks.map((t) => (
                  <div key={t.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-xs font-bold text-indigo-400">
                            {t.task_id_label}
                          </span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                            {t.task_type}
                          </span>
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                              t.priority === 'High'
                                ? 'bg-red-950 text-red-300 border border-red-800/60'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            {t.priority} Priority
                          </span>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full ${
                              t.source === 'AI Recommendation' ? 'badge-ai' : 'badge-source'
                            }`}
                          >
                            {t.source}
                          </span>
                        </div>

                        <h4 className="text-sm font-semibold text-white mt-1.5">{t.name}</h4>
                        <p className="text-xs text-slate-300 mt-1 leading-relaxed">{t.description}</p>

                        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                          {t.deliverables && (
                            <div className="p-2 rounded bg-slate-950 border border-slate-800/80">
                              <span className="text-slate-500 font-semibold text-[10px] block uppercase">Deliverable:</span>
                              <span className="text-slate-300">{t.deliverables}</span>
                            </div>
                          )}
                          {t.acceptance_criteria && (
                            <div className="p-2 rounded bg-slate-950 border border-slate-800/80">
                              <span className="text-slate-500 font-semibold text-[10px] block uppercase">Acceptance Criteria:</span>
                              <span className="text-slate-300">{t.acceptance_criteria}</span>
                            </div>
                          )}
                        </div>

                        {t.subtasks && t.subtasks.length > 0 && (
                          <div className="mt-3 pt-2 border-t border-slate-800/80">
                            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                              Subtasks:
                            </span>
                            <div className="space-y-1">
                              {t.subtasks.map((st) => (
                                <div key={st.id} className="text-xs text-slate-400 flex items-center space-x-2">
                                  <span className="font-mono text-[10px] text-indigo-400">{st.task_id_label}</span>
                                  <span>{st.name}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 5: AUTOMATIONS */}
        {activeTab === 'automations' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-white">Business Automation Matrix</h3>
                <p className="text-xs text-slate-400">
                  Defines triggers, conditions, actions, SLAs, and escalation handling. Unconfirmed SLAs are highlighted.
                </p>
              </div>
              <button
                onClick={handleGenerateAutomations}
                disabled={actionLoading}
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-xl shadow-md transition-all"
              >
                Generate Automation Matrix
              </button>
            </div>

            {automations.length === 0 ? (
              <div className="p-12 text-center rounded-2xl bg-slate-900/30 border border-dashed border-slate-800 text-xs text-slate-400">
                No automations configured. Click "Generate Automation Matrix" to extract workflow opportunities from requirements.
              </div>
            ) : (
              <div className="space-y-3.5">
                {automations.map((a) => (
                  <div key={a.id} className="p-5 rounded-2xl bg-slate-900 border border-slate-800">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-xs font-bold text-amber-400">
                            {a.automation_id_label}
                          </span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                            {a.zoho_module || 'Zoho CRM'}
                          </span>
                          {a.source && (
                            <span className="badge-ai text-[10px] px-2 py-0.5 rounded-full">
                              {a.source}
                            </span>
                          )}
                        </div>
                        <h4 className="text-sm font-bold text-white mt-1.5">{a.name}</h4>
                        <p className="text-xs text-slate-400">{a.business_objective}</p>
                      </div>
                    </div>

                    <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                      <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800/80">
                        <span className="text-slate-500 font-semibold text-[10px] block uppercase">Trigger Event & Condition</span>
                        <span className="text-slate-200 block font-medium mt-0.5">{a.trigger_event}</span>
                        <span className="text-slate-400 text-[11px] font-mono mt-0.5 block">{a.trigger_conditions}</span>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800/80">
                        <span className="text-slate-500 font-semibold text-[10px] block uppercase">Action & Recipient</span>
                        <span className="text-slate-200 block font-medium mt-0.5">{a.action_performed}</span>
                        <span className="text-indigo-400 text-[11px] font-medium mt-0.5 block">Role: {a.recipient_role}</span>
                      </div>

                      <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800/80">
                        <span className="text-slate-500 font-semibold text-[10px] block uppercase">Execution SLA / Timing</span>
                        <span
                          className={`text-xs font-semibold block mt-0.5 ${
                            a.timing?.includes('PENDING_CONFIRMATION')
                              ? 'text-amber-400 font-mono'
                              : 'text-slate-200'
                          }`}
                        >
                          {a.timing || 'PENDING_CONFIRMATION'}
                        </span>
                        {a.exception_conditions && (
                          <span className="text-slate-500 text-[10px] mt-1 block">
                            Exception: {a.exception_conditions}
                          </span>
                        )}
                      </div>
                    </div>

                    {Array.isArray(a.pending_questions) && a.pending_questions.length > 0 && (
                      <div className="mt-3 p-2.5 rounded-xl bg-amber-950/30 border border-amber-800/40 text-xs">
                        <span className="text-amber-400 font-semibold text-[11px] block">
                          Client Clarification Needed:
                        </span>
                        <ul className="list-disc list-inside text-amber-200/80 text-[11px] mt-1 space-y-0.5">
                          {a.pending_questions.map((q, i) => (
                            <li key={i}>{typeof q === 'string' ? q : JSON.stringify(q)}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 6: CLARIFICATIONS & INTEGRATIONS */}
        {activeTab === 'integrations' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-semibold text-white">Client Clarification Questions</h3>
                <p className="text-xs text-slate-400">
                  Targeted questions required to eliminate SOW ambiguity. Answer questions here to incorporate into SOW.
                </p>
              </div>
              <button
                onClick={handleGenerateClarifications}
                disabled={actionLoading}
                className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-xl"
              >
                Generate Clarifications
              </button>
            </div>

            <div className="space-y-3.5">
              {clarifications.map((q) => (
                <div key={q.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-xs font-bold text-violet-400">
                          {q.question_id_label}
                        </span>
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-800 text-slate-300">
                          {q.category || 'General'}
                        </span>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                            q.status === 'Answered'
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/60'
                              : 'bg-amber-950 text-amber-400 border border-amber-800/60'
                          }`}
                        >
                          {q.status}
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-white mt-1.5">{q.question}</h4>
                      {q.why_it_matters && (
                        <p className="text-xs text-slate-400 mt-0.5">
                          <strong className="text-slate-300">Why it matters:</strong> {q.why_it_matters}
                        </p>
                      )}
                    </div>
                  </div>

                  {q.suggested_options && q.suggested_options.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {q.suggested_options.map((opt, i) => (
                        <button
                          key={i}
                          onClick={() => setReplyText({ ...replyText, [q.id]: opt })}
                          className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 hover:text-white hover:border-indigo-500 text-left"
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Reply Input */}
                  <div className="pt-2 flex items-center space-x-2">
                    <input
                      type="text"
                      value={replyText[q.id] || q.client_response || ''}
                      onChange={(e) => setReplyText({ ...replyText, [q.id]: e.target.value })}
                      placeholder="Record client reply or select an option above..."
                      className="flex-1 px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
                    />
                    <button
                      onClick={() => handleAnswerClarification(q.id)}
                      className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg"
                    >
                      Save Answer
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* INTEGRATIONS ARCHITECTURE SECTION */}
            <div className="pt-6 border-t border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">System Integrations Architecture ({integrations.length})</h3>
                  <p className="text-xs text-slate-400">
                    Cross-app data flows, external APIs, and IoT / hardware connector specifications.
                  </p>
                </div>
              </div>

              {integrations.length === 0 ? (
                <div className="p-8 text-center rounded-xl bg-slate-900 border border-slate-800 text-slate-500 text-xs">
                  No integrations generated yet. Click "Generate Clarifications" above to generate integrations.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {integrations.map((item) => (
                    <div key={item.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-indigo-400">
                          {item.integration_id_label || 'INT'}
                        </span>
                        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800/50">
                          {item.data_direction || 'one-way'}
                        </span>
                      </div>

                      <div className="flex items-center space-x-2 text-xs font-semibold text-white">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200">{item.source_app}</span>
                        <span className="text-slate-500">→</span>
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-200">{item.destination_app}</span>
                      </div>

                      <p className="text-xs text-slate-300 font-medium">
                        {item.business_purpose}
                      </p>

                      {item.data_exchanged && (
                        <div className="text-[11px] text-slate-400">
                          <strong className="text-slate-300">Data Exchanged:</strong> {item.data_exchanged}
                        </div>
                      )}

                      <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[10px] text-slate-500">
                        <span>Connector: {item.api_connector || 'Native Sync'}</span>
                        <span>{item.trigger_or_frequency || 'Real-time'}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 7: ASSUMPTIONS, EXCLUSIONS & RISKS */}
        {activeTab === 'assumptions' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div>
                <h3 className="text-sm font-semibold text-white">Project Assumptions, Exclusions & Risks</h3>
                <p className="text-xs text-slate-400">
                  Standard contractual protections and delivery constraints for the Statement of Work.
                </p>
              </div>
              <button
                onClick={handleGenerateAssumptions}
                disabled={actionLoading}
                className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-xl"
              >
                Regenerate Assumptions
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Assumptions */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                  Assumptions ({assumptions.length})
                </h4>
                <div className="space-y-2.5">
                  {assumptions.map((a, i) => (
                    <div key={i} className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs">
                      <p className="text-slate-200 leading-relaxed font-medium">{a.description}</p>
                      {a.impact && <p className="text-[11px] text-slate-400 mt-1">Impact: {a.impact}</p>}
                    </div>
                  ))}
                </div>
              </div>

              {/* Exclusions */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400">
                  Out of Scope Exclusions ({exclusions.length})
                </h4>
                <div className="space-y-2.5">
                  {exclusions.map((e, i) => (
                    <div key={i} className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs">
                      <p className="text-slate-200 leading-relaxed font-medium">{e.description}</p>
                      <span className="text-[10px] text-amber-400/80 font-mono block mt-1">
                        Type: {e.exclusion_type}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Risks */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-rose-400">
                  Delivery Risks & Mitigation ({risks.length})
                </h4>
                <div className="space-y-2.5">
                  {risks.map((r, i) => (
                    <div key={i} className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs">
                      <p className="text-slate-200 leading-relaxed font-medium">{r.description}</p>
                      {r.mitigation && (
                        <p className="text-[11px] text-emerald-400/90 mt-1">
                          Mitigation: {r.mitigation}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 8: VALIDATION AUDIT */}
        {activeTab === 'validation' && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-white">Full SOW Scope Coverage Audit</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-lg">
                  Audits requirements to ensure 100% scope coverage by tasks, automations, or integrations. Identifies unmapped items and pending clarifications before SOW generation.
                </p>
              </div>
              <button
                onClick={handleRunValidation}
                disabled={actionLoading}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-xl shadow-lg shadow-indigo-600/25 transition-all"
              >
                Run Validation Audit
              </button>
            </div>

            {validation && (
              <div className="space-y-5 animate-fade-in">
                {/* Score Banner */}
                <div
                  className={`p-5 rounded-2xl border flex items-center justify-between ${
                    validation.overall_level === 'pass'
                      ? 'bg-emerald-950/40 border-emerald-800/80 text-emerald-300'
                      : validation.overall_level === 'warning'
                      ? 'bg-amber-950/40 border-amber-800/80 text-amber-300'
                      : 'bg-red-950/40 border-red-800/80 text-red-300'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <CheckCircle2 className="w-8 h-8" />
                    <div>
                      <h4 className="text-base font-bold uppercase tracking-wider">
                        Validation Status: {validation.overall_level}
                      </h4>
                      <p className="text-xs text-slate-300">
                        {validation.unmapped_requirements === 0
                          ? 'All requirements are mapped to implementation tasks!'
                          : `${validation.unmapped_requirements} requirements need scope task mapping.`}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-2xl font-black block">
                      {validation.total_requirements > 0
                        ? `${Math.round(((validation.total_requirements - validation.unmapped_requirements) / validation.total_requirements) * 100)}%`
                        : '100%'}
                    </span>
                    <span className="text-[10px] uppercase font-bold text-slate-400">Coverage Score</span>
                  </div>
                </div>

                {/* Issues & Warnings List */}
                {validation.issues.length > 0 && (
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800">
                    <h4 className="text-xs font-semibold text-rose-400 uppercase tracking-wider mb-2">
                      Scope Gap Issues ({validation.issues.length})
                    </h4>
                    <ul className="space-y-1 text-xs text-slate-300">
                      {validation.issues.map((iss, i) => (
                        <li key={i} className="flex items-center space-x-2">
                          <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                          <span>{typeof iss === 'string' ? iss : ((iss as any)?.msg || JSON.stringify(iss))}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* TAB 9: SOW GENERATION */}
        {activeTab === 'sow' && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl bg-gradient-to-br from-indigo-950/50 via-slate-900 to-slate-950 border border-indigo-500/20 flex flex-col md:flex-row items-center justify-between gap-6">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 block mb-1">
                  Ready to Deliver
                </span>
                <h3 className="text-lg font-bold text-white">Generate Client Statement of Work (DOCX)</h3>
                <p className="text-xs text-slate-300 mt-1 max-w-xl">
                  Compiles confirmed requirements, approved Zoho modules, structured task schedules, automations matrix, exclusions, and assumptions into the master template.
                </p>
              </div>

              <button
                onClick={handleGenerateSOW}
                disabled={actionLoading}
                className="flex items-center space-x-2 px-6 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs rounded-xl shadow-xl shadow-indigo-600/30 transition-all hover:scale-105"
              >
                <Download className="w-4 h-4" />
                <span>{actionLoading ? 'Compiling Document...' : 'Generate SOW Document (DOCX)'}</span>
              </button>
            </div>

            {/* Generated Documents List */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Generated SOW Documents ({sowDocs.length})
              </h4>

              {sowDocs.length === 0 ? (
                <div className="p-12 text-center rounded-2xl bg-slate-900/30 border border-dashed border-slate-800 text-xs text-slate-400">
                  No SOW documents generated yet. Click "Generate SOW Document" above to produce your first draft.
                </div>
              ) : (
                sowDocs.map((doc) => (
                  <div
                    key={doc.id}
                    className="p-5 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-4">
                      <div className="w-10 h-10 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                        <FileText className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="text-sm font-bold text-white">
                            Statement of Work — Version {doc.version_number}.0
                          </span>
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/60 uppercase">
                            {doc.status}
                          </span>
                        </div>
                        <span className="text-xs text-slate-400 block mt-0.5">
                          Generated on {doc.generated_at ? new Date(doc.generated_at).toLocaleDateString() : 'Today'}
                        </span>
                        {doc.unresolved_placeholders?.length > 0 && (
                          <span className="text-[11px] text-amber-400 mt-1 block">
                            ⚠️ {doc.unresolved_placeholders.length} placeholders pending confirmation
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <a
                        href={api.getSowDownloadUrl(project.id, doc.id)}
                        download
                        className="flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl shadow-lg shadow-indigo-600/20 transition-all"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download .DOCX</span>
                      </a>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
