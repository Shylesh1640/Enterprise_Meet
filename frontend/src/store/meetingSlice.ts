import { createSlice } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'

export interface Participant {
  user_id: string
  first_name: string
  last_name: string
  avatar: string | null
  role: string
  mic_enabled: boolean
  camera_enabled: boolean
  screen_sharing: boolean
  hand_raised: boolean
  stream?: MediaStream
}

export interface ChatMessage {
  id: string
  sender_id: string
  sender_name: string
  message: string
  created_at: string
  edited?: boolean
  reply_to?: string | null
}

interface MeetingState {
  meetingId: string | null
  meetingCode: string | null
  title: string | null
  hostId: string | null
  participants: Participant[]
  messages: ChatMessage[]
  isConnected: boolean
  micEnabled: boolean
  cameraEnabled: boolean
  screenSharing: boolean
  handRaised: boolean
  isRecording: boolean
  recordingId: string | null
  activeSpeakerId: string | null
  panelOpen: 'chat' | 'participants' | null
}

const initialState: MeetingState = {
  meetingId: null,
  meetingCode: null,
  title: null,
  hostId: null,
  participants: [],
  messages: [],
  isConnected: false,
  micEnabled: false,
  cameraEnabled: false,
  screenSharing: false,
  handRaised: false,
  isRecording: false,
  recordingId: null,
  activeSpeakerId: null,
  panelOpen: null,
}

const meetingSlice = createSlice({
  name: 'meeting',
  initialState,
  reducers: {
    setMeeting(state, { payload }: PayloadAction<{
      meetingId: string; meetingCode: string; title: string; hostId: string
    }>) {
      state.meetingId = payload.meetingId
      state.meetingCode = payload.meetingCode
      state.title = payload.title
      state.hostId = payload.hostId
    },
    setConnected(state, { payload }: PayloadAction<boolean>) {
      state.isConnected = payload
    },
    setParticipants(state, { payload }: PayloadAction<Participant[]>) {
      state.participants = payload
    },
    addParticipant(state, { payload }: PayloadAction<Participant>) {
      if (!state.participants.find(p => p.user_id === payload.user_id)) {
        state.participants.push(payload)
      }
    },
    removeParticipant(state, { payload }: PayloadAction<string>) {
      state.participants = state.participants.filter(p => p.user_id !== payload)
    },
    updateParticipant(state, { payload }: PayloadAction<Partial<Participant> & { user_id: string }>) {
      const idx = state.participants.findIndex(p => p.user_id === payload.user_id)
      if (idx !== -1) Object.assign(state.participants[idx], payload)
    },
    addMessage(state, { payload }: PayloadAction<ChatMessage>) {
      state.messages.push(payload)
    },
    setMessages(state, { payload }: PayloadAction<ChatMessage[]>) {
      state.messages = payload
    },
    setMicEnabled(state, { payload }: PayloadAction<boolean>) {
      state.micEnabled = payload
    },
    setCameraEnabled(state, { payload }: PayloadAction<boolean>) {
      state.cameraEnabled = payload
    },
    setScreenSharing(state, { payload }: PayloadAction<boolean>) {
      state.screenSharing = payload
    },
    setHandRaised(state, { payload }: PayloadAction<boolean>) {
      state.handRaised = payload
    },
    setRecording(state, { payload }: PayloadAction<{ isRecording: boolean; recordingId: string | null }>) {
      state.isRecording = payload.isRecording
      state.recordingId = payload.recordingId
    },
    setActiveSpeaker(state, { payload }: PayloadAction<string | null>) {
      state.activeSpeakerId = payload
    },
    setPanelOpen(state, { payload }: PayloadAction<'chat' | 'participants' | null>) {
      state.panelOpen = state.panelOpen === payload ? null : payload
    },
    resetMeeting() {
      return initialState
    },
  },
})

export const {
  setMeeting, setConnected, setParticipants, addParticipant, removeParticipant,
  updateParticipant, addMessage, setMessages, setMicEnabled, setCameraEnabled,
  setScreenSharing, setHandRaised, setRecording, setActiveSpeaker, setPanelOpen,
  resetMeeting,
} = meetingSlice.actions
export default meetingSlice.reducer
