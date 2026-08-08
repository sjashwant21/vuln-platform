/**
 * SecurityPage.tsx — /security
 * Honest security posture page. No fake certifications.
 * Content grounded in facts from the repo: JWT, MFA, bcrypt, rate limiting,
 * HSTS in production, secrets management via env vars, TLS via nginx.
 */
import { Link } from "react-router-dom";
import { Shield, Lock, Key, Server, AlertTriangle, Mail, Code2 } from "lucide-react";

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-white antialiased">
      <div className="fixed inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_90%_40%_at_50%_-10%,rgba(59,130,246,0.06),transparent)]" />
      </div>
      <nav className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500/30 rounded-md blur-sm" />
              <div className="relative bg-gradient-to-br from-blue-500 to-blue-700 rounded-md p-1">
                <Shield className="w-4 h-4 text-white" strokeWidth={2.5} />
              </div>
            </div>
            <span className="text-white font-bold text-base tracking-tight">Vuln<span className="text-blue-400">Assess</span></span>
          </Link>
          <div className="flex items-center gap-4">
            <Link to="/" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">← Home</Link>
          </div>
        </div>
      </nav>
      <main className="relative">{children}</main>
      <footer className="border-t border-slate-800/40 py-6 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-slate-600 text-xs">© {new Date().getFullYear()} VulnAssess</p>
          <div className="flex items-center gap-4">
            <Link to="/privacy" className="text-slate-700 hover:text-slate-500 text-xs">Privacy</Link>
            <Link to="/terms"   className="text-slate-700 hover:text-slate-500 text-xs">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

const measures = [
  {
    icon: Key,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    title: "Authentication & Session Management",
    items: [
      "JWT HS256 with short-lived access tokens (15 min) and refresh tokens (7 days)",
      "bcrypt password hashing with configurable rounds (default: 12)",
      "Optional multi-factor authentication (MFA) per account",
      "Rate limiting on all authentication endpoints (60 req/min default)",
    ],
  },
  {
    icon: Server,
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    title: "Infrastructure Security",
    items: [
      "TLS termination via nginx with certificates mounted at nginx/ssl",
      "HSTS and security headers applied when APP_ENV=production",
      "Secrets managed via environment variables, never committed to VCS",
      "PostgreSQL with connection pooling (asyncpg) and parameterized queries",
    ],
  },
  {
    icon: Lock,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    title: "Data Protection",
    items: [
      "Scan data is tenant-isolated at the database level",
      "API keys and secrets stored encrypted, never in logs",
      "Structured JSON logging via structlog with configurable log levels",
      "No sensitive data in JWT payload beyond user ID and role",
    ],
  },
  {
    icon: Code2,
    color: "text-orange-400",
    bg: "bg-orange-500/10",
    title: "Application Security",
    items: [
      "FastAPI input validation via Pydantic models on all endpoints",
      "CORS restricted to configured CORS_ORIGINS environment variable",
      "Celery background workers isolated from API process",
      "Docker containers run with minimal required permissions",
    ],
  },
];

export default function SecurityPage() {
  return (
    <PageShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="mb-14">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-blue-400" />
            <span className="text-blue-400 text-sm font-semibold uppercase tracking-widest">Security</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight mb-4">
            Our security posture
          </h1>
          <p className="text-slate-400 text-lg leading-relaxed">
            VulnAssess is an open-source platform. This page documents the security
            controls we implement and how we handle vulnerabilities in the platform itself.
            We do not claim certifications we haven't earned.
          </p>
        </div>

        {/* Measures */}
        <div className="space-y-6 mb-16">
          {measures.map((m) => {
            const Icon = m.icon;
            return (
              <div key={m.title} className="bg-slate-900/40 border border-slate-800/50 rounded-2xl p-6">
                <div className="flex items-start gap-4">
                  <div className={`flex-shrink-0 p-2.5 rounded-xl ${m.bg}`}>
                    <Icon className={`w-5 h-5 ${m.color}`} strokeWidth={1.75} />
                  </div>
                  <div className="flex-1">
                    <h2 className="text-white font-bold text-base mb-3">{m.title}</h2>
                    <ul className="space-y-2">
                      {m.items.map((item) => (
                        <li key={item} className="flex items-start gap-2.5">
                          <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-slate-600 mt-1.5" />
                          <span className="text-slate-400 text-sm leading-relaxed">{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Disclosure */}
        <div className="bg-orange-500/8 border border-orange-500/20 rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <AlertTriangle className="w-5 h-5 text-orange-400 flex-shrink-0 mt-0.5" />
            <div>
              <h2 className="text-white font-bold text-base mb-2">Responsible Disclosure</h2>
              <p className="text-slate-400 text-sm leading-relaxed mb-4">
                If you discover a security vulnerability in VulnAssess, please report it
                responsibly. Do not open a public GitHub issue for security vulnerabilities.
                Contact the maintainer directly.
              </p>
              <div className="flex flex-col sm:flex-row gap-3">
                <a href="https://github.com/sjashwant21/vuln-platform/security" target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-orange-600/80 hover:bg-orange-600 transition-colors">
                  <Shield className="w-4 h-4" />
                  GitHub Security Advisories
                </a>
                <a href="mailto:109244010+sjashwant21@users.noreply.github.com"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-slate-300 border border-slate-700 hover:border-slate-600 hover:text-white transition-colors">
                  <Mail className="w-4 h-4" />
                  Email maintainer
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
