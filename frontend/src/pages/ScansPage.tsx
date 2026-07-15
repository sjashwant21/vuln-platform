import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { scansApi } from '@/api'
import { TopBar } from '@/components/layout/TopBar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input, Select } from '@/components/ui/Input'
import { Table } from '@/components/ui/Table'
import { Pagination } from '@/components/ui/Pagination'
import { Modal } from '@/components/ui/Modal'
import { EmptyState } from '@/components/ui/EmptyState'
import { usePermission } from '@/hooks/usePermission'
import { Scan, Plus, X, Play, RefreshCw, Clock, CheckCircle, XCircle, AlertTriangle } from 'lucide-react'
import type { ScanJob, ScanType } from '@/types'
import { formatDistanceToNow, format } from 'date-fns'

const LIMIT = 20

const scanTypeOptions = [
  { value: 'vulnerability', label: 'Full Vulnerability Scan' },
  { value: 'port_scan',     label: 'Port Scan' },
  { value: 'service_enum',  label: 'Service Enumeration' },
  { value: 'discovery',     label: 'Host Discovery' },
]

function ScanStatusIcon({ status }: { status: string }) {
  if (status === 'running')   return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />
  if (status === 'completed') return <CheckCircle className="w-4 h-4 text-green-500" />
  if (status === 'failed')    return <XCircle className="w-4 h-4 text-red-500" />
  if (status === 'pending' || status === 'queued') return <Clock className="w-4 h-4 text-yellow-500" />
  return <AlertTriangle className="w-4 h-4 text-gray-400" />
}

function duration(scan: ScanJob) {
  if (!scan.started_at) return '—'
  const end = scan.completed_at ? new Date(scan.completed_at) : new Date()
  const secs = Math.floor((end.getTime() - new Date(scan.started_at).getTime()) / 1000)
  if (secs < 60) return `${secs}s`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`
  return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`
}

export function ScansPage() {
  const qc = useQueryClient()
  const { canWrite } = usePermission()
  const [offset, setOffset]       = useState(0)
  const [statusFilter, setStatus] = useState('')
  const [showNew, setShowNew]     = useState(false)
  const [selected, setSelected]   = useState<ScanJob | null>(null)
  const [form, setForm] = useState({ scan_type: 'vulnerability' as ScanType, targets: '' })

  const { data, isLoading } = useQuery({
    queryKey: ['scans', offset, statusFilter],
    queryFn: () => scansApi.list({ limit: LIMIT, offset, status: statusFilter || undefined }),
    refetchInterval: 5_000,
  })

  const { data: findings } = useQuery({
    queryKey: ['scan-findings', selected?.id],
    queryFn: () => scansApi.findings(selected!.id),
    enabled: !!selected?.id && selected.status === 'completed',
  })

  const launch = useMutation({
    mutationFn: () => scansApi.create({
      scan_type: form.scan_type,
      target_ips: form.targets.split(/[\s,]+/).map(s => s.trim()).filter(Boolean),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['scans'] }); setShowNew(false); setForm({ scan_type: 'vulnerability', targets: '' }) },
  })

  const cancel = useMutation({
    mutationFn: (id: string) => scansApi.cancel(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scans'] }),
  })

  const columns = [
    { key: 'status', header: 'Status', render: (s: ScanJob) => (
      <div className="flex items-center gap-2">
        <ScanStatusIcon status={s.status} />
        <Badge variant={s.status}>{s.status}</Badge>
      </div>
    )},
    { key: 'scan_type', header: 'Type', render: (s: ScanJob) => (
      <span className="text-sm capitalize text-gray-700 dark:text-gray-300">{s.scan_type.replace(/_/g, ' ')}</span>
    )},
    { key: 'targets', header: 'Targets', render: (s: ScanJob) => (
      <span className="text-xs font-mono text-gray-500">
        {s.target_ips.slice(0, 3).join(', ')}{s.target_ips.length > 3 ? ` +${s.target_ips.length - 3}` : ''}
      </span>
    )},
    { key: 'duration', header: 'Duration', render: (s: ScanJob) => (
      <span className="text-sm text-gray-500">{duration(s)}</span>
    )},
    { key: 'findings', header: 'Findings', render: (s: ScanJob) => (
      s.result_summary?.vulnerabilities_found != null
        ? <span className="text-sm font-medium text-orange-500">{s.result_summary.vulnerabilities_found}</span>
        : <span className="text-sm text-gray-400">—</span>
    )},
    { key: 'created_at', header: 'Started', render: (s: ScanJob) => (
      <span className="text-xs text-gray-400">
        {formatDistanceToNow(new Date(s.created_at), { addSuffix: true })}
      </span>
    )},
    { key: 'actions', header: '', render: (s: ScanJob) => (
      <div onClick={e => e.stopPropagation()}>
        {(s.status === 'running' || s.status === 'queued' || s.status === 'pending') && canWrite && (
          <Button variant="ghost" size="sm" icon={<X className="w-3.5 h-3.5 text-red-400" />}
            onClick={() => cancel.mutate(s.id)} />
        )}
      </div>
    )},
  ]

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Scans" subtitle={`${data?.total ?? 0} total scans`}
        actions={canWrite ? (
          <Button size="sm" icon={<Plus className="w-4 h-4" />} onClick={() => setShowNew(true)}>New Scan</Button>
        ) : undefined}
      />

      <div className="flex-1 p-6 space-y-4 overflow-y-auto">
        <Select value={statusFilter} onChange={e => { setStatus(e.target.value); setOffset(0) }}
          options={[
            { value: '', label: 'All Statuses' }, { value: 'running', label: 'Running' },
            { value: 'completed', label: 'Completed' }, { value: 'failed', label: 'Failed' },
            { value: 'pending', label: 'Pending' },
          ]} />

        <Card padding={false}>
          {data?.items.length === 0 && !isLoading ? (
            <EmptyState icon={<Scan className="w-8 h-8" />} title="No scans yet"
              description="Launch a scan to discover vulnerabilities across your assets."
              action={canWrite ? { label: 'Launch Scan', onClick: () => setShowNew(true) } : undefined} />
          ) : (
            <>
              <Table columns={columns} data={data?.items ?? []} loading={isLoading} onRowClick={setSelected} />
              <div className="px-4">
                <Pagination total={data?.total ?? 0} limit={LIMIT} offset={offset} onChange={setOffset} />
              </div>
            </>
          )}
        </Card>
      </div>

      {/* Launch scan modal */}
      <Modal open={showNew} onClose={() => setShowNew(false)} title="Launch New Scan">
        <div className="space-y-4">
          <Select label="Scan Type" value={form.scan_type}
            onChange={e => setForm(f => ({ ...f, scan_type: e.target.value as ScanType }))}
            options={scanTypeOptions} />
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Target IPs / CIDRs</label>
            <textarea value={form.targets} onChange={e => setForm(f => ({ ...f, targets: e.target.value }))}
              rows={4} placeholder={"10.0.0.1\n10.0.0.2\n192.168.1.0/24"}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-700 px-4 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500 font-mono" />
            <p className="text-xs text-gray-400 mt-1">One IP or CIDR per line, or comma-separated.</p>
          </div>
          <div className="flex gap-3 pt-2">
            <Button variant="secondary" className="flex-1" onClick={() => setShowNew(false)}>Cancel</Button>
            <Button className="flex-1" icon={<Play className="w-4 h-4" />}
              loading={launch.isPending} onClick={() => launch.mutate()}>Launch</Button>
          </div>
        </div>
      </Modal>

      {/* Scan detail modal */}
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Scan Detail" size="xl">
        {selected && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              {[
                ['Status', <Badge key="s" variant={selected.status}>{selected.status}</Badge>],
                ['Type', selected.scan_type.replace(/_/g, ' ')],
                ['Started', selected.started_at ? format(new Date(selected.started_at), 'MMM d, HH:mm') : '—'],
                ['Duration', duration(selected)],
                ['Hosts found', selected.result_summary?.hosts_discovered ?? '—'],
                ['Ports scanned', selected.result_summary?.ports_scanned ?? '—'],
                ['Vulns found', selected.result_summary?.vulnerabilities_found ?? '—'],
                ['Targets', selected.target_ips.length],
              ].map(([k, v]) => (
                <div key={String(k)}>
                  <p className="text-xs text-gray-400 mb-0.5">{k}</p>
                  <p className="font-medium text-gray-900 dark:text-white capitalize">{v}</p>
                </div>
              ))}
            </div>
            {selected.error_message && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
                <p className="text-sm text-red-600 dark:text-red-400">{selected.error_message}</p>
              </div>
            )}
            {findings && findings.length > 0 && (
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Findings ({findings.length})</p>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {findings.map(f => (
                    <div key={f.id} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                      <Badge variant={f.severity}>{f.severity}</Badge>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">{f.title}</p>
                        {f.cve_ids.length > 0 && <p className="text-xs text-gray-400 font-mono">{f.cve_ids.join(', ')}</p>}
                      </div>
                      {f.cvss_score && <span className="text-xs font-bold text-orange-500 shrink-0">{f.cvss_score.toFixed(1)}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
