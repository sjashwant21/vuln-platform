import { cn } from '@/utils/cn'

interface CardProps { children: React.ReactNode; className?: string; padding?: boolean }
export function Card({ children, className, padding = true }: CardProps) {
  return (
    <div className={cn(
      'bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm',
      padding && 'p-6', className
    )}>
      {children}
    </div>
  )
}

interface StatCardProps {
  label: string; value: string | number; icon?: React.ReactNode
  trend?: { value: number; label: string }; color?: string; className?: string
}
export function StatCard({ label, value, icon, trend, color = 'text-gray-900 dark:text-white', className }: StatCardProps) {
  return (
    <Card className={cn('flex items-start justify-between', className)}>
      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">{label}</p>
        <p className={cn('text-3xl font-bold', color)}>{value}</p>
        {trend && (
          <p className={cn('text-xs mt-1', trend.value >= 0 ? 'text-red-500' : 'text-green-500')}>
            {trend.value > 0 ? '▲' : '▼'} {Math.abs(trend.value)} {trend.label}
          </p>
        )}
      </div>
      {icon && <div className="p-2 bg-gray-50 dark:bg-gray-800 rounded-lg">{icon}</div>}
    </Card>
  )
}
