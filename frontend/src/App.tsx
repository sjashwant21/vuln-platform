import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useAuthStore } from '@/store/auth.store'
import { usersApi, orgApi } from '@/api'
import { AppLayout } from '@/components/layout/AppLayout'

// ── Public landing & marketing pages ──────────────────────────────────────────
import LandingPage    from '@/pages/LandingPage'
import DocsPage       from '@/pages/DocsPage'
import PricingPage    from '@/pages/PricingPage'
import SecurityPage   from '@/pages/SecurityPage'
import PrivacyPage    from '@/pages/PrivacyPage'
import TermsPage      from '@/pages/TermsPage'
import ContactPage    from '@/pages/ContactPage'
import AboutPage      from '@/pages/AboutPage'
import GlossaryPage   from '@/pages/GlossaryPage'
import ChangelogPage  from '@/pages/ChangelogPage'
import DemoPage       from '@/pages/DemoPage'
import NotFoundPage   from '@/pages/NotFoundPage'

// ── Authenticated app pages ────────────────────────────────────────────────────
import { LoginPage }           from '@/pages/LoginPage'
import { RegisterPage }        from '@/pages/RegisterPage'
import { DashboardPage }       from '@/pages/DashboardPage'
import { AssetsPage }          from '@/pages/AssetsPage'
import { ScansPage }           from '@/pages/ScansPage'
import { VulnerabilitiesPage } from '@/pages/VulnerabilitiesPage'
import { ReportsPage }         from '@/pages/ReportsPage'
import { SettingsPage }        from '@/pages/SettingsPage'
import { PageLoader }          from '@/components/ui/Spinner'

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

// ── Scroll-to-top on every navigation ─────────────────────────────────────────
function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    if (!window.location.hash) {
      window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior })
    }
  }, [pathname])
  return null
}

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore()
  if (isLoading) return <PageLoader />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AppBootstrap() {
  const { setAuth, logout } = useAuthStore()
  const [booted, setBooted] = useState(false)

  useEffect(() => {
    // Attempt silent refresh via secure HttpOnly cookie
    import('@/api').then(({ authApi, usersApi, orgApi }) => {
      authApi.refresh()
        .then((data) => {
          // Token acquired successfully; fetch user details
          Promise.all([usersApi.me(), orgApi.me()])
            .then(([user, org]) => {
              setAuth(user, org, data.access_token)
            })
            .catch(() => logout())
            .finally(() => setBooted(true))
        })
        .catch(() => {
          // No valid session cookie, user must log in
          logout()
          setBooted(true)
        })
    })
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
        <ScrollToTop />
        <AppBootstrap />
        <Routes>
          {/* ── Public landing ──────────────────────────────────────────────── */}
          <Route path="/"          element={<LandingPage   />} />

          {/* ── Marketing / content pages ───────────────────────────────────── */}
          <Route path="/docs"      element={<DocsPage      />} />
          <Route path="/pricing"   element={<PricingPage   />} />
          <Route path="/security"  element={<SecurityPage  />} />
          <Route path="/security/disclosure" element={<SecurityPage />} />
          <Route path="/security/data"       element={<SecurityPage />} />
          <Route path="/privacy"   element={<PrivacyPage   />} />
          <Route path="/terms"     element={<TermsPage     />} />
          <Route path="/contact"   element={<ContactPage   />} />
          <Route path="/about"     element={<AboutPage     />} />
          <Route path="/glossary"  element={<GlossaryPage  />} />
          <Route path="/changelog" element={<ChangelogPage />} />
          <Route path="/demo"      element={<DemoPage      />} />

          {/* ── Auth pages ──────────────────────────────────────────────────── */}
          <Route path="/login"     element={<LoginPage    />} />
          <Route path="/register"  element={<RegisterPage />} />

          {/* ── Protected app ───────────────────────────────────────────────── */}
          <Route element={<AuthGuard><AppLayout /></AuthGuard>}>
            <Route path="dashboard"       element={<DashboardPage      />} />
            <Route path="assets"          element={<AssetsPage         />} />
            <Route path="scans"           element={<ScansPage          />} />
            <Route path="vulnerabilities" element={<VulnerabilitiesPage/>} />
            <Route path="reports"         element={<ReportsPage        />} />
            <Route path="settings"        element={<SettingsPage       />} />
          </Route>

          {/* ── 404 catch-all ───────────────────────────────────────────────── */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
