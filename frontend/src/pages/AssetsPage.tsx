import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { assetsApi } from '@/api'
import { TopBar } from '@/components/layout/TopBar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Table } from '@/components/ui/Table'
import { Pagination } from '@/components/ui/Pagination'
import { Modal } from '@/components/ui/Modal'
import { EmptyState } from '@/components/ui/EmptyState'
import { usePermission } from '@/hooks/usePermission'
import { useDebounce } from '@/hooks/useDebounce'
import { Server, Plus, Search, Radar, Trash2, ExternalLink } from 'lucide-react'
import type { Asset, Criticality } from '@/types'
import { formatDistanceToNow } from 'date-fns'

const LIMIT = 20

export function AssetsPage() {
  const qc = useQueryClient()
  const { canWrite, isAdmin } = usePermission()
  const [offset, setOffset]       = useState(0)
  const [search, setSearch]       = useState('')
  const [criticality, setCrit]    = useState('')
  const [showAdd, setShowAdd]     = useState(false)
  const [showDiscover, setShowDiscover] = useState(false)
  const [selected, setSelected]   = useState<Asset | null>(null)
  const [cidr, setCidr]           = useState('')
  const [newAsset, setNewAsset]   = useState({ ip_address: '', hostname: '', criticality: 'medium' as Criticality })

  const debouncedSearch = useDebounce(search)

  const { data, isLoading } = useQuery({
    queryKey: ['assets', offset, debouncedSearch, criticality],
    queryFn: () => assetsApi.list({ limit: LIMIT, offset, search: debouncedSearch || undefined, criticality: criticality || undefined }),
  })

  const createAsset = useMutation({
    mutationFn: () => assetsApi.create(newAsset),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['assets'] }); setShowAdd(false); setNewAsset({ ip_address: '', hostname: '', criticality: 'medium' }) },
  })

  const discover = useMutation({
    mutationFn: () => assetsApi.discover(cidr),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['assets'] }); setShowDiscover(false); setCidr('') },
  })

  const deleteAsset = useMutation({
    mutationFn: (id: string) => assetsApi.delete(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['assets'] }); setSelected(null) },
  })

  const columns = [
    { key: 'hostname', header: 'Host', render: (a: Asset) => (
      <div>
        <p className="font-medium text-gray-900 dark:text-white text-sm">{a.hostname ?? '—'}</p>
        <p className="text-xs text-gray-400 font-mono">{a.ip_address}</p>
      </div>
    )},
    { key: 'asset_type', header: 'Type', render: (a: Asset) => (
      <span className="text-sm capitalize text-gray-600 dark:text-gray-400">{a.asset_type.replace('_', ' ')}</span>
    )},
    { key: 'criticality', header: 'Criticality', render: (a: Asset) => (
      <Badge variant={a.criticality}>{a.criticality}</Badge>
    )},
    { key: 'os_fingerprint', header: 'OS', render: (a: Asset) => (
      <span className="text-xs text-gray-500 dark:text-gray-400">{a.os_fingerprint ?? 'Unknown'}</span>
    )},
    { key: 'last_seen_at', header: 'Last Seen', render: (a: Asset) => (
      <span className="text-xs text-gray-400">
        {a.last_seen_at ? formatDistanceToNow(new Date(a.last_seen_at), { addSuffix: true }) : 'Never'}
      </span>
    )},
    { key: 'actions', header: '', render: (a: Asset) => (
      <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
        <Button variant="ghost" size="sm" icon={<ExternalLink className="w-3.5 h-3.5" />}
          onClick={() => setSelected(a)} />
        {isAdmin && (
          <Button variant="ghost" size="sm" icon={<Trash2 className="w-3.5 h-3.5 text-red-400" />}
            onClick={() => deleteAsset.mutate(a.id)} />
        )}
      </div>
    )},
  ]

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Assets" subtitle={`${data?.total ?? 0} assets monitored`}
        actions={canWrite ? (
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" icon={<Radar className="w-4 h-4" />} onClick={() => setShowDiscover(true)}>Discover</Button>
            <Button size="sm" icon={<Plus className="w-4 h-4" />} onClick={() => setShowAdd(true)}>Add Asset</Button>
          </div>
        ) : undefined}
      />

      <div className="flex-1 p-6 space-y-4 overflow-y-auto">
        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <div className="flex-1 min-w-[200px]">
            <Input placeholder="Search by hostname or IP…" value={search}
              onChange={e => { setSearch(e.target.value); setOffset(0) }}
              icon={<Search className="w-4 h-4" />} />
          </div>
          <Select value={criticality} onChange={e => { setCrit(e.target.value); setOffset(0) }}
            options={[
              { value: '', label: 'All Criticality' },
              { value: 'critical', label: 'Critical' },
              { value: 'high', label: 'High' },
              { value: 'medium', label: 'Medium' },
              { value: 'low', label: 'Low' },
            ]} />
        </div>

        <Card padding={false}>
          {data?.items.length === 0 && !isLoading ? (
            <EmptyState icon={<Server className="w-8 h-8" />} title="No assets found"
              description={search ? 'Try adjusting your search.' : 'Add assets manually or run a discovery scan.'}
              action={canWrite ? { label: 'Add Asset', onClick: () => setShowAdd(true) } : undefined} />
          ) : (
            <>
              <Table columns={columns} data={data?.items ?? []} loading={isLoading}
                onRowClick={setSelected} />
              <div className="px-4">
                <Pagination total={data?.total ?? 0} limit={LIMIT} offset={offset} onChange={setOffset} />
              </div>
            </>
          )}
        </Card>
      </div>

      {/* Add asset modal */}
      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Asset">
        <div className="space-y-4">
          <Input label="IP Address" value={newAsset.ip_address} required
            onChange={e => setNewAsset(a => ({ ...a, ip_address: e.target.value }))} placeholder="10.0.0.1" />
          <Input label="Hostname (optional)" value={newAsset.hostname}
            onChange={e => setNewAsset(a => ({ ...a, hostname: e.target.value }))} placeholder="web-server-01" />
          <Select label="Criticality" value={newAsset.criticality}
            onChange={e => setNewAsset(a => ({ ...a, criticality: e.target.value as Criticality }))}
            options={[
              { value: 'critical', label: 'Critical' }, { value: 'high', label: 'High' },
              { value: 'medium', label: 'Medium' },     { value: 'low', label: 'Low' },
            ]} />
          <div className="flex gap-3 pt-2">
            <Button variant="secondary" className="flex-1" onClick={() => setShowAdd(false)}>Cancel</Button>
            <Button className="flex-1" loading={createAsset.isPending} onClick={() => createAsset.mutate()}>Add Asset</Button>
          </div>
        </div>
      </Modal>

      {/* Discovery modal */}
      <Modal open={showDiscover} onClose={() => setShowDiscover(false)} title="Network Discovery">
        <div className="space-y-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Enter a CIDR range to scan for live hosts.</p>
          <Input label="CIDR Range" value={cidr} onChange={e => setCidr(e.target.value)}
            placeholder="192.168.1.0/24" hint="e.g. 10.0.0.0/24 — max /24" />
          <div className="flex gap-3 pt-2">
            <Button variant="secondary" className="flex-1" onClick={() => setShowDiscover(false)}>Cancel</Button>
            <Button className="flex-1" loading={discover.isPending} onClick={() => discover.mutate()}>Start Discovery</Button>
          </div>
        </div>
      </Modal>

      {/* Asset detail modal */}
      <Modal open={!!selected} onClose={() => setSelected(null)} title="Asset Detail" size="lg">
        {selected && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              {[
                ['IP Address', selected.ip_address],
                ['Hostname', selected.hostname ?? '—'],
                ['Type', selected.asset_type.replace('_', ' ')],
                ['OS', selected.os_fingerprint ?? 'Unknown'],
                ['Criticality', selected.criticality],
                ['Status', selected.is_active ? 'Active' : 'Inactive'],
                ['Last Seen', selected.last_seen_at ? formatDistanceToNow(new Date(selected.last_seen_at), { addSuffix: true }) : 'Never'],
                ['Added', new Date(selected.created_at).toLocaleDateString()],
              ].map(([k, v]) => (
                <div key={k}>
                  <p className="text-xs text-gray-400 mb-0.5">{k}</p>
                  <p className="font-medium text-gray-900 dark:text-white capitalize">{v}</p>
                </div>
              ))}
            </div>
            {selected.ports && selected.ports.length > 0 && (
              <div>
                <p className="text-xs text-gray-400 mb-2">Open Ports</p>
                <div className="flex flex-wrap gap-2">
                  {selected.ports.map(p => (
                    <span key={p.id} className="px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-xs font-mono">
                      {p.port}/{p.protocol} {p.service && `(${p.service})`}
                    </span>
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
