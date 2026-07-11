import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { register, clearError } from '../store/authSlice'
import type { AppDispatch, RootState } from '../store'
import { isAuthenticated } from '../lib/auth'

export default function RegisterPage() {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const { loading, error } = useSelector((s: RootState) => s.auth)

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    confirm_password: '',
  })
  const [localError, setLocalError] = useState('')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (isAuthenticated()) navigate('/dashboard', { replace: true })
    return () => { dispatch(clearError()) }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError('')

    if (form.password !== form.confirm_password) {
      setLocalError('Passwords do not match')
      return
    }
    if (form.password.length < 8) {
      setLocalError('Password must be at least 8 characters')
      return
    }

    const result = await dispatch(register({
      first_name: form.first_name,
      last_name: form.last_name,
      email: form.email,
      password: form.password,
    }))

    if (register.fulfilled.match(result)) {
      setSuccess(true)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6"
        style={{ background: 'var(--bg-primary)' }}>
        <div className="max-w-md text-center glass p-12 animate-fade-in">
          <div className="text-6xl mb-6">📧</div>
          <h1 className="text-2xl font-bold mb-4">Check your email!</h1>
          <p className="mb-8" style={{ color: 'var(--text-secondary)' }}>
            We've sent a verification link to <strong>{form.email}</strong>.
            Please verify your email before signing in.
          </p>
          <Link to="/login" className="btn-primary btn">Go to Sign In →</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex" style={{ background: 'var(--bg-primary)' }}>
      {/* Left Panel */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 p-12 relative overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #0d0d18 0%, #111130 100%)' }}>
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full"
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
            Start meeting<br />
            <span className="gradient-text">in seconds</span>
          </h2>
          <div className="space-y-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <div>✓ Free forever for teams up to 100</div>
            <div>✓ No download required</div>
            <div>✓ Works in any browser</div>
          </div>
        </div>
        <p className="relative text-xs" style={{ color: 'var(--text-muted)' }}>
          Your data stays on your server
        </p>
      </div>

      {/* Right Panel */}
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

          <h1 className="text-3xl font-bold mb-2">Create an account</h1>
          <p className="mb-8 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Join EnterpriseMeet for free — no credit card needed
          </p>

          {(error || localError) && (
            <div className="mb-5 px-4 py-3 rounded-xl text-sm flex items-center gap-2"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5' }}>
              <span>⚠️</span>
              <span>{error || localError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label" htmlFor="first_name">First name</label>
                <input id="first_name" type="text" className="input" placeholder="Jane"
                  value={form.first_name}
                  onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))}
                  required />
              </div>
              <div>
                <label className="label" htmlFor="last_name">Last name</label>
                <input id="last_name" type="text" className="input" placeholder="Doe"
                  value={form.last_name}
                  onChange={e => setForm(f => ({ ...f, last_name: e.target.value }))}
                  required />
              </div>
            </div>

            <div>
              <label className="label" htmlFor="reg-email">Email address</label>
              <input id="reg-email" type="email" className="input" placeholder="you@company.com"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                required autoComplete="email" />
            </div>

            <div>
              <label className="label" htmlFor="reg-password">Password</label>
              <input id="reg-password" type="password" className="input" placeholder="Min. 8 characters"
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                required autoComplete="new-password" />
            </div>

            <div>
              <label className="label" htmlFor="confirm-password">Confirm password</label>
              <input id="confirm-password" type="password"
                className={`input ${form.confirm_password && form.password !== form.confirm_password ? 'input-error' : ''}`}
                placeholder="Repeat password"
                value={form.confirm_password}
                onChange={e => setForm(f => ({ ...f, confirm_password: e.target.value }))}
                required />
            </div>

            <button type="submit" className="btn-primary btn w-full py-3" disabled={loading}>
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Creating account...
                </span>
              ) : 'Create account →'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
            Already have an account?{' '}
            <Link to="/login" className="font-semibold hover:underline" style={{ color: 'var(--accent)' }}>
              Sign in
            </Link>
          </p>

          <p className="mt-4 text-center text-xs" style={{ color: 'var(--text-muted)' }}>
            By registering you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </div>
    </div>
  )
}
