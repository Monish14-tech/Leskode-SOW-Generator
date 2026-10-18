import React, { useState } from 'react'
import { X, Lock, Mail, User, Building, Sparkles, AlertCircle } from 'lucide-react'
import { api, formatApiError } from '../api'
import type { User as UserType } from '../types'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (user: UserType) => void
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('demo@scopepilot.ai')
  const [password, setPassword] = useState('demo1234')
  const [fullName, setFullName] = useState('Senior Consultant')
  const [orgName, setOrgName] = useState('ScopePilot Implementation Studio')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      if (isRegister) {
        const res = await api.register({
          email,
          password,
          full_name: fullName,
          organization_name: orgName,
        })
        onSuccess(res.user)
      } else {
        const res = await api.login(email, password)
        onSuccess(res.user)
      }
      onClose()
    } catch (err: any) {
      setError(formatApiError(err, 'Authentication failed. Please check credentials.'))
    } finally {
      setLoading(false)
    }
  }

  const handleQuickDemoRegister = async () => {
    setLoading(true)
    setError(null)
    const randomSuffix = Math.floor(1000 + Math.random() * 9000)
    const demoEmail = `demo.${randomSuffix}@scopepilot.ai`
    try {
      const res = await api.register({
        email: demoEmail,
        password: 'password123',
        full_name: `Consultant ${randomSuffix}`,
        organization_name: `Zoho Delivery Team ${randomSuffix}`,
      })
      onSuccess(res.user)
      onClose()
    } catch (err: any) {
      setError(formatApiError(err, 'Demo login failed.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 relative overflow-hidden">
        {/* Glow accent */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <div className="w-7 h-7 rounded-lg bg-indigo-600/30 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-indigo-400" />
            </div>
            <h2 className="text-base font-semibold text-white">
              {isRegister ? 'Create ScopePilot Workspace' : 'Sign in to ScopePilot AI'}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-red-950/40 border border-red-800/60 flex items-center space-x-2 text-xs text-red-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          {isRegister && (
            <>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Full Name
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Alex Vance"
                    className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Workspace / Organization Name
                </label>
                <div className="relative">
                  <Building className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    required
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    placeholder="e.g. CloudSync Solutions"
                    className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="consultant@company.com"
                className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm rounded-xl shadow-lg shadow-indigo-600/30 transition-all"
          >
            {loading ? 'Processing...' : isRegister ? 'Create Account & Workspace' : 'Sign In'}
          </button>
        </form>

        <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
          <button
            type="button"
            onClick={() => setIsRegister(!isRegister)}
            className="hover:text-indigo-400 underline underline-offset-4 transition-colors"
          >
            {isRegister ? 'Already have an account? Sign in' : "Don't have an account? Register"}
          </button>

          <button
            type="button"
            onClick={handleQuickDemoRegister}
            className="text-xs px-2.5 py-1 rounded-lg bg-indigo-950/60 text-indigo-300 border border-indigo-800/60 hover:bg-indigo-900 transition-colors"
          >
            Instant 1-Click Demo
          </button>
        </div>
      </div>
    </div>
  )
}
