import { cn } from '@/utils/cn'
import { ChevronUp, ChevronDown } from 'lucide-react'

interface Column<T> {
  key: string; header: string; sortable?: boolean
  render?: (row: T) => React.ReactNode; width?: string
}
interface TableProps<T> {
  columns: Column<T>[]; data: T[]; loading?: boolean
  emptyMessage?: string; onSort?: (key: string) => void
  sortKey?: string; sortDir?: 'asc' | 'desc'
  onRowClick?: (row: T) => void
}
export function Table<T extends { id: string }>({
  columns, data, loading, emptyMessage = 'No data found.',
  onSort, sortKey, sortDir, onRowClick
}: TableProps<T>) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 dark:bg-gray-800/60">
          <tr>
            {columns.map(col => (
              <th key={col.key}
                className={cn('px-4 py-3 text-left font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap',
                  col.sortable && 'cursor-pointer hover:text-gray-900 dark:hover:text-white select-none',
                  col.width)}
                onClick={() => col.sortable && onSort?.(col.key)}
              >
                <div className="flex items-center gap-1">
                  {col.header}
                  {col.sortable && sortKey === col.key && (
                    sortDir === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <tr key={i}>
                {columns.map(col => (
                  <td key={col.key} className="px-4 py-3">
                    <div className="h-4 bg-gray-100 dark:bg-gray-800 rounded animate-pulse w-3/4" />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr><td colSpan={columns.length} className="px-4 py-12 text-center text-gray-400">{emptyMessage}</td></tr>
          ) : (
            data.map(row => (
              <tr key={row.id}
                className={cn('bg-white dark:bg-gray-900 transition-colors',
                  onRowClick && 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/60')}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map(col => (
                  <td key={col.key} className="px-4 py-3 text-gray-700 dark:text-gray-300">
                    {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
