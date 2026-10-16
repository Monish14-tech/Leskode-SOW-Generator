import React, { useState, useEffect } from 'react'
import { Navbar } from './components/Navbar'
import { Dashboard } from './components/Dashboard'
import { ProjectWorkspace } from './components/ProjectWorkspace'
import { NewProjectModal } from './components/NewProjectModal'
import { TemplateManagerModal } from './components/TemplateManagerModal'
import { api } from './api'
import type { User, Project } from './types'

const DEFAULT_USER: User = {
  id: 'default-consultant-id',
  email: 'consultant@scopepilot.ai',
  full_name: 'Monish (Leskode)',
  role: 'admin',
  organization_id: 'leskode-default',
  is_active: true,
}

export const App: React.FC = () => {
  const [user, setUser] = useState<User>(() => {
    const savedUser = localStorage.getItem('scopepilot_user')
    if (savedUser) {
      try {
        return JSON.parse(savedUser)
      } catch (e) {
        console.error(e)
      }
    }
    return DEFAULT_USER
  })

  const [projects, setProjects] = useState<Project[]>([])
  const [activeProject, setActiveProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(false)

  // Modals
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false)
  const [isTemplateOpen, setIsTemplateOpen] = useState(false)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    setLoading(true)
    try {
      const res = await api.getProjects()
      setProjects(res.projects || [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  // Create a realistic sample Zoho client project
  const handleQuickDemoProject = async () => {
    setLoading(true)
    try {
      const newProj = await api.createProject({
        client_name: 'Nexus Healthcare Systems',
        project_name: 'Zoho One Patient Intake & Billing Suite',
        primary_zoho_edition: 'Zoho One Enterprise',
        description: 'Multi-clinic enterprise requiring centralized patient lead intake, scheduling workflows, automated invoice processing, and ticket escalation.',
      })

      // Upload a realistic requirement document
      const sampleRequirementText = `NEXUS HEALTHCARE SYSTEMS — ZOHO IMPLEMENTATION REQUIREMENTS SPECIFICATION

1. Business Background & Overview:
Nexus Healthcare operates 8 regional outpatient diagnostic centers. Currently, patient registration, inquiries, appointment follow-ups, and diagnostic billing are managed across isolated spreadsheets and a legacy SQL billing system. Nexus is procuring Zoho One to centralize operations.

2. Lead & Patient Intake Requirements:
• The system must capture patient inquiry leads directly from the Nexus public website appointment form.
• All incoming web inquiries must be assigned to regional clinic intake coordinators within 15 minutes.
• If an inquiry has not received a response within 2 hours, automatically escalate to Clinic Operations Manager.
• Prevent duplicate patient accounts by validating National Health ID and mobile phone number.

3. Diagnostic Billing & Accounting Scope:
• Automatically generate tax invoices in Zoho Books upon completion of diagnostic test orders.
• Support multi-branch GST tax calculations and daily bank reconciliation.
• Send automated payment reminders via SMS and email 24 hours prior to scheduled appointment.

4. Customer Support & Inquiry Helpdesk:
• Patient service queries from email and live chat must create tickets in Zoho Desk.
• High priority SLA: Initial response within 1 hour; resolution within 4 hours.

5. Integration Requirements:
• Sync patient diagnostic test completion status from external Laboratory Information System (LIS) into Zoho CRM using Zoho Flow webhooks.
• Historical data migration: Migrate approximately 12,000 patient contact records from CSV export.`

      const blob = new Blob([sampleRequirementText], { type: 'text/plain' })
      const file = new File([blob], 'Nexus_Healthcare_Zoho_SOW_Requirements.txt', { type: 'text/plain' })

      await api.uploadDocument(newProj.id, file)

      // Refresh and open the project
      await loadProjects()
      setActiveProject(newProj)
    } catch (err) {
      console.error('Failed to create demo project:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      <Navbar
        user={user}
        activeProject={activeProject}
        onOpenAuth={() => {}}
        onOpenTemplateManager={() => setIsTemplateOpen(true)}
        onSelectProject={(p) => setActiveProject(p)}
        onLogout={() => {}}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeProject ? (
          <ProjectWorkspace
            project={activeProject}
            onBack={() => {
              setActiveProject(null)
              loadProjects()
            }}
            onProjectUpdated={(updated) => {
              setActiveProject(updated)
              loadProjects()
            }}
          />
        ) : (
          <Dashboard
            projects={projects}
            loading={loading}
            onSelectProject={(p) => setActiveProject(p)}
            onOpenNewProject={() => setIsNewProjectOpen(true)}
            onQuickDemoProject={handleQuickDemoProject}
          />
        )}
      </main>

      <NewProjectModal
        isOpen={isNewProjectOpen}
        onClose={() => setIsNewProjectOpen(false)}
        onCreated={(p) => {
          setActiveProject(p)
          loadProjects()
        }}
      />

      <TemplateManagerModal
        isOpen={isTemplateOpen}
        onClose={() => setIsTemplateOpen(false)}
      />
    </div>
  )
}
