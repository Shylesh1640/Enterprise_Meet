import { useState, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { login, clearError } from '../store/authSlice'
import type { AppDispatch, RootState } from '../store'
import { isAuthenticated } from '../lib/auth'

export default function LoginPage() {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const location = useLocation()
  const { loading, error } = useSelector((s: RootState) => s.auth)
  const returnTo = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/dashboard'

  const [form, setForm] = useState({ email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)

  useEffect(() => {
    if (isAuthenticated()) navigate(returnTo, { replace: true })
    return () => { dispatch(clearError()) }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const result = await dispatch(login(form))
    if (login.fulfilled.match(result)) {
      navigate(returnTo, { replace: true })
    }
  }

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--bg-primary)' }}>
      {/* Left Panel — Branding */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 p-12 relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #0d0d18 0%, #111130 100%)' }}>
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full"
            style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%)' }} />
        </div>
        <div className="relative flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}>
            <span className="text-white font-bold">M</span>
          </div>
          <span className="text-xl font-bold gradient-text">EnterpriseMeet</span>
        </div>
        <div className="relative">
          <h2 className="text-4xl font-extrabold mb-6 leading-tight">
            Connect with your<br />
            <span className="gradient-text">team instantly</span>
          </h2>
          <div className="space-y-4">
            {[
              '🔒 End-to-end encrypted video',
              '💬 Real-time chat & file sharing',
              '🖥️ Screen sharing & recording',
            ].map(item => (
              <div key={item} className="flex items-center gap-3 text-sm"
                style={{ color: 'var(--text-secondary)' }}>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
        <p className="relative text-xs" style={{ color: 'var(--text-muted)' }}>
          Self-hosted • Open Source • Enterprise-grade
        </p>
      </div>

      {/* Right Panel — Form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md animate-fade-in">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}>
              <span className="text-white font-bold">M</span>
            </div>
            <span className="text-xl font-bold gradient-text">EnterpriseMeet</span>
          </div>

          <h1 className="text-3xl font-bold mb-2">Welcome back</h1>
          <p className="mb-8 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Sign in to your account to continue
          </p>

          {error && (
            <div className="mb-5 px-4 py-3 rounded-xl text-sm flex items-center gap-2"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5' }}>
              <span>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label" htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                className="input"
                placeholder="you@company.com"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                required
                autoComplete="email"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="label mb-0" htmlFor="password">Password</label>
                <Link to="/forgot-password" className="text-xs hover:underline"
                  style={{ color: 'var(--accent)' }}>
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="input pr-12"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  required
                  autoComplete="current-password"
                />
                <button type="button"
                  onClick={() => setShowPassword(s => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-sm"
                  style={{ color: 'var(--text-muted)' }}>
                  {showPassword ? '🙈' : '👁️'}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn-primary btn w-full mt-2 py-3"
              disabled={loading}>
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in...
                </span>
              ) : 'Sign in →'}
            </button>
          </form>

          <div className="divider">or</div>

          <p className="text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold hover:underline"
              style={{ color: 'var(--accent)' }}>
              Create one free
            </Link>
          </p>

          {/* Demo credentials hint */}
          <div className="mt-6 p-4 rounded-xl text-xs"
            style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', color: 'var(--text-muted)' }}>
            <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>Demo:</span>{' '}
            Register a new account to get started instantly.
          </div>
        </div>
      </div>
    </div>
  )
}
