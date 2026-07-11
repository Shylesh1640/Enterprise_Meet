/** WebSocket client for the meeting room real-time protocol */
import { getAccessToken } from './auth'

const BASE_WS = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
const WS_API_PREFIX = '/api/v1'

export type WSMessage = {
  event: string
  data: Record<string, unknown>
  ack_id?: string
}

type EventCallback = (data: Record<string, unknown>) => void

export class MeetingWebSocket {
  private ws: WebSocket | null = null
  private meetingId: string
  private handlers = new Map<string, EventCallback[]>()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private closed = false

  constructor(meetingId: string) {
    this.meetingId = meetingId
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const token = getAccessToken()
      const url = `${BASE_WS}${WS_API_PREFIX}/ws/meeting/${this.meetingId}?token=${encodeURIComponent(token ?? '')}`
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
        resolve()
      }

      this.ws.onmessage = (e) => {
        try {
          const msg: WSMessage = JSON.parse(e.data)
          const cbs = this.handlers.get(msg.event)
          if (cbs) cbs.forEach(cb => cb(msg.data))
          // Also call wildcard handlers
          const all = this.handlers.get('*')
          if (all) all.forEach(cb => cb({ event: msg.event, ...msg.data }))
        } catch {
          // ignore parse errors
        }
      }

      this.ws.onclose = (e) => {
        if (!this.closed && this.reconnectAttempts < this.maxReconnectAttempts) {
          const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000)
          this.reconnectAttempts++
          // A retry failure is handled by this connection's `onclose` handler.
          // Swallow the promise here so it does not surface as an unhandled rejection.
          this.reconnectTimer = setTimeout(() => { void this.connect().catch(() => {}) }, delay)
        }
        const cbs = this.handlers.get('_close')
        if (cbs) cbs.forEach(cb => cb({ code: e.code, reason: e.reason }))
      }

      this.ws.onerror = () => reject(new Error('WebSocket connection failed'))
    })
  }

  on(event: string, cb: EventCallback): () => void {
    if (!this.handlers.has(event)) this.handlers.set(event, [])
    this.handlers.get(event)!.push(cb)
    return () => {
      const arr = this.handlers.get(event)
      if (arr) this.handlers.set(event, arr.filter(h => h !== cb))
    }
  }

  send(event: string, data: Record<string, unknown> = {}, ackId?: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ event, data, ack_id: ackId }))
    }
  }

  disconnect(): void {
    this.closed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close(1000, 'User left')
  }
}
