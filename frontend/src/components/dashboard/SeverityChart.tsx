import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

const COLORS = { critical: '#dc2626', high: '#ea580c', medium: '#d97706', low: '#2563eb', info: '#6b7280' }

interface SeverityChartProps { data: Record<string, number> }
export function SeverityChart({ data }: SeverityChartProps) {
  const chartData = Object.entries(data)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name: name.charAt(0).toUpperCase() + name.slice(1), value, key: name }))

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        No vulnerabilities found
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={chartData} cx="50%" cy="50%" innerRadius={55} outerRadius={85}
          paddingAngle={3} dataKey="value" strokeWidth={0}>
          {chartData.map(entry => (
            <Cell key={entry.key} fill={COLORS[entry.key as keyof typeof COLORS] ?? '#6b7280'} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{ background: 'var(--tw-bg)', border: '1px solid #e5e7eb', borderRadius: 8, fontSize: 12 }}
          formatter={(value: number, name: string) => [value, name]}
        />
        <Legend iconType="circle" iconSize={8} formatter={v => <span className="text-xs text-gray-600 dark:text-gray-400">{v}</span>} />
      </PieChart>
    </ResponsiveContainer>
  )
}
