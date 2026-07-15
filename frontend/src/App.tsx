import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useAuthStore } from '@/store/auth.store'
import { usersApi, orgApi } from '@/api'
import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage }          from '@/pages/LoginPage'
import { RegisterPage }       from '@/pages/RegisterPage'
import { DashboardPage }      from '@/pages/DashboardPage'
import { AssetsPage }         from '@/pages/AssetsPage'
import { ScansPage }          from '@/pages/ScansPage'
import { VulnerabilitiesPage }from '@/pages/VulnerabilitiesPage'
import { ReportsPage }        from '@/pages/ReportsPage'
import { SettingsPage }       from '@/pages/SettingsPage'
import { PageLoader }         from '@/components/ui/Spinner'

const qc = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, err) => {
        const status = (err as { response?: { status?: number } })?.response?.status
        if (status === 401 || status === 403 || status === 404) return false
        return count < 2
      },
    },
  },
})

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore()
  if (isLoading) return <PageLoader />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppBootstrap() {
  const { setAuth, logout, isLoading } = useAuthStore()
  const [booted, setBooted] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) { logout(); setBooted(true); return }
    Promise.all([usersApi.me(), orgApi.me()])
      .then(([user, org]) => {
        setAuth(user, org, {
          access_token:  localStorage.getItem('access_token')  ?? '',
          refresh_token: localStorage.getItem('refresh_token') ?? '',
          token_type: 'bearer', expires_in: 900,
        })
      })
      .catch(() => logout())
      .finally(() => setBooted(true))
  }, [])

  if (!booted) return <PageLoader />
  return null
}

export default function App() {
  // Apply saved theme on mount
  useEffect(() => {
    const theme = localStorage.getItem('theme')
    if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      document.documentElement.classList.add('dark')
    }
  }, [])

  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <AppBootstrap />
        <Routes>
          {/* Public */}
          <Route path="/login"    element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected */}
          <Route element={<AuthGuard><AppLayout /></AuthGuard>}>
            <Route index                   element={<DashboardPage />} />
            <Route path="assets"           element={<AssetsPage />} />
            <Route path="scans"            element={<ScansPage />} />
            <Route path="vulnerabilities"  element={<VulnerabilitiesPage />} />
            <Route path="reports"          element={<ReportsPage />} />
            <Route path="settings"         element={<SettingsPage />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
