import React, { useState, useEffect } from 'react'
import { X, Upload, LayoutTemplate, CheckCircle2, AlertTriangle, FileCode } from 'lucide-react'
import { api } from '../api'
import type { SowTemplateItem } from '../types'

interface TemplateManagerModalProps {
  isOpen: boolean
  onClose: () => void
}

export const TemplateManagerModal: React.FC<TemplateManagerModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [templates, setTemplates] = useState<SowTemplateItem[]>([])
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<{ text: string; isError?: boolean } | null>(null)

  useEffect(() => {
    if (isOpen) {
      loadTemplates()
    }
  }, [isOpen])

  const loadTemplates = async () => {
    try {
      const res = await api.getTemplates()
      setTemplates(res.templates || [])
    } catch (e) {
      console.error(e)
    }
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    setLoading(true)
    setMsg(null)
    try {
      const res = await api.uploadTemplate(file, name || file.name.replace('.docx', ''), description)
      setMsg({ text: `Template uploaded! Detected ${res.placeholders?.length || 0} placeholders.` })
      setFile(null)
      setName('')
      setDescription('')
      loadTemplates()
    } catch (err: any) {
      setMsg({ text: err.response?.data?.detail || 'Upload failed.', isError: true })
    } finally {
      setLoading(false)
    }
  }

  const handleSetActive = async (versionId: string, templateName: string) => {
    setLoading(true)
    setMsg(null)
    try {
      await api.publishTemplateVersion(versionId)
      setMsg({ text: `"${templateName}" is now the active master template!` })
      await loadTemplates()
    } catch (err: any) {
      setMsg({ text: err.response?.data?.detail || 'Failed to activate template.', isError: true })
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 relative max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-violet-600/30 flex items-center justify-center">
              <LayoutTemplate className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Master SOW Templates</h2>
              <p className="text-xs text-slate-400">
                Upload any format or sample SOW. The generator replicates its exact logo, layout, and styling.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {msg && (
          <div
            className={`mt-4 p-3 rounded-xl text-xs flex items-center space-x-2 ${
              msg.isError
                ? 'bg-red-950/40 border border-red-800/60 text-red-300'
                : 'bg-emerald-950/40 border border-emerald-800/60 text-emerald-300'
            }`}
          >
            {msg.isError ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
            <span>{msg.text}</span>
          </div>
        )}

        {/* Upload Form */}
        <div className="mt-5 p-4 rounded-xl bg-slate-950 border border-slate-800">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1 flex items-center space-x-2">
            <Upload className="w-3.5 h-3.5 text-indigo-400" />
            <span>Upload Master SOW Template or Sample SOW</span>
          </h3>
          <p className="text-[11px] text-slate-400 mb-3">
            Upload any .docx SOW. Logos, margins, headers, footers, module tables, and typography are 100% cloned for new projects.
          </p>

          <form onSubmit={handleUpload} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">
                  Template Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Master Zoho SOW (Corporate Format)"
                  className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-400 mb-1">
                  Select .docx Template or Sample SOW
                </label>
                <input
                  type="file"
                  accept=".docx"
                  required
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-300 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-medium file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !file}
              className="py-1.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs rounded-lg transition-all"
            >
              {loading ? 'Uploading & Analyzing...' : 'Upload & Set as Active Master Template'}
            </button>
          </form>
        </div>

        {/* Existing Templates List */}
        <div className="mt-6">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">
            Existing Master Templates ({templates.length})
          </h3>

          {templates.length === 0 ? (
            <div className="p-6 text-center rounded-xl bg-slate-950/50 border border-slate-800/80">
              <FileCode className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400">
                No templates uploaded yet. The system will use its built-in official Leskode SOW engine until you upload a custom template.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {templates.map((tpl) => {
                const isActive = Boolean(tpl.active_version)
                const latestVersion = tpl.versions?.[0]
                const versionToActivate = tpl.active_version?.id || latestVersion?.id

                return (
                  <div
                    key={tpl.id}
                    className={`p-4 rounded-xl border flex items-start justify-between gap-3 ${
                      isActive
                        ? 'bg-slate-950 border-indigo-700/60 shadow-lg shadow-indigo-950/20'
                        : 'bg-slate-950/60 border-slate-800'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-sm text-white">{tpl.name}</span>
                        {isActive ? (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/60 flex items-center space-x-1">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Active Master</span>
                          </span>
                        ) : (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-900 text-slate-400 border border-slate-800">
                            Archived
                          </span>
                        )}
                      </div>

                      {tpl.active_version?.original_filename && (
                        <p className="text-[11px] font-mono text-slate-400">
                          File: {tpl.active_version.original_filename}
                        </p>
                      )}

                      {tpl.description && (
                        <p className="text-xs text-slate-400">{tpl.description}</p>
                      )}

                      {tpl.active_version?.detected_placeholders && tpl.active_version.detected_placeholders.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {tpl.active_version.detected_placeholders.slice(0, 8).map((ph) => (
                            <span
                              key={ph}
                              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-indigo-300"
                            >
                              {ph}
                            </span>
                          ))}
                          {tpl.active_version.detected_placeholders.length > 8 && (
                            <span className="text-[10px] text-slate-500 py-0.5">
                              +{tpl.active_version.detected_placeholders.length - 8} more
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {!isActive && versionToActivate && (
                      <button
                        onClick={() => handleSetActive(versionToActivate, tpl.name)}
                        disabled={loading}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white text-xs font-medium rounded-lg border border-slate-700 shrink-0 transition-colors"
                      >
                        Set as Active
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
