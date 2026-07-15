import { apiClient } from '@/lib/axios'
import type {
  Asset, AssetListResponse, AuthTokens, CorrelateRequest, CorrelationReport,
  DashboardSummary, HealthScore, Organization, PaginationParams,
  ReportFormat, ReportType, ScanFinding, ScanJob, User,
  VulnListResponse, VulnStatus, Vulnerability, RemediationPlan,
} from '@/types'
export const authApi = {
  login: (email: string, password: string) =>
    apiClient.post<AuthTokens>('/auth/login', { email, password }).then(r => r.data),
  register: (p: { email: string; password: string; full_name: string; organization_name: string; organization_slug: string }) =>
    apiClient.post<{ user: User; organization: Organization; tokens: AuthTokens }>('/auth/register', p).then(r => r.data),
  logout: (refresh_token: string) => apiClient.post('/auth/logout', { refresh_token }),
  me: () => apiClient.get<{ user_id: string; org_id: string; role: string; email: string }>('/auth/me').then(r => r.data),
  changePassword: (current_password: string, new_password: string) =>
    apiClient.post('/auth/change-password', { current_password, new_password }).then(r => r.data),
}
export const usersApi = {
  me: () => apiClient.get<User>('/users/me').then(r => r.data),
  updateProfile: (data: { full_name?: string }) => apiClient.patch<User>('/users/me', data).then(r => r.data),
  list: (params?: PaginationParams) => apiClient.get<{ items: User[]; total: number }>('/users', { params }).then(r => r.data),
  changeRole: (id: string, role: string) => apiClient.patch<User>(`/users/${id}/role`, { role }).then(r => r.data),
  deactivate: (id: string) => apiClient.delete(`/users/${id}`),
}
export const orgApi = {
  me: () => apiClient.get<Organization>('/organizations/me').then(r => r.data),
  update: (data: { name?: string }) => apiClient.patch<Organization>('/organizations/me', data).then(r => r.data),
}
export const assetsApi = {
  list: (params?: PaginationParams & { criticality?: string; search?: string }) =>
    apiClient.get<AssetListResponse>('/assets', { params }).then(r => r.data),
  get: (id: string) => apiClient.get<Asset>(`/assets/${id}`).then(r => r.data),
  create: (data: Partial<Asset>) => apiClient.post<Asset>('/assets', data).then(r => r.data),
  update: (id: string, data: Partial<Asset>) => apiClient.patch<Asset>(`/assets/${id}`, data).then(r => r.data),
  delete: (id: string) => apiClient.delete(`/assets/${id}`),
  discover: (cidr: string) => apiClient.post<ScanJob>('/assets/discover', { cidr }).then(r => r.data),
}
export const scansApi = {
  list: (params?: PaginationParams & { status?: string }) =>
    apiClient.get<{ items: ScanJob[]; total: number }>('/scans', { params }).then(r => r.data),
  get: (id: string) => apiClient.get<ScanJob>(`/scans/${id}`).then(r => r.data),
  create: (data: { scan_type: string; target_ips: string[] }) =>
    apiClient.post<ScanJob>('/scans', data).then(r => r.data),
  cancel: (id: string) => apiClient.post(`/scans/${id}/cancel`),
  findings: (id: string) => apiClient.get<ScanFinding[]>(`/scans/${id}/findings`).then(r => r.data),
}
export const vulnsApi = {
  list: (params?: PaginationParams & { severity?: string; status?: string; asset_id?: string }) =>
    apiClient.get<VulnListResponse>('/vulnerabilities', { params }).then(r => r.data),
  get: (id: string) => apiClient.get<Vulnerability>(`/vulnerabilities/${id}`).then(r => r.data),
  updateStatus: (id: string, status: VulnStatus, reason?: string) =>
    apiClient.patch<Vulnerability>(`/vulnerabilities/${id}/status`, { status, reason }).then(r => r.data),
  getRemediation: (id: string) =>
    apiClient.get<RemediationPlan>(`/vulnerabilities/${id}/remediation`).then(r => r.data),
  generateRemediation: (id: string) =>
    apiClient.post<RemediationPlan>(`/vulnerabilities/${id}/remediation`).then(r => r.data),
}
export const dashboardApi = {
  summary: () => apiClient.get<DashboardSummary>('/dashboard/summary').then(r => r.data),
  healthScore: () => apiClient.get<HealthScore>('/dashboard/health-score').then(r => r.data),
}
export const intelligenceApi = {
  correlate: (data: CorrelateRequest) =>
    apiClient.post<CorrelationReport>('/intelligence/correlate', data).then(r => r.data),
  getCve: (id: string) => apiClient.get(`/intelligence/cve/${id}`).then(r => r.data),
}
export const reportsApi = {
  generate: async (params: { report_type: ReportType; report_format: ReportFormat; period_days?: number }) => {
    const res = await apiClient.post('/reports/generate', params, { responseType: 'blob', timeout: 120_000 })
    const disp = res.headers['content-disposition'] ?? ''
    const match = disp.match(/filename="(.+)"/)
    return { blob: res.data as Blob, filename: match?.[1] ?? `report.${params.report_format}` }
  },
}
