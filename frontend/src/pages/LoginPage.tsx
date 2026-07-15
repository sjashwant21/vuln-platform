import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Shield, Eye, EyeOff } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { authApi, usersApi, orgApi } from '@/api'
import { useAuthStore } from '@/store/auth.store'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

export function LoginPage() {
  const navigate    = useNavigate()
  const { setAuth } = useAuthStore()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [error, setError]       = useState('')

  const login = useMutation({
    mutationFn: async () => {
      const tokens = await authApi.login(email, password)
      localStorage.setItem('access_token',  tokens.access_token)
      localStorage.setItem('refresh_token', tokens.refresh_token)
      const [user, org] = await Promise.all([usersApi.me(), orgApi.me()])
      return { user, org, tokens }
    },
    onSuccess: ({ user, org, tokens }) => {
      setAuth(user, org, tokens)
      navigate('/')
    },
    onError: () => setError('Invalid email or password'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    login.mutate()
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-950 p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-brand-600 flex items-center justify-center mb-4 shadow-lg">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">VulnAssess</h1>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">AI-Powered Security Platform</p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm p-8">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Sign in to your account</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Email address" type="email" value={email}
              onChange={e => setEmail(e.target.value)} required autoComplete="email" placeholder="you@company.com" />
            <div className="relative">
              <Input label="Password" type={showPw ? 'text' : 'password'} value={password}
                onChange={e => setPassword(e.target.value)} required autoComplete="current-password" placeholder="••••••••" />
              <button type="button" onClick={() => setShowPw(p => !p)}
                className="absolute right-3 top-8 text-gray-400 hover:text-gray-600">
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {error && <p className="text-sm text-red-500 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg">{error}</p>}
            <Button type="submit" className="w-full mt-2" loading={login.isPending}>Sign in</Button>
          </form>
          <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-6">
            Don't have an account?{' '}
            <Link to="/register" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">Create one</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
