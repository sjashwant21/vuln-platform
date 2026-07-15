import { useAuthStore } from '@/store/auth.store'
import type { UserRole } from '@/types'

export function usePermission() {
  const { hasRole, canWrite, isAdmin, isOwner } = useAuthStore()
  return { hasRole, canWrite: canWrite(), isAdmin: isAdmin(), isOwner: isOwner() }
}

export function useRequireRole(role: UserRole) {
  const { hasRole } = useAuthStore()
  return hasRole(role)
}
