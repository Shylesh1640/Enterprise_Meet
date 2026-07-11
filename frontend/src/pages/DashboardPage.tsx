import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { useQuery } from '@tanstack/react-query'
import { logout, fetchMe } from '../store/authSlice'
import type { AppDispatch, RootState } from '../store'
import api from '../lib/api'
import { isAuthenticated } from '../lib/auth'

interface Meeting {
  id: string
  title: string
  meeting_code: string
  status: string
  meeting_type: string
  created_at: string
  host_id: string
}

export default function DashboardPage() {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const user = useSelector((s: RootState) => s.auth.user)

  const [joinCode, setJoinCode] = useState('')
  const [newTitle, setNewTitle] = useState('')
  const [creatingMeeting, setCreatingMeeting] = useState(false)
  const [createError, setCreateError] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)

  useEffect(() => {
    if (!user) dispatch(fetchMe())
  }, [])

  const { data: meetingsData, refetch } = useQuery({
    queryKey: ['meetings'],
    queryFn: async () => {
      const { data } = await api.get('/meetings?page=1&page_size=10')
      return data.data?.items as Meeting[] ?? []
    },
    enabled: isAuthenticated(),
    retry: false,
  })

  const handleCreateMeeting = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newTitle.trim()) return
    setCreatingMeeting(true)
    setCreateError('')
    try {
      const { data } = await api.post('/meetings', {
        title: newTitle.trim(),
        meeting_type: 'instant',
      })
      const meeting = data.data
      navigate(`/room/${meeting.meeting_code}`)
    } catch {
      setCreateError('Failed to create meeting. Please try again.')
    } finally {
      setCreatingMeeting(false)
    }
  }

  const handleInstantMeeting = async () => {
    setCreatingMeeting(true)
    try {
      const { data } = await api.post('/meetings', {
        title: `${user?.first_name || 'My'}'s Meeting`,
        meeting_type: 'instant',
      })
      navigate(`/room/${data.data.meeting_code}`)
    } catch {
      setCreateError('Failed to start meeting.')
      setCreatingMeeting(false)
    }
  }

  const handleJoin = (e: React.FormEvent) => {
    e.preventDefault()
    const code = joinCode.trim().toUpperCase()
    if (code) navigate(`/room/${code}`)
  }

  const handleLogout = async () => {
    await dispatch(logout())
    navigate('/login', { replace: true })
  }

  const statusColor = (status: string) =>
    status === 'active' ? '#10b981' : status === 'ended' ? '#9898b8' : '#6366f1'

  const initials = user ? `${user.first_name[0]}${user.last_name[0]}`.toUpperCase() : '?'

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-primary)' }}>
      {/* Header */}
      <header className="sticky top-0 z-40 flex items-center justify-between px-6 py-4 border-b"
        style={{ background: 'rgba(10,10,15,0.8)', backdropFilter: 'blur(20px)', borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}>
            <span className="text-white text-sm font-bold">M</span>
          </div>
          <span className="text-lg font-bold gradient-text">EnterpriseMeet</span>
        </div>

        <div className="flex items-center gap-3">
          {user && (
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <div className="text-sm font-semibold">{user.first_name} {user.last_name}</div>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{user.email}</div>
              </div>
              <div className="w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm"
                style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: 'white' }}>
                {initials}
              </div>
            </div>
          )}
          <button onClick={handleLogout} className="btn-secondary btn text-sm">Sign out</button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10">
        {/* Hero Actions */}
        <div className="mb-10 animate-fade-in">
          <h1 className="text-3xl font-bold mb-2">
            Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 18 ? 'afternoon' : 'evening'},{' '}
            <span className="gradient-text">{user?.first_name || 'there'} 👋</span>
          </h1>
          <p className="text-sm mb-8" style={{ color: 'var(--text-secondary)' }}>
            Ready to connect with your team?
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Start Instant Meeting */}
            <div className="glass p-6 flex flex-col gap-4" style={{ borderColor: 'rgba(99,102,241,0.3)' }}>
              <div>
                <div className="text-3xl mb-2">🚀</div>
                <h2 className="font-bold text-lg">Start a new meeting</h2>
                <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                  Create an instant room and share the link
                </p>
              </div>
              <div className="flex gap-2">
                <button onClick={handleInstantMeeting}
                  className="btn-primary btn flex-1"
                  disabled={creatingMeeting}>
                  {creatingMeeting ? '⏳ Starting...' : 'Start instantly'}
                </button>
                <button onClick={() => setShowCreateModal(true)}
                  className="btn-secondary btn">
                  🗓️ Schedule
                </button>
              </div>
            </div>

            {/* Join Meeting */}
            <div className="glass p-6 flex flex-col gap-4">
              <div>
                <div className="text-3xl mb-2">🔗</div>
                <h2 className="font-bold text-lg">Join a meeting</h2>
                <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                  Enter a meeting code to join
                </p>
              </div>
              <form onSubmit={handleJoin} className="flex gap-2">
                <input
                  type="text"
                  className="input flex-1"
                  placeholder="Enter meeting code..."
                  value={joinCode}
                  onChange={e => setJoinCode(e.target.value)}
                />
                <button type="submit" className="btn-primary btn" disabled={!joinCode.trim()}>
                  Join →
                </button>
              </form>
            </div>
          </div>

          {createError && (
            <div className="mt-4 px-4 py-3 rounded-xl text-sm"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#fca5a5' }}>
              {createError}
            </div>
          )}
        </div>

        {/* Recent Meetings */}
        <div className="animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-xl">Your meetings</h2>
            <button onClick={() => refetch()} className="btn-ghost btn text-sm">↻ Refresh</button>
          </div>

          {!meetingsData?.length ? (
            <div className="glass p-12 text-center">
              <div className="text-5xl mb-4">📅</div>
              <h3 className="font-semibold text-lg mb-2">No meetings yet</h3>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Start your first meeting to see it listed here.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {meetingsData.map(m => (
                <div key={m.id} className="glass glass-hover flex items-center justify-between p-4 cursor-pointer"
                  onClick={() => navigate(`/room/${m.meeting_code}`)}>
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg"
                      style={{ background: 'var(--bg-hover)' }}>
                      {m.meeting_type === 'scheduled' ? '📅' : '⚡'}
                    </div>
                    <div>
                      <div className="font-semibold text-sm">{m.title}</div>
                      <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        Code: {m.meeting_code} · {new Date(m.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="badge text-xs font-medium px-2.5 py-0.5 rounded-full"
                      style={{
                        background: `${statusColor(m.status)}22`,
                        color: statusColor(m.status),
                        border: `1px solid ${statusColor(m.status)}44`,
                      }}>
                      {m.status}
                    </span>
                    <button
                      onClick={e => { e.stopPropagation(); navigate(`/room/${m.meeting_code}`) }}
                      className="btn-secondary btn text-xs py-1.5">
                      {m.status === 'active' ? 'Join →' : 'Rejoin →'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Schedule Meeting Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}>
          <div className="glass w-full max-w-md p-6 animate-fade-in">
            <h2 className="text-xl font-bold mb-6">Schedule a meeting</h2>
            <form onSubmit={handleCreateMeeting} className="space-y-4">
              <div>
                <label className="label">Meeting title</label>
                <input type="text" className="input" placeholder="Weekly Team Sync"
                  value={newTitle}
                  onChange={e => setNewTitle(e.target.value)}
                  required autoFocus />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="submit" className="btn-primary btn flex-1" disabled={creatingMeeting}>
                  {creatingMeeting ? '⏳ Creating...' : 'Create meeting'}
                </button>
                <button type="button" className="btn-secondary btn"
                  onClick={() => { setShowCreateModal(false); setNewTitle('') }}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
