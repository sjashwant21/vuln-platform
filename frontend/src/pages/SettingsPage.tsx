import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usersApi, orgApi, authApi } from '@/api'
import { useAuthStore } from '@/store/auth.store'
import { TopBar } from '@/components/layout/TopBar'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input, Select } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { usePermission } from '@/hooks/usePermission'
import { useTheme } from '@/hooks/useTheme'
import { User, Building2, Users, Lock, Moon, Sun, Trash2, ShieldAlert, Check } from 'lucide-react'
import type { UserRole } from '@/types'

type Tab = 'profile' | 'organisation' | 'team' | 'security' | 'appearance'

export function SettingsPage() {
  const qc               = useQueryClient()
  const { user, setUser } = useAuthStore()
  const { isAdmin, isOwner } = usePermission()
  const { dark, toggle }  = useTheme()
  const [tab, setTab]     = useState<Tab>('profile')

  // Profile
  const [fullName, setFullName]     = useState(user?.full_name ?? '')
  const [profileSaved, setProfileSaved] = useState(false)

  // Password
  const [curPw, setCurPw]     = useState('')
  const [newPw, setNewPw]     = useState('')
  const [pwError, setPwError] = useState('')
  const [pwSaved, setPwSaved] = useState(false)

  // Org
  const [orgName, setOrgName]    = useState('')
  const [orgSaved, setOrgSaved]  = useState(false)

  // Team
  const [roleModal, setRoleModal] = useState<{ id: string; name: string; role: UserRole } | null>(null)
  const [newRole, setNewRole]     = useState<UserRole>('viewer')

  const orgQuery = useQuery({ queryKey: ['org'], queryFn: orgApi.me,
    onSuccess: (o: { name: string }) => setOrgName(o.name) })
  const teamQuery = useQuery({ queryKey: ['team'], queryFn: () => usersApi.list({ limit: 50 }), enabled: isAdmin })

  const updateProfile = useMutation({
    mutationFn: () => usersApi.updateProfile({ full_name: fullName }),
    onSuccess: u => { setUser(u); setProfileSaved(true); setTimeout(() => setProfileSaved(false), 2000) },
  })

  const changePassword = useMutation({
    mutationFn: () => authApi.changePassword(curPw, newPw),
    onSuccess: () => { setCurPw(''); setNewPw(''); setPwSaved(true); setTimeout(() => setPwSaved(false), 2000) },
    onError: () => setPwError('Current password is incorrect'),
  })

  const updateOrg = useMutation({
    mutationFn: () => orgApi.update({ name: orgName }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['org'] }); setOrgSaved(true); setTimeout(() => setOrgSaved(false), 2000) },
  })

  const changeRole = useMutation({
    mutationFn: () => usersApi.changeRole(roleModal!.id, newRole),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['team'] }); setRoleModal(null) },
  })

  const deactivate = useMutation({
    mutationFn: (id: string) => usersApi.deactivate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team'] }),
  })

  const TABS = [
    { id: 'profile',      label: 'Profile',      icon: User,        show: true },
    { id: 'organisation', label: 'Organisation',  icon: Building2,   show: isAdmin },
    { id: 'team',         label: 'Team',          icon: Users,       show: isAdmin },
    { id: 'security',     label: 'Security',      icon: Lock,        show: true },
    { id: 'appearance',   label: 'Appearance',    icon: Moon,        show: true },
  ] as const

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Settings" />
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar nav */}
        <nav className="w-52 shrink-0 border-r border-gray-100 dark:border-gray-800 p-4 space-y-0.5">
          {TABS.filter(t => t.show).map(t => {
            const Icon = t.icon
            return (
              <button key={t.id} onClick={() => setTab(t.id as Tab)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors text-left ${tab === t.id ? 'bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-400' : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800'}`}>
                <Icon className="w-4 h-4" />
                {t.label}
              </button>
            )
          })}
        </nav>

        {/* Content */}
        <div className="flex-1 p-6 overflow-y-auto">
          {/* Profile */}
          {tab === 'profile' && (
            <div className="max-w-lg space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Profile</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">Update your name and account details.</p>
              </div>
              <Card className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center text-brand-700 dark:text-brand-400 text-2xl font-bold">
                    {user?.full_name?.[0]?.toUpperCase() ?? 'U'}
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900 dark:text-white">{user?.full_name}</p>
                    <p className="text-sm text-gray-500">{user?.email}</p>
                    <Badge variant="info" className="mt-1">{user?.role}</Badge>
                  </div>
                </div>
                <Input label="Full Name" value={fullName} onChange={e => setFullName(e.target.value)} />
                <Input label="Email" value={user?.email ?? ''} disabled hint="Contact support to change your email." />
                <Button onClick={() => updateProfile.mutate()} loading={updateProfile.isPending}
                  icon={profileSaved ? <Check className="w-4 h-4" /> : undefined}>
                  {profileSaved ? 'Saved!' : 'Save Changes'}
                </Button>
              </Card>
            </div>
          )}

          {/* Organisation */}
          {tab === 'organisation' && isAdmin && (
            <div className="max-w-lg space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Organisation</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">Manage your organisation settings.</p>
              </div>
              <Card className="space-y-4">
                {orgQuery.data && (
                  <div className="grid grid-cols-2 gap-3 text-sm mb-2">
                    {[
                      ['Plan', orgQuery.data.plan_tier?.toUpperCase()],
                      ['Max Assets', orgQuery.data.max_assets],
                      ['Max Users', orgQuery.data.max_users],
                      ['Slug', orgQuery.data.slug],
                    ].map(([k, v]) => (
                      <div key={String(k)}>
                        <p className="text-xs text-gray-400 mb-0.5">{k}</p>
                        <p className="font-medium text-gray-900 dark:text-white">{v}</p>
                      </div>
                    ))}
                  </div>
                )}
                <Input label="Organisation Name" value={orgName} onChange={e => setOrgName(e.target.value)} />
                <Button onClick={() => updateOrg.mutate()} loading={updateOrg.isPending}
                  icon={orgSaved ? <Check className="w-4 h-4" /> : undefined}>
                  {orgSaved ? 'Saved!' : 'Save Changes'}
                </Button>
              </Card>
            </div>
          )}

          {/* Team */}
          {tab === 'team' && isAdmin && (
            <div className="max-w-2xl space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Team Members</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">{teamQuery.data?.total ?? 0} members in your organisation.</p>
              </div>
              <Card padding={false}>
                <div className="divide-y divide-gray-100 dark:divide-gray-800">
                  {(teamQuery.data?.items ?? []).map(member => (
                    <div key={member.id} className="flex items-center justify-between px-5 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center text-brand-700 dark:text-brand-400 text-sm font-bold">
                          {member.full_name?.[0]?.toUpperCase() ?? 'U'}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-900 dark:text-white">{member.full_name}</p>
                          <p className="text-xs text-gray-400">{member.email}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="info">{member.role}</Badge>
                        {isOwner && member.id !== user?.id && (
                          <>
                            <Button variant="ghost" size="sm"
                              onClick={() => { setRoleModal({ id: member.id, name: member.full_name, role: member.role }); setNewRole(member.role) }}>
                              Change Role
                            </Button>
                            <Button variant="ghost" size="sm" icon={<Trash2 className="w-3.5 h-3.5 text-red-400" />}
                              onClick={() => { if (confirm(`Remove ${member.full_name}?`)) deactivate.mutate(member.id) }} />
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          )}

          {/* Security */}
          {tab === 'security' && (
            <div className="max-w-lg space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Security</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">Manage your password and security settings.</p>
              </div>
              <Card className="space-y-4">
                <h3 className="font-medium text-gray-900 dark:text-white">Change Password</h3>
                <Input label="Current Password" type="password" value={curPw} onChange={e => { setCurPw(e.target.value); setPwError('') }} />
                <Input label="New Password" type="password" value={newPw} onChange={e => setNewPw(e.target.value)}
                  hint="Min 8 chars, one uppercase, one digit" error={pwError} />
                <Button onClick={() => changePassword.mutate()} loading={changePassword.isPending}
                  disabled={!curPw || !newPw}
                  icon={pwSaved ? <Check className="w-4 h-4" /> : undefined}>
                  {pwSaved ? 'Password Updated!' : 'Update Password'}
                </Button>
              </Card>
              <Card className="space-y-3">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-yellow-500" />
                  <h3 className="font-medium text-gray-900 dark:text-white">Multi-Factor Authentication</h3>
                </div>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {user?.mfa_enabled ? 'MFA is enabled on your account.' : 'MFA is not enabled. Enable it to secure your account.'}
                </p>
                <Badge variant={user?.mfa_enabled ? 'resolved' : 'open'}>
                  {user?.mfa_enabled ? 'Enabled' : 'Disabled'}
                </Badge>
              </Card>
            </div>
          )}

          {/* Appearance */}
          {tab === 'appearance' && (
            <div className="max-w-lg space-y-6">
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Appearance</h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">Customise the look and feel of the platform.</p>
              </div>
              <Card>
                <h3 className="font-medium text-gray-900 dark:text-white mb-4">Theme</h3>
                <div className="flex gap-3">
                  {[
                    { id: 'light', label: 'Light', icon: <Sun className="w-5 h-5" /> },
                    { id: 'dark',  label: 'Dark',  icon: <Moon className="w-5 h-5" /> },
                  ].map(t => (
                    <button key={t.id} onClick={() => { if ((t.id === 'dark') !== dark) toggle() }}
                      className={`flex-1 flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all ${(t.id === 'dark') === dark ? 'border-brand-500 bg-brand-50 dark:bg-brand-900/20' : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'}`}>
                      <div className={`${(t.id === 'dark') === dark ? 'text-brand-600 dark:text-brand-400' : 'text-gray-400'}`}>
                        {t.icon}
                      </div>
                      <span className={`text-sm font-medium ${(t.id === 'dark') === dark ? 'text-brand-700 dark:text-brand-400' : 'text-gray-500'}`}>
                        {t.label}
                      </span>
                    </button>
                  ))}
                </div>
              </Card>
            </div>
          )}
        </div>
      </div>

      {/* Role change modal */}
      <Modal open={!!roleModal} onClose={() => setRoleModal(null)} title="Change Role">
        {roleModal && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">Changing role for <strong>{roleModal.name}</strong>.</p>
            <Select label="New Role" value={newRole}
              onChange={e => setNewRole(e.target.value as UserRole)}
              options={[
                { value: 'viewer',  label: 'Viewer — Read-only access' },
                { value: 'analyst', label: 'Analyst — Can run scans and update vulns' },
                { value: 'admin',   label: 'Admin — Full access except billing' },
                { value: 'owner',   label: 'Owner — Full access' },
              ]} />
            <div className="flex gap-3">
              <Button variant="secondary" className="flex-1" onClick={() => setRoleModal(null)}>Cancel</Button>
              <Button className="flex-1" loading={changeRole.isPending} onClick={() => changeRole.mutate()}>Update Role</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
