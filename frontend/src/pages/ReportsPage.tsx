import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { reportsApi } from '@/api'
import { TopBar } from '@/components/layout/TopBar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { FileText, Download, Eye, Loader2, CheckCircle, BarChart3, Shield, ClipboardList } from 'lucide-react'
import type { ReportFormat, ReportType } from '@/types'

interface ReportConfig {
  type: ReportType
  label: string
  description: string
  icon: React.ReactNode
  color: string
  audience: string
  sections: string[]
}

const REPORT_CONFIGS: ReportConfig[] = [
  {
    type: 'executive',
    label: 'Executive Report',
    description: 'High-level security posture summary with AI recommendations for leadership.',
    icon: <BarChart3 className="w-6 h-6" />,
    color: 'bg-brand-50 dark:bg-brand-900/20 text-brand-600 dark:text-brand-400',
    audience: 'CTO / Board',
    sections: ['Security Score', 'Key Findings', 'Risk Trend', 'AI Recommendations', 'Management Summary'],
  },
  {
    type: 'technical',
    label: 'Technical Report',
    description: 'Full asset inventory, vulnerability breakdown, and detailed remediation steps.',
    icon: <FileText className="w-6 h-6" />,
    color: 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400',
    audience: 'Security Engineers',
    sections: ['Asset Inventory', 'Vulnerability Details', 'Risk Trend', 'Attack Paths', 'Remediation'],
  },
  {
    type: 'vulnerability',
    label: 'Vulnerability Report',
    description: 'Complete listing of all open, resolved, and accepted-risk findings.',
    icon: <Shield className="w-6 h-6" />,
    color: 'bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400',
    audience: 'Ops / DevSecOps',
    sections: ['Open Vulns', 'Critical CVEs', 'Severity Distribution', 'Age Analysis', 'By Asset'],
  },
  {
    type: 'compliance',
    label: 'Compliance Report',
    description: 'PCI-DSS and SOC 2 control mapping based on current vulnerability state.',
    icon: <ClipboardList className="w-6 h-6" />,
    color: 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400',
    audience: 'Compliance / Audit',
    sections: ['PCI-DSS Controls', 'SOC 2 Controls', 'Compliance %', 'Gap Analysis', 'Remediation Roadmap'],
  },
]

interface GenerationState {
  type: ReportType
  format: ReportFormat
  status: 'generating' | 'done' | 'error'
  filename?: string
  blob?: Blob
  error?: string
}

export function ReportsPage() {
  const [format, setFormat] = useState<ReportFormat>('pdf')
  const [periodDays, setPeriodDays] = useState('30')
  const [states, setStates] = useState<Record<string, GenerationState>>({})

  const generate = useMutation({
    mutationFn: ({ type }: { type: ReportType }) =>
      reportsApi.generate({ report_type: type, report_format: format, period_days: parseInt(periodDays) }),
    onMutate: ({ type }) => {
      setStates(s => ({ ...s, [type]: { type, format, status: 'generating' } }))
    },
    onSuccess: ({ blob, filename }, { type }) => {
      setStates(s => ({ ...s, [type]: { type, format, status: 'done', blob, filename } }))
    },
    onError: (err: unknown, { type }) => {
      const msg = (err as { message?: string })?.message ?? 'Generation failed'
      setStates(s => ({ ...s, [type]: { type, format, status: 'error', error: msg } }))
    },
  })

  const downloadBlob = (state: GenerationState) => {
    if (!state.blob || !state.filename) return
    const url = URL.createObjectURL(state.blob)
    const a   = document.createElement('a')
    a.href    = url
    a.download = state.filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const previewReport = (type: ReportType) => {
    window.open(`/v1/reports/preview?report_type=${type}`, '_blank')
  }

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Reports" subtitle="Generate security reports in PDF or DOCX format" />

      <div className="flex-1 p-6 space-y-6 overflow-y-auto">
        {/* Global options */}
        <Card>
          <p className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Report Options</p>
          <div className="flex flex-wrap gap-4">
            <Select label="Output Format" value={format}
              onChange={e => setFormat(e.target.value as ReportFormat)}
              options={[{ value: 'pdf', label: 'PDF Document' }, { value: 'docx', label: 'Word Document (DOCX)' }]} />
            <Select label="Assessment Period" value={periodDays}
              onChange={e => setPeriodDays(e.target.value)}
              options={[
                { value: '7',   label: 'Last 7 days' },
                { value: '30',  label: 'Last 30 days' },
                { value: '90',  label: 'Last 90 days' },
                { value: '180', label: 'Last 6 months' },
                { value: '365', label: 'Last year' },
              ]} />
          </div>
          <p className="text-xs text-gray-400 mt-3">
            Reports are generated from live data. PDF reports include embedded charts and are optimised for printing.
            DOCX reports are editable in Microsoft Word.
          </p>
        </Card>

        {/* Report cards */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {REPORT_CONFIGS.map(config => {
            const state = states[config.type]
            const isGenerating = state?.status === 'generating'
            const isDone       = state?.status === 'done'
            const isError      = state?.status === 'error'

            return (
              <Card key={config.type} className="flex flex-col">
                {/* Header */}
                <div className="flex items-start gap-4 mb-4">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${config.color}`}>
                    {config.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-gray-900 dark:text-white">{config.label}</h3>
                      <Badge variant="info" className="text-xs">{config.audience}</Badge>
                    </div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{config.description}</p>
                  </div>
                </div>

                {/* Sections list */}
                <div className="flex flex-wrap gap-1.5 mb-5">
                  {config.sections.map(s => (
                    <span key={s} className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-md">
                      {s}
                    </span>
                  ))}
                </div>

                {/* Status / error */}
                {isError && (
                  <div className="mb-3 px-3 py-2 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                    <p className="text-xs text-red-600 dark:text-red-400">{state.error}</p>
                  </div>
                )}
                {isDone && (
                  <div className="mb-3 flex items-center gap-2 px-3 py-2 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
                    <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
                    <p className="text-xs text-green-600 dark:text-green-400 truncate">{state.filename} — ready to download</p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 mt-auto">
                  <Button variant="secondary" size="sm" icon={<Eye className="w-4 h-4" />}
                    onClick={() => previewReport(config.type)} className="flex-1">
                    Preview
                  </Button>
                  {isDone ? (
                    <Button size="sm" icon={<Download className="w-4 h-4" />}
                      onClick={() => downloadBlob(state)} className="flex-1">
                      Download
                    </Button>
                  ) : (
                    <Button size="sm" className="flex-1"
                      disabled={isGenerating}
                      icon={isGenerating
                        ? <Loader2 className="w-4 h-4 animate-spin" />
                        : <FileText className="w-4 h-4" />}
                      onClick={() => generate.mutate({ type: config.type })}>
                      {isGenerating ? 'Generating…' : `Generate ${format.toUpperCase()}`}
                    </Button>
                  )}
                </div>
              </Card>
            )
          })}
        </div>

        {/* Info box */}
        <Card className="border-brand-200 dark:border-brand-800 bg-brand-50/50 dark:bg-brand-900/10">
          <div className="flex gap-4">
            <Shield className="w-5 h-5 text-brand-600 dark:text-brand-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-brand-800 dark:text-brand-300 mb-1">AI-Enhanced Reports</p>
              <p className="text-sm text-brand-600 dark:text-brand-400">
                Reports include AI-generated executive summaries and prioritised remediation recommendations.
                Run the AI Security Analyst via the API before generating reports to include detailed threat analysis.
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
