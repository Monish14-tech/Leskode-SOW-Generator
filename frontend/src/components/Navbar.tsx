import React from 'react'
import { Sparkles, FileText, User as UserIcon, LayoutTemplate, LogOut } from 'lucide-react'
import type { User, Project } from '../types'

interface NavbarProps {
  user: User | null
  activeProject: Project | null
  onOpenAuth: () => void
  onOpenTemplateManager: () => void
  onSelectProject: (p: Project | null) => void
  onLogout: () => void
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  activeProject,
  onOpenAuth,
  onOpenTemplateManager,
  onSelectProject,
  onLogout,
}) => {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand & Breadcrumb */}
        <div className="flex items-center space-x-4">
          <button
            onClick={() => onSelectProject(null)}
            className="flex items-center space-x-2.5 group text-left focus:outline-none"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="font-bold text-lg bg-gradient-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent">
                ScopePilot<span className="text-indigo-400">.AI</span>
              </span>
              <span className="block text-[10px] font-medium uppercase tracking-wider text-slate-400">
                Zoho Implementation Platform
              </span>
            </div>
          </button>

          {activeProject && (
            <div className="flex items-center space-x-2 text-sm">
              <span className="text-slate-600">/</span>
              <button
                onClick={() => onSelectProject(null)}
                className="text-slate-400 hover:text-white transition-colors"
              >
                Projects
              </button>
              <span className="text-slate-600">/</span>
              <span className="font-medium text-indigo-400 max-w-[220px] truncate">
                {activeProject.client_name} — {activeProject.project_name}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                {activeProject.status}
              </span>
            </div>
          )}
        </div>

        {/* Right Actions */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onOpenTemplateManager}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-900 border border-slate-800 hover:border-slate-700 transition-colors"
          >
            <LayoutTemplate className="w-3.5 h-3.5 text-indigo-400" />
            <span>Master Templates</span>
          </button>

          <div className="flex items-center space-x-2 pl-3 border-l border-slate-800">
            <button
              onClick={onOpenAuth}
              title="Click to sign in or switch workspace"
              className="flex items-center space-x-2 text-left hover:opacity-80 transition-opacity"
            >
              <div className="w-7 h-7 rounded-lg bg-indigo-600/25 border border-indigo-500/40 flex items-center justify-center text-xs font-bold text-indigo-300">
                {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'M'}
              </div>
              <div>
                <span className="block text-xs font-semibold text-slate-200">
                  {user?.full_name || 'Monish (Leskode)'}
                </span>
                <span className="block text-[10px] font-medium text-emerald-400">
                  Zoho Advanced Partner
                </span>
              </div>
            </button>
            <button
              onClick={onLogout}
              title="Reset session / Sign out"
              className="p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition-colors ml-1"
            >
              <LogOut className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}
