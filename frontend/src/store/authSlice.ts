import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import type { PayloadAction } from '@reduxjs/toolkit'
import api from '../lib/api'
import { setTokens, clearTokens } from '../lib/auth'

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  avatar: string | null
  status: string
  email_verified: boolean
}

interface AuthState {
  user: User | null
  loading: boolean
  error: string | null
}

const initialState: AuthState = {
  user: null,
  loading: false,
  error: null,
}

// ── Thunks ───────────────────────────────────────────────────────────────────

export const login = createAsyncThunk(
  'auth/login',
  async (payload: { email: string; password: string }, { rejectWithValue }) => {
    try {
      const { data } = await api.post('/auth/login', payload)
      const tokens = data.data
      setTokens(tokens.access_token, tokens.refresh_token)
      // Fetch user profile
      const me = await api.get('/auth/me')
      return me.data.data as User
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      return rejectWithValue(err.response?.data?.detail || 'Login failed')
    }
  }
)

export const register = createAsyncThunk(
  'auth/register',
  async (
    payload: { email: string; password: string; first_name: string; last_name: string },
    { rejectWithValue }
  ) => {
    try {
      const { data } = await api.post('/auth/register', payload)
      return data.data
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      return rejectWithValue(err.response?.data?.detail || 'Registration failed')
    }
  }
)

export const fetchMe = createAsyncThunk('auth/fetchMe', async (_, { rejectWithValue }) => {
  try {
    const { data } = await api.get('/auth/me')
    return data.data as User
  } catch {
    return rejectWithValue('Not authenticated')
  }
})

export const logout = createAsyncThunk('auth/logout', async () => {
  try {
    await api.post('/auth/logout')
  } finally {
    clearTokens()
  }
})

// ── Slice ────────────────────────────────────────────────────────────────────

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    clearError(state) {
      state.error = null
    },
    setUser(state, action: PayloadAction<User>) {
      state.user = action.payload
    },
  },
  extraReducers: builder => {
    // Login
    builder.addCase(login.pending, state => {
      state.loading = true
      state.error = null
    })
    builder.addCase(login.fulfilled, (state, { payload }) => {
      state.loading = false
      state.user = payload
    })
    builder.addCase(login.rejected, (state, { payload }) => {
      state.loading = false
      state.error = payload as string
    })

    // Register
    builder.addCase(register.pending, state => {
      state.loading = true
      state.error = null
    })
    builder.addCase(register.fulfilled, state => {
      state.loading = false
    })
    builder.addCase(register.rejected, (state, { payload }) => {
      state.loading = false
      state.error = payload as string
    })

    // FetchMe
    builder.addCase(fetchMe.fulfilled, (state, { payload }) => {
      state.user = payload
    })
    builder.addCase(fetchMe.rejected, state => {
      state.user = null
    })

    // Logout
    builder.addCase(logout.fulfilled, state => {
      state.user = null
      state.loading = false
      state.error = null
    })
  },
})

export const { clearError, setUser } = authSlice.actions
export default authSlice.reducer
