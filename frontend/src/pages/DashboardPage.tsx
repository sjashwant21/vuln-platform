import { useQuery } from '@tanstack/react-query'
import { dashboardApi } from '@/api'
import { TopBar } from '@/components/layout/TopBar'
import { Card, StatCard } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { HealthGauge } from '@/components/dashboard/HealthGauge'
import { SeverityChart } from '@/components/dashboard/SeverityChart'
import { TrendChart } from '@/components/dashboard/TrendChart'
import { PageLoader } from '@/components/ui/Spinner'
import { Button } from '@/components/ui/Button'
import { ShieldAlert, Server, Scan, AlertTriangle, RefreshCw } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'

export function DashboardPage() {
  const navigate = useNavigate()

  const summary = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: dashboardApi.summary,
    refetchInterval: 30_000,
  })

  const health = useQuery({
    queryKey: ['health-score'],
    queryFn: dashboardApi.healthScore,
    refetchInterval: 60_000,
  })

  if (summary.isLoading || health.isLoading) return <PageLoader />

  const s = summary.data
  const h = health.data

  const severityData = {
    critical: s?.critical_count ?? 0,
    high:     s?.high_count ?? 0,
    medium:   s?.medium_count ?? 0,
    low:      s?.low_count ?? 0,
  }

  return (
    <div className="flex flex-col h-full">
      <TopBar
        title="Dashboard"
        subtitle="Security posture at a glance"
        actions={
          <Button variant="ghost" size="sm" icon={<RefreshCw className="w-4 h-4" />}
            onClick={() => { summary.refetch(); health.refetch() }}>
            Refresh
          </Button>
        }
      />

      <div className="flex-1 p-6 space-y-6 overflow-y-auto">
        {/* Health + Stats row */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          {/* Health gauge card */}
          <Card className="lg:col-span-1">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">Security Health</p>
            <HealthGauge
              score={h?.score ?? 0}
              label={h?.label ?? 'Unknown'}
              grade={h?.grade ?? '?'}
            />
          </Card>

          {/* Stat cards */}
          <div className="lg:col-span-3 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard label="Total Assets" value={s?.total_assets ?? 0}
              icon={<Server className="w-5 h-5 text-brand-500" />}
              color="text-brand-600 dark:text-brand-400" />
            <StatCard label="Critical" value={s?.critical_count ?? 0}
              icon={<AlertTriangle className="w-5 h-5 text-red-500" />}
              color="text-red-600 dark:text-red-400" />
            <StatCard label="High" value={s?.high_count ?? 0}
              icon={<ShieldAlert className="w-5 h-5 text-orange-500" />}
              color="text-orange-600 dark:text-orange-400" />
            <StatCard label="Open Vulns" value={s?.open_vulnerabilities ?? 0}
              icon={<Scan className="w-5 h-5 text-yellow-500" />}
              color="text-yellow-600 dark:text-yellow-400" />
          </div>
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Severity Distribution</p>
            <SeverityChart data={severityData} />
          </Card>
          <Card>
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Health Score Trend</p>
            <TrendChart data={h?.trend ?? []} />
          </Card>
        </div>

        {/* Recent scans */}
        <Card padding={false}>
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-800">
            <p className="text-sm font-semibold text-gray-700 dark:text-gray-300">Recent Scans</p>
            <Button variant="ghost" size="sm" onClick={() => navigate('/scans')}>View all</Button>
          </div>
          <div className="divide-y divide-gray-50 dark:divide-gray-800">
            {(s?.recent_scans ?? []).length === 0 ? (
              <div className="px-6 py-8 text-center text-sm text-gray-400">No scans yet. <button className="text-brand-600 hover:underline" onClick={() => navigate('/scans')}>Launch your first scan →</button></div>
            ) : (s?.recent_scans ?? []).slice(0, 5).map(scan => (
              <div key={scan.id} className="flex items-center justify-between px-6 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/40 cursor-pointer"
                onClick={() => navigate(`/scans/${scan.id}`)}>
                <div className="flex items-center gap-3">
                  <Badge variant={scan.status} dot>{scan.status}</Badge>
                  <span className="text-sm text-gray-600 dark:text-gray-400">{scan.scan_type.replace('_', ' ')}</span>
                  <span className="text-xs text-gray-400">{scan.target_ips.slice(0, 2).join(', ')}{scan.target_ips.length > 2 ? ` +${scan.target_ips.length - 2}` : ''}</span>
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-400">
                    {scan.created_at ? formatDistanceToNow(new Date(scan.created_at), { addSuffix: true }) : '—'}
                  </p>
                  {scan.result_summary?.vulnerabilities_found != null && (
                    <p className="text-xs font-medium text-orange-500">{scan.result_summary.vulnerabilities_found} vulns found</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
