import { Bell, Search } from 'lucide-react'
import { useAuthStore } from '@/store/auth.store'
import { Badge } from '@/components/ui/Badge'

interface TopBarProps { title: string; subtitle?: string; actions?: React.ReactNode }
export function TopBar({ title, subtitle, actions }: TopBarProps) {
  const { organization } = useAuthStore()
  return (
    <header className="flex items-center justify-between px-6 py-4 bg-white dark:bg-gray-950 border-b border-gray-100 dark:border-gray-800 shrink-0">
      <div>
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{title}</h1>
        {subtitle && <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        {actions}
        <Badge variant="info" className="hidden sm:inline-flex">
          {organization?.plan_tier?.toUpperCase() ?? 'FREE'}
        </Badge>
      </div>
    </header>
  )
}
