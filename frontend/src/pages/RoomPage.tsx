import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import type { AppDispatch, RootState } from '../store'
import {
  setMeeting, setConnected, setParticipants, addParticipant, removeParticipant,
  updateParticipant, addMessage, setMicEnabled, setCameraEnabled, setScreenSharing,
  setRecording, setPanelOpen, resetMeeting,
} from '../store/meetingSlice'
import { fetchMe } from '../store/authSlice'
import { MeetingWebSocket } from '../lib/ws'
import api from '../lib/api'
import ChatPanel from '../components/ChatPanel'
import ParticipantsPanel from '../components/ParticipantsPanel'
import VideoTile from '../components/VideoTile'
import ControlBar from '../components/ControlBar'

interface IceServer {
  urls: string[]
  username?: string
  credential?: string
}

export default function RoomPage() {
  const { code } = useParams<{ code: string }>()
  const navigate = useNavigate()
  const dispatch = useDispatch<AppDispatch>()
  const user = useSelector((s: RootState) => s.auth.user)
  const meeting = useSelector((s: RootState) => s.meeting)

  // Refs
  const wsRef = useRef<MeetingWebSocket | null>(null)
  const localStreamRef = useRef<MediaStream | null>(null)
  const localVideoRef = useRef<HTMLVideoElement>(null)
  const peerConnections = useRef<Map<string, RTCPeerConnection>>(new Map())
  const remoteStreams = useRef<Map<string, MediaStream>>(new Map())
  const iceServers = useRef<IceServer[]>([{ urls: ['stun:stun.l.google.com:19302'] }])

  // State
  const [connecting, setConnecting] = useState(true)
  const [error, setError] = useState('')
  const [inviteCopied, setInviteCopied] = useState(false)
  const [remoteVideoRefs] = useState<Map<string, React.RefObject<HTMLVideoElement | null>>>(new Map())

  // ── Init ─────────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!user) { dispatch(fetchMe()) }
    void initRoom()
    return () => { cleanup() }
  }, [code])

  const initRoom = async () => {
    try {
      // 1. Validate meeting
      const { data: meetingData } = await api.get(`/meetings/by-code/${code}`)
      const m = meetingData.data
      // Find meeting by code - need to join via code then fetch full meeting
      const joinRes = await api.post(`/meetings/${m.id}/join`, {})
      void joinRes

      dispatch(setMeeting({
        meetingId: m.id,
        meetingCode: m.meeting_code,
        title: m.title,
        hostId: m.host_id,
      }))

      // 2. Init local media
      await initLocalMedia()

      // 3. Connect WebSocket
      await connectWebSocket(m.id)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e.response?.data?.detail || 'Failed to join meeting.')
      setConnecting(false)
    }
  }

  const initLocalMedia = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      localStreamRef.current = stream
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream
      }
      dispatch(setMicEnabled(true))
      dispatch(setCameraEnabled(true))
    } catch {
      // Fallback: no media
      dispatch(setMicEnabled(false))
      dispatch(setCameraEnabled(false))
    }
  }

  const connectWebSocket = async (meetingId: string) => {
    const ws = new MeetingWebSocket(meetingId)
    wsRef.current = ws

    ws.on('meeting_joined', (data) => {
      const participants = (data.participants as Array<Record<string, unknown>>).map(p => ({
        user_id: p.user_id as string,
        first_name: '',
        last_name: '',
        avatar: null,
        role: p.role as string,
        mic_enabled: p.mic_enabled as boolean,
        camera_enabled: p.camera_enabled as boolean,
        screen_sharing: p.screen_sharing as boolean,
        hand_raised: p.hand_raised as boolean,
      }))
      dispatch(setParticipants(participants))
      if (data.turn_servers) {
        iceServers.current = data.turn_servers as IceServer[]
      }
      dispatch(setConnected(true))
      setConnecting(false)
    })

    ws.on('participant_joined', (data) => {
      dispatch(addParticipant({
        user_id: data.user_id as string,
        first_name: data.first_name as string,
        last_name: data.last_name as string,
        avatar: data.avatar as string | null,
        role: 'attendee',
        mic_enabled: false,
        camera_enabled: false,
        screen_sharing: false,
        hand_raised: false,
      }))
      // Initiate peer connection for new participant
      void initiateConnection(data.user_id as string)
    })

    ws.on('participant_left', (data) => {
      dispatch(removeParticipant(data.user_id as string))
      closePeer(data.user_id as string)
    })

    ws.on('mic_updated', (data) => {
      dispatch(updateParticipant({ user_id: data.user_id as string, mic_enabled: data.enabled as boolean }))
    })

    ws.on('camera_updated', (data) => {
      dispatch(updateParticipant({ user_id: data.user_id as string, camera_enabled: data.enabled as boolean }))
    })

    ws.on('message_received', (data) => {
      dispatch(addMessage({
        id: data.id as string,
        sender_id: data.sender_id as string,
        sender_name: '',
        message: data.message as string,
        created_at: data.created_at as string,
      }))
    })

    ws.on('recording_started', (data) => {
      dispatch(setRecording({ isRecording: true, recordingId: data.recording_id as string }))
    })

    ws.on('recording_stopped', () => {
      dispatch(setRecording({ isRecording: false, recordingId: null }))
    })

    // WebRTC signaling
    ws.on('offer', (data) => { void handleOffer(data) })
    ws.on('answer', (data) => { void handleAnswer(data) })
    ws.on('ice_candidate', (data) => { void handleIceCandidate(data) })

    await ws.connect()
  }

  // ── WebRTC ───────────────────────────────────────────────────────────────

  const createPeer = (targetId: string): RTCPeerConnection => {
    const pc = new RTCPeerConnection({ iceServers: iceServers.current })

    localStreamRef.current?.getTracks().forEach(track => {
      pc.addTrack(track, localStreamRef.current!)
    })

    pc.onicecandidate = (e) => {
      if (e.candidate) {
        wsRef.current?.send('ice_candidate', {
          target_id: targetId,
          candidate: e.candidate.candidate,
          sdpMid: e.candidate.sdpMid,
          sdpMLineIndex: e.candidate.sdpMLineIndex,
        })
      }
    }

    pc.ontrack = (e) => {
      const stream = e.streams[0] || new MediaStream([e.track])
      remoteStreams.current.set(targetId, stream)
      const ref = remoteVideoRefs.get(targetId)
      if (ref?.current) ref.current.srcObject = stream
    }

    peerConnections.current.set(targetId, pc)
    return pc
  }

  const initiateConnection = async (targetId: string) => {
    const pc = createPeer(targetId)
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    wsRef.current?.send('offer', { target_id: targetId, sdp: offer.sdp, type: 'offer' })
  }

  const handleOffer = async (data: Record<string, unknown>) => {
    const fromId = data.from as string
    const pc = createPeer(fromId)
    await pc.setRemoteDescription(new RTCSessionDescription({ type: 'offer', sdp: data.sdp as string }))
    const answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    wsRef.current?.send('answer', { target_id: fromId, sdp: answer.sdp, type: 'answer' })
  }

  const handleAnswer = async (data: Record<string, unknown>) => {
    const pc = peerConnections.current.get(data.from as string)
    if (pc) await pc.setRemoteDescription(new RTCSessionDescription({ type: 'answer', sdp: data.sdp as string }))
  }

  const handleIceCandidate = async (data: Record<string, unknown>) => {
    const pc = peerConnections.current.get(data.from as string)
    if (pc) {
      await pc.addIceCandidate(new RTCIceCandidate({
        candidate: data.candidate as string,
        sdpMid: data.sdpMid as string,
        sdpMLineIndex: data.sdpMLineIndex as number,
      }))
    }
  }

  const closePeer = (targetId: string) => {
    peerConnections.current.get(targetId)?.close()
    peerConnections.current.delete(targetId)
    remoteStreams.current.delete(targetId)
  }

  // ── Media Controls ───────────────────────────────────────────────────────

  const toggleMic = useCallback(() => {
    const enabled = !meeting.micEnabled
    localStreamRef.current?.getAudioTracks().forEach(t => { t.enabled = enabled })
    dispatch(setMicEnabled(enabled))
    wsRef.current?.send('toggle_mic', { enabled })
  }, [meeting.micEnabled])

  const toggleCamera = useCallback(() => {
    const enabled = !meeting.cameraEnabled
    localStreamRef.current?.getVideoTracks().forEach(t => { t.enabled = enabled })
    dispatch(setCameraEnabled(enabled))
    wsRef.current?.send('toggle_camera', { enabled })
  }, [meeting.cameraEnabled])

  const toggleScreenShare = useCallback(async () => {
    if (!meeting.screenSharing) {
      try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true })
        const screenTrack = screenStream.getVideoTracks()[0]
        peerConnections.current.forEach(pc => {
          const sender = pc.getSenders().find(s => s.track?.kind === 'video')
          sender?.replaceTrack(screenTrack)
        })
        dispatch(setScreenSharing(true))
        wsRef.current?.send('start_screen_share', {})
        screenTrack.onended = () => stopScreenShare()
      } catch { /* user cancelled */ }
    } else {
      stopScreenShare()
    }
  }, [meeting.screenSharing])

  const stopScreenShare = () => {
    const camTrack = localStreamRef.current?.getVideoTracks()[0]
    if (camTrack) {
      peerConnections.current.forEach(pc => {
        const sender = pc.getSenders().find(s => s.track?.kind === 'video')
        sender?.replaceTrack(camTrack)
      })
    }
    dispatch(setScreenSharing(false))
    wsRef.current?.send('stop_screen_share', {})
  }

  const leaveMeeting = useCallback(async () => {
    wsRef.current?.send('leave_meeting', {})
    cleanup()
    navigate('/dashboard', { replace: true })
  }, [])

  const sendMessage = useCallback((message: string) => {
    wsRef.current?.send('send_message', { message })
  }, [])

  const copyInviteLink = useCallback(async () => {
    if (!code) return

    const inviteLink = `${window.location.origin}/room/${encodeURIComponent(code)}`
    try {
      await navigator.clipboard.writeText(inviteLink)
      setInviteCopied(true)
      window.setTimeout(() => setInviteCopied(false), 2000)
    } catch {
      setError('Could not copy the invite link. Please copy the URL from your browser.')
    }
  }, [code])

  const cleanup = () => {
    localStreamRef.current?.getTracks().forEach(t => t.stop())
    peerConnections.current.forEach(pc => pc.close())
    peerConnections.current.clear()
    wsRef.current?.disconnect()
    dispatch(resetMeeting())
  }

  // ── Render ───────────────────────────────────────────────────────────────

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center"
        style={{ background: 'var(--bg-primary)' }}>
        <div className="glass p-10 text-center max-w-md">
          <div className="text-5xl mb-4">😕</div>
          <h2 className="text-xl font-bold mb-3">Couldn't join meeting</h2>
          <p className="text-sm mb-6" style={{ color: 'var(--text-secondary)' }}>{error}</p>
          <button className="btn-primary btn" onClick={() => navigate('/dashboard')}>
            Go to Dashboard
          </button>
        </div>
      </div>
    )
  }

  if (connecting) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6"
        style={{ background: 'var(--bg-primary)' }}>
        <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
        <div className="text-center">
          <h2 className="font-bold text-xl mb-2">Joining meeting...</h2>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            Code: <span className="font-mono font-bold" style={{ color: 'var(--accent)' }}>{code}</span>
          </p>
        </div>
      </div>
    )
  }

  const participants = meeting.participants
  const gridCols = participants.length <= 1 ? 'grid-cols-1' :
    participants.length <= 4 ? 'grid-cols-2' : 'grid-cols-3'

  return (
    <div className="h-screen flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b shrink-0"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #6366f1, #4f46e5)' }}>
            <span className="text-white text-xs font-bold">M</span>
          </div>
          <div>
            <div className="font-semibold text-sm">{meeting.title || 'Meeting'}</div>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {meeting.meetingCode} · {participants.length + 1} participant{participants.length !== 0 ? 's' : ''}
            </div>
          </div>
        </div>
        {meeting.isRecording && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full"
            style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}>
            <div className="w-2 h-2 rounded-full recording-dot" style={{ background: '#ef4444' }} />
            <span className="text-xs font-semibold" style={{ color: '#ef4444' }}>Recording</span>
          </div>
        )}
      </header>

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Video Grid */}
        <div className={`flex-1 p-4 overflow-auto grid ${gridCols} gap-3 content-start auto-rows-max`}>
          {/* Local tile */}
          <VideoTile
            key="local"
            label={`${user?.first_name || 'You'} (You)`}
            videoRef={localVideoRef}
            micEnabled={meeting.micEnabled}
            cameraEnabled={meeting.cameraEnabled}
            isLocal={true}
          />
          {/* Remote tiles */}
          {participants
            .filter(p => p.user_id !== user?.id)
            .map(p => {
              if (!remoteVideoRefs.has(p.user_id)) {
                remoteVideoRefs.set(p.user_id, { current: null })
              }
              return (
                <VideoTile
                  key={p.user_id}
                  label={p.first_name ? `${p.first_name} ${p.last_name}` : `User-${p.user_id.slice(0, 4)}`}
                  videoRef={remoteVideoRefs.get(p.user_id)!}
                  micEnabled={p.mic_enabled}
                  cameraEnabled={p.camera_enabled}
                  isLocal={false}
                />
              )
            })}
        </div>

        {/* Side Panel */}
        {meeting.panelOpen && (
          <div className="w-80 shrink-0 border-l flex flex-col animate-slide-right"
            style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
            {meeting.panelOpen === 'chat' ? (
              <ChatPanel onSendMessage={sendMessage} />
            ) : (
              <ParticipantsPanel
                localUser={user}
                participants={participants}
              />
            )}
          </div>
        )}
      </div>

      {/* Control Bar */}
      <ControlBar
        micEnabled={meeting.micEnabled}
        cameraEnabled={meeting.cameraEnabled}
        screenSharing={meeting.screenSharing}
        panelOpen={meeting.panelOpen}
        onToggleMic={toggleMic}
        onToggleCamera={toggleCamera}
        onToggleScreenShare={toggleScreenShare}
        onToggleChat={() => dispatch(setPanelOpen('chat'))}
        onToggleParticipants={() => dispatch(setPanelOpen('participants'))}
        onCopyInvite={() => { void copyInviteLink() }}
        inviteCopied={inviteCopied}
        onLeave={leaveMeeting}
      />
    </div>
  )
}
