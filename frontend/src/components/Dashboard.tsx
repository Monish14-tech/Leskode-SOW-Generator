import React, { useState } from 'react'
import {
  FolderPlus, Search, Filter, Clock, ArrowRight,
  Layers, CheckCircle, FileText, HelpCircle, Sparkles, Building
} from 'lucide-react'
import type { Project } from '../types'

interface DashboardProps {
  projects: Project[]
  loading: boolean
  onSelectProject: (p: Project) => void
  onOpenNewProject: () => void
  onQuickDemoProject: () => void
}

export const Dashboard: React.FC<DashboardProps> = ({
  projects,
  loading,
  onSelectProject,
  onOpenNewProject,
  onQuickDemoProject,
}) => {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL')

  const filteredProjects = projects.filter((p) => {
    const matchesSearch =
      p.client_name.toLowerCase().includes(search.toLowerCase()) ||
      p.project_name.toLowerCase().includes(search.toLowerCase())
    const matchesStatus = statusFilter === 'ALL' || p.status === statusFilter
    return matchesSearch && matchesStatus
  })

  // Quick stats
  const totalCount = projects.length
  const sowDraftCount = projects.filter((p) => p.status.includes('SOW')).length
  const reviewingCount = projects.filter((p) => p.status.includes('Review')).length

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Hero / Header */}
      <div className="relative rounded-3xl p-8 mb-8 overflow-hidden border border-indigo-500/20 bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-slate-950 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl">
            <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 text-xs font-semibold mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Next-Gen Zoho Implementation Planning & SOW Engine</span>
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
              Transform Client Documents into Production Statements of Work
            </h1>
            <p className="mt-2 text-sm text-slate-300 leading-relaxed">
              Extract business requirements, map Zoho applications, organize module-wise scope & automation rules, identify missing information, and generate client-ready DOCX SOWs preserving master formatting.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={onOpenNewProject}
              className="flex items-center justify-center space-x-2 px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm shadow-xl shadow-indigo-600/30 transition-all hover:scale-[1.02]"
            >
              <FolderPlus className="w-4 h-4" />
              <span>Create Project</span>
            </button>
            <button
              onClick={onQuickDemoProject}
              className="flex items-center justify-center space-x-2 px-4 py-3 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-200 text-sm font-medium transition-all"
            >
              <Sparkles className="w-4 h-4 text-violet-400" />
              <span>Load Sample Zoho Project</span>
            </button>
          </div>
        </div>

        {/* Stats Row */}
        <div className="mt-8 pt-6 border-t border-slate-800/80 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Total Projects</span>
            <span className="block text-2xl font-bold text-white mt-1">{totalCount}</span>
          </div>
          <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">In Scope Review</span>
            <span className="block text-2xl font-bold text-amber-400 mt-1">{reviewingCount}</span>
          </div>
          <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">SOW Drafts</span>
            <span className="block text-2xl font-bold text-indigo-400 mt-1">{sowDraftCount}</span>
          </div>
          <div className="p-3.5 rounded-2xl bg-slate-900/60 border border-slate-800/80">
            <span className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Active Zoho Modules</span>
            <span className="block text-2xl font-bold text-emerald-400 mt-1">15+ Catalogue</span>
          </div>
        </div>
      </div>

      {/* Filters & Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by client or project name..."
            className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div className="flex items-center space-x-1.5 overflow-x-auto w-full sm:w-auto pb-2 sm:pb-0">
          {['ALL', 'Draft', 'Requirements Review', 'Scope Review', 'SOW Draft', 'Approved'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors whitespace-nowrap ${
                statusFilter === st
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Projects Grid */}
      {loading ? (
        <div className="py-20 text-center">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs text-slate-400">Loading client projects...</p>
        </div>
      ) : filteredProjects.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-dashed border-slate-800">
          <Building className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-white">No projects found</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
            {search || statusFilter !== 'ALL'
              ? 'Try adjusting your search terms or status filter.'
              : 'Create your first project or load the sample Zoho project to get started.'}
          </p>
          <div className="mt-5 flex items-center justify-center space-x-3">
            <button
              onClick={onOpenNewProject}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-xl transition-all"
            >
              Create New Project
            </button>
            <button
              onClick={onQuickDemoProject}
              className="px-4 py-2 bg-slate-800 text-slate-200 text-xs font-medium rounded-xl transition-all"
            >
              Load Demo Project
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredProjects.map((p) => (
            <div
              key={p.id}
              onClick={() => onSelectProject(p)}
              className="glass-card group p-5 rounded-2xl cursor-pointer transition-all hover:translate-y-[-2px] flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider">
                    {p.client_name}
                  </span>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                      p.status.includes('SOW')
                        ? 'bg-purple-950/60 text-purple-300 border-purple-800/60'
                        : p.status.includes('Review')
                        ? 'bg-amber-950/60 text-amber-300 border-amber-800/60'
                        : p.status === 'Approved'
                        ? 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                        : 'bg-slate-800 text-slate-300 border-slate-700'
                    }`}
                  >
                    {p.status}
                  </span>
                </div>

                <h3 className="text-base font-bold text-white group-hover:text-indigo-300 transition-colors">
                  {p.project_name}
                </h3>

                {p.description && (
                  <p className="text-xs text-slate-400 mt-2 line-clamp-2 leading-relaxed">
                    {p.description}
                  </p>
                )}
              </div>

              <div className="mt-5 pt-4 border-t border-slate-800/80">
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span className="flex items-center space-x-1 text-[11px]">
                    <Layers className="w-3.5 h-3.5 text-slate-500" />
                    <span>{p.primary_zoho_edition || 'Zoho One'}</span>
                  </span>

                  <span className="flex items-center space-x-1 text-indigo-400 group-hover:translate-x-1 transition-transform font-medium">
                    <span>Open Workbench</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
