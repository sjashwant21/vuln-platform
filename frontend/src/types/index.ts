export type UserRole = 'owner' | 'admin' | 'analyst' | 'viewer'
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'
export type VulnStatus = 'open' | 'in_progress' | 'resolved' | 'accepted_risk' | 'false_positive'
export type ScanStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'timeout'
export type ScanType = 'discovery' | 'port_scan' | 'service_enum' | 'vulnerability' | 'cve_correlation'
export type AssetType = 'server' | 'workstation' | 'network_device' | 'iot' | 'cloud_instance' | 'container' | 'unknown'
export type Criticality = 'critical' | 'high' | 'medium' | 'low'
export type ReportType = 'executive' | 'technical' | 'vulnerability' | 'compliance'
export type ReportFormat = 'pdf' | 'docx'

export interface User {
  id: string; email: string; full_name: string; role: UserRole
  org_id: string; mfa_enabled: boolean; email_verified: boolean
  created_at: string; last_login_at: string | null
}
export interface Organization {
  id: string; name: string; slug: string
  plan_tier: 'free' | 'starter' | 'professional' | 'enterprise'
  max_assets: number; max_users: number; max_concurrent_scans: number
  is_active: boolean; created_at: string
}
export interface AuthTokens {
  access_token: string; refresh_token: string; token_type: string; expires_in: number
}
export interface Asset {
  id: string; organization_id: string; hostname: string | null
  ip_address: string; asset_type: AssetType; os_fingerprint: string | null
  criticality: Criticality; tags: Record<string, string>
  is_active: boolean; last_seen_at: string | null
  created_at: string; updated_at: string
  ports?: AssetPort[]
}
export interface AssetPort {
  id: string; port: number; protocol: string; service: string | null
  service_version: string | null; state: string; scanned_at: string
}
export interface AssetListResponse { items: Asset[]; total: number; limit: number; offset: number }
export interface ScanJob {
  id: string; organization_id: string; scan_type: ScanType; status: ScanStatus
  target_ips: string[]; started_at: string | null; completed_at: string | null
  created_at: string; error_message: string | null
  result_summary: { hosts_discovered?: number; ports_scanned?: number; vulnerabilities_found?: number; duration_seconds?: number }
}
export interface ScanFinding {
  id: string; scan_job_id: string; asset_id: string; port: number | null
  severity: Severity; title: string; description: string
  evidence: string | null; cve_ids: string[]; cvss_score: number | null; created_at: string
}
export interface Vulnerability {
  id: string; organization_id: string; asset_id: string; cve_id: string | null
  title: string; description: string; severity: Severity; cvss_score: number | null
  risk_score: number | null; status: VulnStatus; port: number | null
  service: string | null; notes: string | null; detected_at: string
  resolved_at: string | null; updated_at: string
  asset?: Pick<Asset, 'id' | 'hostname' | 'ip_address' | 'criticality'>
}
export interface VulnListResponse { items: Vulnerability[]; total: number; limit: number; offset: number }
export interface RemediationPlan {
  id: string; vulnerability_id: string; ai_model: string
  recommendation_markdown: string; structured_steps: Record<string, unknown>
  confidence_score: number | null; accepted: boolean; generated_at: string
}
export interface DashboardSummary {
  total_assets: number; total_vulnerabilities: number; open_vulnerabilities: number
  critical_count: number; high_count: number; medium_count: number; low_count: number
  recent_scans: ScanJob[]
}
export interface HealthScore {
  score: number; label: string; grade: string
  critical: number; high: number; medium: number; low: number
  trend: Array<{ date: string; score: number }>
}
export interface CorrelateRequest {
  service: string; version: string; asset_criticality: Criticality
  internet_exposed: boolean; max_results?: number
}
export interface CVEMatch {
  cve_id: string
  cve: { cve_id: string; description: string; severity: Severity; base_score: number | null; has_public_exploit: boolean; has_patch: boolean; published_at: string | null }
  risk_score: number; confidence: number; match_method: string; severity: Severity
}
export interface CorrelationReport {
  service: string; version: string; total_findings: number
  max_risk_score: number; has_exploitable: boolean
  severity_breakdown: Record<string, number>; matches: CVEMatch[]
}
export interface ApiError { error: string; detail: string | null }
export interface PaginationParams { limit?: number; offset?: number }
