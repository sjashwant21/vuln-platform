import { cn } from '@/utils/cn'

const styles: Record<string, string> = {
  critical:      'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  high:          'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  medium:        'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  low:           'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  info:          'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  open:          'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  in_progress:   'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  resolved:      'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  accepted_risk: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  false_positive:'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  running:       'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  completed:     'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  failed:        'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  pending:       'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  queued:        'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  cancelled:     'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
}

const dotColors: Record<string, string> = {
  critical: 'bg-red-500', high: 'bg-orange-500',
  medium: 'bg-yellow-500', low: 'bg-blue-500',
  running: 'bg-blue-500 animate-pulse', completed: 'bg-green-500',
}

interface BadgeProps { variant?: string; children: React.ReactNode; className?: string; dot?: boolean }
export function Badge({ variant = 'info', children, className, dot }: BadgeProps) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium',
      styles[variant] ?? styles.info, className)}>
      {dot && <span className={cn('w-1.5 h-1.5 rounded-full', dotColors[variant] ?? 'bg-gray-400')} />}
      {children}
    </span>
  )
}
