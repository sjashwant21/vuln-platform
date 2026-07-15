import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { AuthTokens, Organization, User, UserRole } from '@/types'
const ROLE_ORDER: UserRole[] = ['viewer', 'analyst', 'admin', 'owner']
interface AuthState {
  user: User | null; organization: Organization | null
  isLoading: boolean; isAuthenticated: boolean
  setAuth: (user: User, org: Organization, tokens: AuthTokens) => void
  setUser: (user: User) => void; logout: () => void
  hasRole: (r: UserRole) => boolean; canWrite: () => boolean
  isAdmin: () => boolean; isOwner: () => boolean
}
export const useAuthStore = create<AuthState>()(devtools((set, get) => ({
  user: null, organization: null, isLoading: true, isAuthenticated: false,
  setAuth: (user, organization, tokens) => {
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
    set({ user, organization, isAuthenticated: true, isLoading: false })
  },
  setUser: user => set({ user }),
  logout: () => {
    localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token')
    set({ user: null, organization: null, isAuthenticated: false, isLoading: false })
  },
  hasRole: r => { const role = get().user?.role; return role ? ROLE_ORDER.indexOf(role) >= ROLE_ORDER.indexOf(r) : false },
  canWrite: () => get().hasRole('analyst'),
  isAdmin:  () => get().hasRole('admin'),
  isOwner:  () => get().hasRole('owner'),
}), { name: 'auth-store' }))
