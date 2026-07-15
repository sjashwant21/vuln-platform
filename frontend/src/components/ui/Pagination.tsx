import { Button } from './Button'
import { ChevronLeft, ChevronRight } from 'lucide-react'

interface PaginationProps { total: number; limit: number; offset: number; onChange: (offset: number) => void }
export function Pagination({ total, limit, offset, onChange }: PaginationProps) {
  const page  = Math.floor(offset / limit) + 1
  const pages = Math.ceil(total / limit)
  if (pages <= 1) return null
  return (
    <div className="flex items-center justify-between px-1 py-3">
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Showing {offset + 1}–{Math.min(offset + limit, total)} of {total}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="secondary" size="sm" icon={<ChevronLeft className="w-4 h-4" />}
          disabled={page === 1} onClick={() => onChange(offset - limit)}>Prev</Button>
        <span className="text-sm text-gray-600 dark:text-gray-400">Page {page} / {pages}</span>
        <Button variant="secondary" size="sm" disabled={page === pages}
          onClick={() => onChange(offset + limit)}>
          Next<ChevronRight className="w-4 h-4" />
        </Button>
      </div>
    </div>
  )
}
