import React, { useState } from 'react'
import { X, FolderPlus, Building, Briefcase, Layers, FileText, User } from 'lucide-react'
import { api, formatApiError } from '../api'
import type { Project } from '../types'

interface NewProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated: (project: Project) => void
}

export const NewProjectModal: React.FC<NewProjectModalProps> = ({
  isOpen,
  onClose,
  onCreated,
}) => {
  const [clientName, setClientName] = useState('')
  const [projectName, setProjectName] = useState('')
  const [preparedBy, setPreparedBy] = useState('Leskode Solutions Team')
  const [zohoEdition, setZohoEdition] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const proj = await api.createProject({
        client_name: clientName,
        project_name: projectName,
        prepared_by: preparedBy || 'Leskode Solutions Team',
        primary_zoho_edition: zohoEdition || undefined,
        description: description || undefined,
      })
      onCreated(proj)
      onClose()
      // reset form
      setClientName('')
      setProjectName('')
      setPreparedBy('Leskode Solutions Team')
      setZohoEdition('')
      setDescription('')
    } catch (err: any) {
      setError(formatApiError(err, 'Failed to create project.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 relative">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-indigo-600/30 flex items-center justify-center">
              <FolderPlus className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Create SOW Project</h2>
              <p className="text-xs text-slate-400">Initialize a new client requirements & implementation workspace</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-red-950/40 border border-red-800/60 text-xs text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Client / Company Name *
              </label>
              <div className="relative">
                <Building className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  required
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  placeholder="e.g. Acme Corporation"
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Project Name *
              </label>
              <div className="relative">
                <Briefcase className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  required
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="e.g. Zoho CRM & Books Rollout"
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Prepared By (Author / Consultant Name) *
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="text"
                required
                value={preparedBy}
                onChange={(e) => setPreparedBy(e.target.value)}
                placeholder="e.g. Monish / Leskode Solutions Team"
                className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              This name will be printed on the SOW cover page, document control metadata, and sign-off acceptance block.
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Primary Zoho Edition (Optional)
            </label>
            <div className="relative">
              <Layers className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <select
                value={zohoEdition}
                onChange={(e) => setZohoEdition(e.target.value)}
                className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="">None / To Be Determined</option>
                <option value="Zoho One Enterprise">Zoho One Enterprise</option>
                <option value="Zoho CRM Enterprise">Zoho CRM Enterprise</option>
                <option value="Zoho CRM Professional">Zoho CRM Professional</option>
                <option value="Zoho Finance Plus">Zoho Finance Plus</option>
                <option value="Zoho Books Ultimate">Zoho Books Ultimate</option>
                <option value="Zoho Creator Custom App">Zoho Creator Custom App</option>
                <option value="Zoho Workplace">Zoho Workplace</option>
              </select>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              Leave blank if client edition is not yet decided; ScopePilot AI will recommend appropriate editions.
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Project Context / Client Summary
            </label>
            <div className="relative">
              <textarea
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Briefly state client background, current challenges, and primary objectives..."
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500 resize-none"
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="py-2 px-5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition-all"
            >
              {loading ? 'Creating Project...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
