/**
 * DocsPage.tsx — /docs (public-facing documentation index)
 * Links to the real FastAPI Swagger UI at /docs (served by the backend).
 * This page is shown when visiting the frontend route /docs.
 *
 * Stack facts from repo:
 *   API base path: /v1
 *   Swagger UI:    /docs  (served by uvicorn/FastAPI)
 *   Health:        /health
 *   Auth:          JWT HS256, /v1/auth/login, /v1/auth/refresh
 *   AI provider:   Groq llama3-70b-8192
 *   Reports:       DOCX, HTML, charts
 */

import { Link } from "react-router-dom";
import {
  Shield, FileText, Cpu, Lock, Activity,
  ArrowRight, ExternalLink, Terminal,
  BookOpen, Code2, Zap, Database, RefreshCw,
} from "lucide-react";

// ── Shared layout shell used by all sub-pages ────────────────────────────────
function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-white antialiased">
      {/* ambient glow */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_90%_40%_at_50%_-10%,rgba(59,130,246,0.06),transparent)]" />
      </div>

      {/* Simple top-bar nav */}
      <nav className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500/30 rounded-md blur-sm" />
              <div className="relative bg-gradient-to-br from-blue-500 to-blue-700 rounded-md p-1">
                <Shield className="w-4 h-4 text-white" strokeWidth={2.5} />
              </div>
            </div>
            <span className="text-white font-bold text-base tracking-tight">
              Vuln<span className="text-blue-400">Assess</span>
            </span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">← Home</Link>
            <Link to="/register" className="px-4 py-1.5 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 transition-colors">
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative">{children}</main>

      {/* Minimal footer */}
      <footer className="border-t border-slate-800/40 py-6 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-slate-600 text-xs">© {new Date().getFullYear()} VulnAssess</p>
          <div className="flex items-center gap-4">
            <Link to="/privacy" className="text-slate-700 hover:text-slate-500 text-xs transition-colors">Privacy</Link>
            <Link to="/terms"   className="text-slate-700 hover:text-slate-500 text-xs transition-colors">Terms</Link>
            <a href="https://github.com/sjashwant21/vuln-platform" target="_blank" rel="noopener noreferrer"
              className="text-slate-700 hover:text-slate-500 text-xs transition-colors">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}

// ── Docs sections ────────────────────────────────────────────────────────────
const sections = [
  {
    icon: Zap,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    title: "Quick Start",
    desc: "Create an account, add a target domain or IP, and run your first scan. Results appear within minutes.",
    links: [
      { label: "Create your account", to: "/register" },
      { label: "API interactive explorer", href: "/docs" },
    ],
  },
  {
    icon: Lock,
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    title: "Authentication",
    desc: "VulnAssess uses JWT (HS256). Access tokens expire in 15 minutes; use the refresh token endpoint for long-lived sessions. Optional MFA is available.",
    links: [
      { label: "POST /v1/auth/login",   href: "/docs#/auth/login"   },
      { label: "POST /v1/auth/refresh", href: "/docs#/auth/refresh" },
    ],
  },
  {
    icon: Terminal,
    color: "text-cyan-400",
    bg: "bg-cyan-500/10",
    title: "Scanning API",
    desc: "Submit scan targets via the REST API. Scans run asynchronously via Celery workers. Poll the scan status endpoint or use webhooks.",
    links: [
      { label: "POST /v1/scans",       href: "/docs#/scans/create" },
      { label: "GET  /v1/scans/{id}",  href: "/docs#/scans/get"    },
    ],
  },
  {
    icon: Cpu,
    color: "text-orange-400",
    bg: "bg-orange-500/10",
    title: "AI Analysis",
    desc: "Every finding is enriched by Groq (llama3-70b-8192) with plain-language explanations, risk context, and environment-specific remediation. Configurable via GROQ_MODEL env var.",
    links: [
      { label: "GET /v1/findings/{id}/ai-analysis", href: "/docs#/findings/ai" },
    ],
  },
  {
    icon: FileText,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    title: "Reports",
    desc: "Generate executive (PDF) and technical (DOCX/HTML) reports via the reports API. Reports include severity distribution, CVSS scores, asset lists, and AI-generated summaries.",
    links: [
      { label: "POST /v1/reports",       href: "/docs#/reports/create" },
      { label: "GET  /v1/reports/{id}",  href: "/docs#/reports/get"    },
    ],
  },
  {
    icon: Database,
    color: "text-yellow-400",
    bg: "bg-yellow-500/10",
    title: "CVE Intelligence",
    desc: "Findings are automatically enriched via the NVD API (NVD_API_KEY). Each CVE includes CVSS v3 score, CWE, affected versions, and known exploit status.",
    links: [
      { label: "GET /v1/cves/{cve_id}", href: "/docs#/cves/get" },
      { label: "NVD API reference",     href: "https://nvd.nist.gov/developers/vulnerabilities" },
    ],
  },
  {
    icon: Activity,
    color: "text-rose-400",
    bg: "bg-rose-500/10",
    title: "Health & Status",
    desc: "Monitor the API and background workers. The /health endpoint returns system status, database connectivity, and Redis/Celery worker availability.",
    links: [
      { label: "GET /health", href: "/health" },
      { label: "GET /v1/status/workers", href: "/docs#/status/workers" },
    ],
  },
  {
    icon: RefreshCw,
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
    title: "Self-Hosting",
    desc: "Run VulnAssess on your own infrastructure with Docker Compose. Requires PostgreSQL, Redis, and a Groq API key. See the GitHub repo for full setup instructions.",
    links: [
      { label: "GitHub — docker-compose.yml", href: "https://github.com/sjashwant21/vuln-platform/blob/main/docker-compose.yml" },
      { label: "Environment variables reference", href: "https://github.com/sjashwant21/vuln-platform/blob/main/.env.example" },
    ],
  },
];

export default function DocsPage() {
  return (
    <PageShell>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">

        {/* Header */}
        <div className="max-w-3xl mb-14">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-5 h-5 text-blue-400" />
            <span className="text-blue-400 text-sm font-semibold uppercase tracking-widest">Documentation</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight mb-4">VulnAssess Docs</h1>
          <p className="text-slate-400 text-lg leading-relaxed mb-6">
            Everything you need to integrate, scan, and automate with VulnAssess.
            The interactive API explorer is served directly by the backend at{" "}
            <code className="text-blue-300 bg-slate-800 px-1.5 py-0.5 rounded text-sm">/docs</code>.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <a href="/docs"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-500 transition-colors">
              <Code2 className="w-4 h-4" />
              Open API Explorer
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <a href="/health"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-300 border border-slate-700/60 hover:border-slate-600 hover:text-white transition-colors">
              <Activity className="w-4 h-4" />
              Check API Health
            </a>
          </div>
        </div>

        {/* Base URL callout */}
        <div className="bg-slate-900/50 border border-slate-800/50 rounded-xl p-4 mb-12 flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex-shrink-0">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">API Base URL</span>
            <code className="text-emerald-300 font-mono text-sm">https://your-deployment.railway.app/v1</code>
          </div>
          <div className="w-px h-8 bg-slate-800 hidden sm:block" />
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Interactive Docs</span>
            <a href="/docs" className="text-blue-400 hover:text-blue-300 font-mono text-sm transition-colors">/docs (Swagger UI)</a>
          </div>
          <div className="w-px h-8 bg-slate-800 hidden sm:block" />
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block mb-1">Health Endpoint</span>
            <a href="/health" className="text-blue-400 hover:text-blue-300 font-mono text-sm transition-colors">/health</a>
          </div>
        </div>

        {/* Sections grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {sections.map((s) => {
            const Icon = s.icon;
            return (
              <div key={s.title} className="bg-slate-900/40 border border-slate-800/50 hover:border-slate-700/60 rounded-2xl p-5 transition-colors">
                <div className={`inline-flex p-2.5 rounded-xl ${s.bg} mb-4`}>
                  <Icon className={`w-5 h-5 ${s.color}`} strokeWidth={1.75} />
                </div>
                <h2 className="text-white font-bold text-base mb-2">{s.title}</h2>
                <p className="text-slate-400 text-sm leading-relaxed mb-4">{s.desc}</p>
                <ul className="space-y-1.5">
                  {s.links.map((l) =>
                    "to" in l ? (
                      <li key={l.label}>
                        <Link to={l.to as string} className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors font-mono">
                          <ArrowRight className="w-3 h-3 flex-shrink-0" />{l.label}
                        </Link>
                      </li>
                    ) : (
                      <li key={l.label}>
                        <a href={l.href} target={l.href?.startsWith("http") ? "_blank" : undefined}
                          rel={l.href?.startsWith("http") ? "noopener noreferrer" : undefined}
                          className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors font-mono">
                          <ArrowRight className="w-3 h-3 flex-shrink-0" />{l.label}
                        </a>
                      </li>
                    )
                  )}
                </ul>
              </div>
            );
          })}
        </div>
      </div>
    </PageShell>
  );
}
