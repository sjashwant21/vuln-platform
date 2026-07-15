import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Shield } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '@/api'
import { useAuthStore } from '@/store/auth.store'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

export function RegisterPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [form, setForm] = useState({
    email: '', password: '', full_name: '', organization_name: '', organization_slug: ''
  })
  const [error, setError] = useState('')

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value,
      ...(k === 'organization_name' ? { organization_slug: e.target.value.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') } : {})
    }))

  const register = useMutation({
    mutationFn: () => authApi.register(form),
    onSuccess: ({ user, organization, tokens }) => {
      setAuth(user, organization, tokens)
      navigate('/')
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { error?: string } } })?.response?.data?.error
      setError(msg ?? 'Registration failed. Please try again.')
    },
  })

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); setError(''); register.mutate() }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-950 p-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-2xl bg-brand-600 flex items-center justify-center mb-4 shadow-lg">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Create your account</h1>
        </div>
        <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-800 shadow-sm p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input label="Full name" value={form.full_name} onChange={set('full_name')} required placeholder="Alice Smith" />
            <Input label="Work email" type="email" value={form.email} onChange={set('email')} required placeholder="alice@company.com" />
            <Input label="Password" type="password" value={form.password} onChange={set('password')} required
              hint="Min 8 chars, one uppercase, one digit" />
            <hr className="border-gray-100 dark:border-gray-800" />
            <Input label="Organisation name" value={form.organization_name} onChange={set('organization_name')} required placeholder="Acme Corp" />
            <Input label="Organisation slug" value={form.organization_slug} onChange={set('organization_slug')} required
              placeholder="acme-corp" hint="URL-safe identifier, e.g. acme-corp" />
            {error && <p className="text-sm text-red-500 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg">{error}</p>}
            <Button type="submit" className="w-full mt-2" loading={register.isPending}>Create account</Button>
          </form>
          <p className="text-center text-sm text-gray-500 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-600 dark:text-brand-400 font-medium hover:underline">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
