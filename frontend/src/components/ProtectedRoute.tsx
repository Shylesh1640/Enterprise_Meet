import { Navigate, useLocation } from 'react-router-dom'
import { useSelector } from 'react-redux'
import type { RootState } from '../store'
import { isAuthenticated } from '../lib/auth'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useSelector((s: RootState) => s.auth.user)
  const location = useLocation()
  if (!isAuthenticated() && !user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return <>{children}</>
}
