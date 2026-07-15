import { cn } from '@/utils/cn'

interface HealthGaugeProps { score: number; label: string; grade: string }
export function HealthGauge({ score, label, grade }: HealthGaugeProps) {
  const color =
    score >= 80 ? 'text-green-500'  :
    score >= 60 ? 'text-yellow-500' :
    score >= 40 ? 'text-orange-500' : 'text-red-500'

  const ringColor =
    score >= 80 ? 'stroke-green-500'  :
    score >= 60 ? 'stroke-yellow-500' :
    score >= 40 ? 'stroke-orange-500' : 'stroke-red-500'

  const circumference = 2 * Math.PI * 45
  const offset = circumference - (score / 100) * circumference

  return (
    <div className="flex flex-col items-center justify-center py-4">
      <div className="relative w-36 h-36">
        <svg className="w-36 h-36 -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" fill="none" strokeWidth="8"
            className="stroke-gray-100 dark:stroke-gray-800" />
          <circle cx="50" cy="50" r="45" fill="none" strokeWidth="8"
            strokeDasharray={circumference} strokeDashoffset={offset}
            strokeLinecap="round" className={cn('transition-all duration-700', ringColor)} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn('text-3xl font-bold', color)}>{score}</span>
          <span className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">/ 100</span>
        </div>
      </div>
      <div className="mt-3 text-center">
        <p className={cn('text-lg font-bold', color)}>{grade} — {label}</p>
      </div>
    </div>
  )
}
