import { NavLink, useNavigate } from 'react-router-dom'
import { cn } from '@/utils/cn'
import { useAuthStore } from '@/store/auth.store'
import {
  LayoutDashboard, Server, Scan, ShieldAlert, FileText,
  Settings, LogOut, Shield, ChevronRight, Moon, Sun
} from 'lucide-react'
import { useState } from 'react'

const navItems = [
  { path: '/',              label: 'Dashboard',       icon: LayoutDashboard, minRole: 'viewer'  },
  { path: '/assets',        label: 'Assets',          icon: Server,          minRole: 'viewer'  },
  { path: '/scans',         label: 'Scans',           icon: Scan,            minRole: 'viewer'  },
  { path: '/vulnerabilities',label: 'Vulnerabilities', icon: ShieldAlert,     minRole: 'viewer'  },
  { path: '/reports',       label: 'Reports',         icon: FileText,        minRole: 'viewer'  },
  { path: '/settings',      label: 'Settings',        icon: Settings,        minRole: 'analyst' },
]

function useDarkMode() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'))
  const toggle = () => {
    document.documentElement.classList.toggle('dark')
    setDark(d => !d)
    localStorage.setItem('theme', dark ? 'light' : 'dark')
  }
  return { dark, toggle }
}

export function Sidebar() {
  const { user, organization, logout, hasRole } = useAuthStore()
  const navigate = useNavigate()
  const { dark, toggle } = useDarkMode()

  const handleLogout = async () => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      try { await import('@/api').then(m => m.authApi.logout(refreshToken)) } catch {}
    }
    logout()
    navigate('/login')
  }

  return (
    <aside className="w-64 shrink-0 flex flex-col h-screen bg-white dark:bg-gray-950 border-r border-gray-200 dark:border-gray-800">
      {/* Logo */}
      <div className="flex items-center gap-3 px-6 py-5 border-b border-gray-100 dark:border-gray-800">
        <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <p className="font-bold text-gray-900 dark:text-white text-sm leading-tight">VulnAssess</p>
          <p className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[120px]">
            {organization?.name ?? '—'}
          </p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map(item => {
          if (!hasRole(item.minRole as 'viewer' | 'analyst' | 'admin' | 'owner')) return null
          const Icon = item.icon
          return (
            <NavLink key={item.path} to={item.path} end={item.path === '/'}
              className={({ isActive }) => cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group',
                isActive
                  ? 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-400'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/60 hover:text-gray-900 dark:hover:text-white'
              )}>
              {({ isActive }) => (
                <>
                  <Icon className={cn('w-5 h-5', isActive ? 'text-brand-600 dark:text-brand-400' : 'text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300')} />
                  {item.label}
                  {isActive && <ChevronRight className="w-3.5 h-3.5 ml-auto text-brand-500" />}
                </>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-gray-100 dark:border-gray-800 space-y-1">
        <button onClick={toggle}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/60">
          {dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          {dark ? 'Light mode' : 'Dark mode'}
        </button>
        <div className="flex items-center gap-3 px-3 py-2.5">
          <div className="w-7 h-7 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center text-brand-700 dark:text-brand-400 text-xs font-bold shrink-0">
            {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-gray-900 dark:text-white truncate">{user?.full_name}</p>
            <p className="text-xs text-gray-400 truncate">{user?.role}</p>
          </div>
          <button onClick={handleLogout} className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-red-500">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
