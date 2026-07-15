import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format, parseISO } from 'date-fns'

interface TrendChartProps { data: Array<{ date: string; score: number }> }
export function TrendChart({ data }: TrendChartProps) {
  if (!data.length) return (
    <div className="flex items-center justify-center h-48 text-gray-400 text-sm">No trend data</div>
  )
  const formatted = data.map(d => ({
    ...d,
    label: (() => { try { return format(parseISO(d.date), 'MMM d') } catch { return d.date } })()
  }))
  return (
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={formatted}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" className="dark:stroke-gray-800" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, fontSize: 12 }}
          formatter={(v: number) => [`${v}/100`, 'Health Score']}
        />
        <Line type="monotone" dataKey="score" stroke="#4f46e5" strokeWidth={2.5}
          dot={{ fill: '#4f46e5', strokeWidth: 0, r: 3 }} activeDot={{ r: 5 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}
