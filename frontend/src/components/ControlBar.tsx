interface ControlBarProps {
  micEnabled: boolean
  cameraEnabled: boolean
  screenSharing: boolean
  panelOpen: 'chat' | 'participants' | null
  onToggleMic: () => void
  onToggleCamera: () => void
  onToggleScreenShare: () => Promise<void> | void
  onToggleChat: () => void
  onToggleParticipants: () => void
  onCopyInvite: () => void
  inviteCopied: boolean
  onLeave: () => void
}

export default function ControlBar({
  micEnabled, cameraEnabled, screenSharing, panelOpen,
  onToggleMic, onToggleCamera, onToggleScreenShare,
  onToggleChat, onToggleParticipants, onCopyInvite, inviteCopied, onLeave,
}: ControlBarProps) {
  return (
    <div className="shrink-0 flex items-center justify-center gap-3 px-6 py-4 border-t"
      style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
      {/* Mic */}
      <button
        onClick={onToggleMic}
        className={`btn-icon w-12 h-12 text-xl ${micEnabled ? '' : 'btn-icon-danger'}`}
        title={micEnabled ? 'Mute microphone' : 'Unmute microphone'}>
        {micEnabled ? '🎤' : '🔇'}
      </button>

      {/* Camera */}
      <button
        onClick={onToggleCamera}
        className={`btn-icon w-12 h-12 text-xl ${cameraEnabled ? '' : 'btn-icon-danger'}`}
        title={cameraEnabled ? 'Turn off camera' : 'Turn on camera'}>
        {cameraEnabled ? '🎥' : '📷'}
      </button>

      {/* Screen share */}
      <button
        onClick={() => void onToggleScreenShare()}
        className={`btn-icon w-12 h-12 text-xl ${screenSharing ? 'btn-icon-active' : ''}`}
        title={screenSharing ? 'Stop sharing' : 'Share screen'}>
        🖥️
      </button>

      {/* Divider */}
      <div className="w-px h-8 mx-1" style={{ background: 'var(--border)' }} />

      {/* Chat */}
      <button
        onClick={onToggleChat}
        className={`btn-icon w-12 h-12 text-xl ${panelOpen === 'chat' ? 'btn-icon-active' : ''}`}
        title="Chat">
        💬
      </button>

      {/* Participants */}
      <button
        onClick={onToggleParticipants}
        className={`btn-icon w-12 h-12 text-xl ${panelOpen === 'participants' ? 'btn-icon-active' : ''}`}
        title="Participants">
        👥
      </button>

      {/* Divider */}
      <div className="w-px h-8 mx-1" style={{ background: 'var(--border)' }} />

      {/* Invite link */}
      <button
        onClick={onCopyInvite}
        className={`btn-icon h-12 px-3 text-sm ${inviteCopied ? 'btn-icon-active' : ''}`}
        title="Copy meeting invite link">
        {inviteCopied ? 'Copied!' : 'Copy link'}
      </button>

      {/* Leave */}
      <button
        onClick={onLeave}
        className="btn-danger btn px-6 h-12 text-base font-bold"
        title="Leave meeting">
        📞 Leave
      </button>
    </div>
  )
}
