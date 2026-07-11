import React from 'react'

interface VideoTileProps {
  label: string
  videoRef: React.RefObject<HTMLVideoElement | null>
  micEnabled: boolean
  cameraEnabled: boolean
  isLocal: boolean
  isActiveSpeaker?: boolean
}

export default function VideoTile({
  label,
  videoRef,
  micEnabled,
  cameraEnabled,
  isLocal,
  isActiveSpeaker,
}: VideoTileProps) {
  const initials = label
    .split(' ')
    .slice(0, 2)
    .map(w => w[0] || '')
    .join('')
    .toUpperCase()

  return (
    <div className="video-tile" style={{
      borderColor: isActiveSpeaker ? 'var(--accent)' : undefined,
      boxShadow: isActiveSpeaker ? '0 0 0 2px var(--accent)' : undefined,
    }}>
      {/* Video element */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted={isLocal}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          display: cameraEnabled ? 'block' : 'none',
          transform: isLocal ? 'scaleX(-1)' : undefined,
        }}
      />

      {/* Avatar when camera off */}
      {!cameraEnabled && (
        <div className="absolute inset-0 flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #1e1e2a, #16161f)' }}>
          <div className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-bold"
            style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: 'white' }}>
            {initials || '?'}
          </div>
        </div>
      )}

      {/* Bottom bar */}
      <div className="absolute bottom-0 inset-x-0 flex items-center justify-between px-3 py-2"
        style={{ background: 'linear-gradient(transparent, rgba(0,0,0,0.7))' }}>
        <span className="text-xs font-medium text-white truncate max-w-[120px]">{label}</span>
        <div className="flex items-center gap-1">
          {!micEnabled && (
            <div className="w-5 h-5 rounded flex items-center justify-center"
              style={{ background: 'rgba(239,68,68,0.8)' }}>
              <span style={{ fontSize: 10 }}>🔇</span>
            </div>
          )}
          {!cameraEnabled && (
            <div className="w-5 h-5 rounded flex items-center justify-center"
              style={{ background: 'rgba(239,68,68,0.8)' }}>
              <span style={{ fontSize: 10 }}>📷</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
