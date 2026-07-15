import { cn } from '@/utils/cn'
import { Loader2 } from 'lucide-react'

interface SpinnerProps { size?: 'sm' | 'md' | 'lg'; className?: string }
export function Spinner({ size = 'md', className }: SpinnerProps) {
  const sizes = { sm: 'w-4 h-4', md: 'w-6 h-6', lg: 'w-8 h-8' }
  return <Loader2 className={cn('animate-spin text-brand-500', sizes[size], className)} />
}

export function PageLoader() {
  return (
    <div className="flex-1 flex items-center justify-center min-h-[400px]">
      <Spinner size="lg" />
    </div>
  )
}
