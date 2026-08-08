import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { AuthTokens, Organization, User, UserRole } from '@/types'
const ROLE_ORDER: UserRole[] = ['viewer', 'analyst', 'admin', 'owner']
interface AuthState {
  user: User | null; organization: Organization | null
  accessToken: string | null
  isLoading: boolean; isAuthenticated: boolean
  setAuth: (user: User, org: Organization, accessToken: string) => void
  setUser: (user: User) => void; logout: () => void
  setLoading: (loading: boolean) => void
  hasRole: (r: UserRole) => boolean; canWrite: () => boolean
  isAdmin: () => boolean; isOwner: () => boolean
}
export const useAuthStore = create<AuthState>()(devtools((set, get) => ({
  user: null, organization: null, accessToken: null, isLoading: true, isAuthenticated: false,
  setAuth: (user, organization, accessToken) => {
    set({ user, organization, accessToken, isAuthenticated: true, isLoading: false })
  },
  setUser: user => set({ user }),
  logout: () => {
    set({ user: null, organization: null, accessToken: null, isAuthenticated: false, isLoading: false })
  },
  setLoading: (loading) => set({ isLoading: loading }),
  hasRole: r => { const role = get().user?.role; return role ? ROLE_ORDER.indexOf(role) >= ROLE_ORDER.indexOf(r) : false },
  canWrite: () => get().hasRole('analyst'),
  isAdmin:  () => get().hasRole('admin'),
  isOwner:  () => get().hasRole('owner'),
}), { name: 'auth-store' }))
