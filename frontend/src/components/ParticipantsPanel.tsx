import type { Participant } from '../store/meetingSlice'
import type { User } from '../store/authSlice'

interface ParticipantsPanelProps {
  localUser: User | null
  participants: Participant[]
}

function ParticipantRow({ name, role, micEnabled, cameraEnabled, isYou }: {
  name: string
  role: string
  micEnabled: boolean
  cameraEnabled: boolean
  isYou?: boolean
}) {
  const initials = name.split(' ').slice(0, 2).map(w => w[0] || '').join('').toUpperCase()

  return (
    <div className="flex items-center gap-3 px-4 py-3 rounded-xl glass-hover">
      <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
        style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: 'white' }}>
        {initials || '?'}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{name}{isYou && ' (you)'}</div>
        <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{role}</div>
      </div>
      <div className="flex items-center gap-1">
        <span className="text-sm" title={micEnabled ? 'Mic on' : 'Mic off'}>
          {micEnabled ? '🎤' : '🔇'}
        </span>
        <span className="text-sm" title={cameraEnabled ? 'Camera on' : 'Camera off'}>
          {cameraEnabled ? '🎥' : '📷'}
        </span>
      </div>
    </div>
  )
}

export default function ParticipantsPanel({ localUser, participants }: ParticipantsPanelProps) {
  const total = (localUser ? 1 : 0) + participants.length

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b font-semibold text-sm flex items-center justify-between"
        style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-2">
          <span>👥</span>
          <span>Participants</span>
        </div>
        <span className="badge-accent text-xs">{total}</span>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1">
        {/* Local user */}
        {localUser && (
          <ParticipantRow
            name={`${localUser.first_name} ${localUser.last_name}`}
            role="host"
            micEnabled={true}
            cameraEnabled={true}
            isYou
          />
        )}

        {/* Remote participants */}
        {participants
          .filter(p => p.user_id !== localUser?.id)
          .map(p => (
            <ParticipantRow
              key={p.user_id}
              name={p.first_name ? `${p.first_name} ${p.last_name}` : `User-${p.user_id.slice(0, 6)}`}
              role={p.role}
              micEnabled={p.mic_enabled}
              cameraEnabled={p.camera_enabled}
            />
          ))}

        {participants.length === 0 && !localUser && (
          <div className="text-center py-8 text-sm" style={{ color: 'var(--text-muted)' }}>
            <div className="text-3xl mb-3">👤</div>
            <p>No participants yet</p>
          </div>
        )}
      </div>
    </div>
  )
}
