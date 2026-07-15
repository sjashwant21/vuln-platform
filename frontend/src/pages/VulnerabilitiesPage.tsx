import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { vulnsApi } from '@/api'
import { TopBar } from '@/components/layout/TopBar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Select } from '@/components/ui/Input'
import { Table } from '@/components/ui/Table'
import { Pagination } from '@/components/ui/Pagination'
import { Modal } from '@/components/ui/Modal'
import { EmptyState } from '@/components/ui/EmptyState'
import { PageLoader } from '@/components/ui/Spinner'
import { usePermission } from '@/hooks/usePermission'
import { ShieldAlert, Sparkles, CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import type { Vulnerability, VulnStatus, Severity } from '@/types'
import { formatDistanceToNow } from 'date-fns'

const LIMIT = 25

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'accepted_risk', label: 'Accepted Risk' },
  { value: 'false_positive', label: 'False Positive' },
]

const SEVERITY_OPTIONS = [
  { value: '', label: 'All Severities' },
  { value: 'critical', label: 'Critical' },
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

export function VulnerabilitiesPage() {
  const qc = useQueryClient()
  const { canWrite } = usePermission()
  const [offset, setOffset]     = useState(0)
  const [severity, setSeverity] = useState('')
  const [status, setStatus]     = useState('open')
  const [selected, setSelected] = useState<Vulnerability | null>(null)
  const [showStatusModal, setShowStatusModal] = useState(false)
  const [newStatus, setNewStatus] = useState<VulnStatus>('open')
  const [reason, setReason]     = useState('')
  const [showAI, setShowAI]     = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['vulnerabilities', offset, severity, status],
    queryFn: () => vulnsApi.list({ limit: LIMIT, offset, severity: severity || undefined, status: status || undefined }),
  })

  const { data: remediation, isLoading: remLoading } = useQuery({
    queryKey: ['remediation', selected?.id],
    queryFn: () => vulnsApi.getRemediation(selected!.id),
    enabled: showAI && !!selected?.id,
    retry: false,
  })

  const updateStatus = useMutation({
    mutationFn: () => vulnsApi.updateStatus(selected!.id, newStatus, reason || undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vulnerabilities'] })
      setShowStatusModal(false)
      setSelected(null)
      setReason('')
    },
  })

  const generateAI = useMutation({
    mutationFn: () => vulnsApi.generateRemediation(selected!.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['remediation', selected?.id] }),
  })

  const severityColor: Record<Severity, string> = {
    critical: 'text-red-600 dark:text-red-400',
    high:     'text-orange-600 dark:text-orange-400',
    medium:   'text-yellow-600 dark:text-yellow-600',
    low:      'text-blue-600 dark:text-blue-400',
    info:     'text-gray-500',
  }

  const columns = [
    { key: 'severity', header: 'Sev', render: (v: Vulnerability) => (
      <Badge variant={v.severity} dot>{v.severity.slice(0, 4).toUpperCase()}</Badge>
    )},
    { key: 'cve_id', header: 'CVE', render: (v: Vulnerability) => (
      <span className="text-xs font-mono text-gray-600 dark:text-gray-400">{v.cve_id ?? '—'}</span>
    )},
    { key: 'title', header: 'Title', render: (v: Vulnerability) => (
      <div>
        <p className="text-sm font-medium text-gray-900 dark:text-white line-clamp-1">{v.title}</p>
        {v.asset && (
          <p className="text-xs text-gray-400">{v.asset.hostname ?? v.asset.ip_address}</p>
        )}
      </div>
    )},
    { key: 'cvss_score', header: 'CVSS', sortable: true, render: (v: Vulnerability) => (
      v.cvss_score != null
        ? <span className={`text-sm font-bold ${severityColor[v.severity]}`}>{v.cvss_score.toFixed(1)}</span>
        : <span className="text-gray-400">—</span>
    )},
    { key: 'service', header: 'Service', render: (v: Vulnerability) => (
      <span className="text-xs text-gray-500">{v.service}{v.port ? `:${v.port}` : ''}</span>
    )},
    { key: 'status', header: 'Status', render: (v: Vulnerability) => (
      <Badge variant={v.status}>{v.status.replace('_', ' ')}</Badge>
    )},
    { key: 'detected_at', header: 'Age', render: (v: Vulnerability) => (
      <span className="text-xs text-gray-400">
        {formatDistanceToNow(new Date(v.detected_at), { addSuffix: true })}
      </span>
    )},
    { key: 'actions', header: '', render: (v: Vulnerability) => (
      <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
        {canWrite && (
          <Button variant="ghost" size="sm" icon={<CheckCircle className="w-3.5 h-3.5 text-green-500" />}
            onClick={() => { setSelected(v); setNewStatus('resolved'); setShowStatusModal(true) }} />
        )}
        <Button variant="ghost" size="sm" icon={<Sparkles className="w-3.5 h-3.5 text-brand-500" />}
          onClick={() => { setSelected(v); setShowAI(true) }} />
      </div>
    )},
  ]

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Vulnerabilities" subtitle={`${data?.total ?? 0} findings`} />

      <div className="flex-1 p-6 space-y-4 overflow-y-auto">
        {/* Summary badges */}
        <div className="flex flex-wrap gap-2">
          {(['critical', 'high', 'medium', 'low'] as Severity[]).map(sev => {
            const items = data?.items.filter(v => v.severity === sev) ?? []
            return (
              <button key={sev} onClick={() => { setSeverity(sev === severity ? '' : sev); setOffset(0) }}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${sev === severity ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-400' : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-300'}`}>
                <span className={severityColor[sev]}>{sev.charAt(0).toUpperCase() + sev.slice(1)}</span>
                {items.length > 0 && <span className="ml-1 text-gray-400">({items.length})</span>}
              </button>
            )
          })}
        </div>

        <div className="flex flex-wrap gap-3">
          <Select value={status} onChange={e => { setStatus(e.target.value); setOffset(0) }} options={STATUS_OPTIONS} />
          <Select value={severity} onChange={e => { setSeverity(e.target.value); setOffset(0) }} options={SEVERITY_OPTIONS} />
        </div>

        <Card padding={false}>
          {data?.items.length === 0 && !isLoading ? (
            <EmptyState icon={<ShieldAlert className="w-8 h-8" />} title="No vulnerabilities"
              description={status === 'open' ? 'No open vulnerabilities. Run a scan to check for new issues.' : 'No results match your filters.'} />
          ) : (
            <>
              <Table columns={columns} data={data?.items ?? []} loading={isLoading}
                onRowClick={v => setSelected(v)} />
              <div className="px-4">
                <Pagination total={data?.total ?? 0} limit={LIMIT} offset={offset} onChange={setOffset} />
              </div>
            </>
          )}
        </Card>
      </div>

      {/* Vuln detail modal */}
      <Modal open={!!selected && !showStatusModal && !showAI} onClose={() => setSelected(null)}
        title="Vulnerability Detail" size="lg">
        {selected && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Badge variant={selected.severity} dot>{selected.severity}</Badge>
              {selected.cve_id && <span className="text-sm font-mono text-gray-500">{selected.cve_id}</span>}
              {selected.cvss_score && <span className={`text-sm font-bold ${severityColor[selected.severity]}`}>CVSS {selected.cvss_score.toFixed(1)}</span>}
            </div>
            <h3 className="font-semibold text-gray-900 dark:text-white">{selected.title}</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">{selected.description}</p>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                ['Asset', selected.asset?.hostname ?? selected.asset?.ip_address ?? '—'],
                ['Service', `${selected.service ?? '—'}${selected.port ? `:${selected.port}` : ''}`],
                ['Status', selected.status.replace('_', ' ')],
                ['Detected', formatDistanceToNow(new Date(selected.detected_at), { addSuffix: true })],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-xs text-gray-400 mb-0.5">{k}</p>
                  <p className="font-medium text-gray-900 dark:text-white capitalize">{v}</p>
                </div>
              ))}
            </div>
            {canWrite && (
              <div className="flex gap-2 pt-2">
                <Button size="sm" variant="secondary" icon={<Sparkles className="w-4 h-4" />}
                  onClick={() => setShowAI(true)}>AI Remediation</Button>
                <Button size="sm" icon={<CheckCircle className="w-4 h-4" />}
                  onClick={() => { setNewStatus('resolved'); setShowStatusModal(true) }}>Mark Resolved</Button>
                <Button size="sm" variant="ghost" icon={<XCircle className="w-4 h-4" />}
                  onClick={() => { setNewStatus('false_positive'); setShowStatusModal(true) }}>False Positive</Button>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Status update modal */}
      <Modal open={showStatusModal} onClose={() => setShowStatusModal(false)} title="Update Status">
        <div className="space-y-4">
          <Select label="New Status" value={newStatus}
            onChange={e => setNewStatus(e.target.value as VulnStatus)}
            options={STATUS_OPTIONS.filter(o => o.value)} />
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Reason / Notes <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <textarea value={reason} onChange={e => setReason(e.target.value)} rows={3}
              className="w-full rounded-lg border border-gray-300 dark:border-gray-700 px-4 py-2 text-sm bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-500" />
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" className="flex-1" onClick={() => setShowStatusModal(false)}>Cancel</Button>
            <Button className="flex-1" loading={updateStatus.isPending} onClick={() => updateStatus.mutate()}>Update</Button>
          </div>
        </div>
      </Modal>

      {/* AI remediation modal */}
      <Modal open={showAI} onClose={() => setShowAI(false)} title="AI Remediation Plan" size="xl">
        {selected && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <Badge variant={selected.severity}>{selected.severity}</Badge>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{selected.title}</span>
            </div>
            {remLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <Sparkles className="w-8 h-8 text-brand-500 animate-pulse mx-auto mb-2" />
                  <p className="text-sm text-gray-500">Generating AI recommendations…</p>
                </div>
              </div>
            ) : remediation ? (
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono leading-relaxed max-h-96 overflow-y-auto">
                  {remediation.recommendation_markdown}
                </div>
                <div className="flex items-center gap-3 mt-3">
                  {remediation.confidence_score && (
                    <span className="text-xs text-gray-400">
                      Confidence: {(remediation.confidence_score * 100).toFixed(0)}%
                    </span>
                  )}
                  <span className="text-xs text-gray-400">Model: {remediation.ai_model}</span>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <Sparkles className="w-10 h-10 text-brand-400 mx-auto mb-3" />
                <p className="text-sm text-gray-500 mb-4">No AI recommendation yet for this vulnerability.</p>
                <Button icon={<Sparkles className="w-4 h-4" />} loading={generateAI.isPending}
                  onClick={() => generateAI.mutate()}>Generate AI Plan</Button>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
