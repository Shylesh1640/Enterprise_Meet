import { useState, useRef, useEffect } from 'react'
import { useSelector } from 'react-redux'
import type { RootState } from '../store'

interface ChatPanelProps {
  onSendMessage: (message: string) => void
}

export default function ChatPanel({ onSendMessage }: ChatPanelProps) {
  const messages = useSelector((s: RootState) => s.meeting.messages)
  const user = useSelector((s: RootState) => s.auth.user)
  const [draft, setDraft] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault()
    const msg = draft.trim()
    if (!msg) return
    onSendMessage(msg)
    setDraft('')
  }

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch { return '' }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b font-semibold text-sm flex items-center gap-2"
        style={{ borderColor: 'var(--border)' }}>
        <span>💬</span>
        <span>In-meeting Chat</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.length === 0 ? (
          <div className="text-center py-8 text-sm" style={{ color: 'var(--text-muted)' }}>
            <div className="text-3xl mb-3">👋</div>
            <p>No messages yet.<br />Say hello to everyone!</p>
          </div>
        ) : (
          messages.map(msg => {
            const isOwn = msg.sender_id === user?.id
            return (
              <div key={msg.id} className={`flex flex-col gap-0.5 ${isOwn ? 'items-end' : 'items-start'}`}>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {isOwn ? 'You' : (msg.sender_name || `User-${msg.sender_id.slice(0, 4)}`)} · {formatTime(msg.created_at)}
                </div>
                <div className={`max-w-[85%] px-3 py-2 rounded-2xl text-sm break-words`}
                  style={{
                    background: isOwn ? 'linear-gradient(135deg, #6366f1, #4f46e5)' : 'var(--bg-hover)',
                    color: isOwn ? 'white' : 'var(--text-primary)',
                    borderRadius: isOwn ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  }}>
                  {msg.message}
                </div>
              </div>
            )
          })
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend}
        className="px-3 py-3 border-t flex gap-2"
        style={{ borderColor: 'var(--border)' }}>
        <input
          type="text"
          className="input flex-1 py-2 text-sm"
          placeholder="Send a message..."
          value={draft}
          onChange={e => setDraft(e.target.value)}
          maxLength={2000}
        />
        <button type="submit"
          className="btn-primary btn px-4 py-2 text-base"
          disabled={!draft.trim()}>
          ➤
        </button>
      </form>
    </div>
  )
}
