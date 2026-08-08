/**
 * AboutPage.tsx — /about
 * Honest "about" page for an open-source project.
 * No invented team size, funding, or milestones.
 */
import { Link } from "react-router-dom";
import {
  Shield, Github, Brain, Radar, Wrench,
  FileText, Target, BarChart2,
} from "lucide-react";

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
      <footer className="border-t border-slate-800/40 py-6 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-slate-600 text-xs">© {new Date().getFullYear()} VulnAssess</p>
          <div className="flex items-center gap-4">
            <Link to="/privacy" className="text-slate-700 hover:text-slate-500 text-xs transition-colors">Privacy</Link>
            <Link to="/terms"   className="text-slate-700 hover:text-slate-500 text-xs transition-colors">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

const stack = [
  { label: "FastAPI + asyncpg",  desc: "Async Python API with PostgreSQL"       },
  { label: "React + Vite + TS",  desc: "Fast, typed frontend build"             },
  { label: "Groq llama3-70b",    desc: "AI analysis and remediation generation" },
  { label: "Celery + Redis",     desc: "Async scan task queue"                  },
  { label: "Alembic",            desc: "Database migrations"                    },
  { label: "NVD API",            desc: "CVE and CVSS data enrichment"           },
];

const capabilities = [
  { icon: Radar,     color: "text-blue-400",   label: "Asset Discovery"          },
  { icon: Target,    color: "text-orange-400", label: "Vulnerability Scanning"   },
  { icon: Brain,     color: "text-purple-400", label: "AI Risk Analysis"         },
  { icon: BarChart2, color: "text-yellow-400", label: "CVSS Prioritization"      },
  { icon: Wrench,    color: "text-emerald-400",label: "Remediation Guidance"     },
  { icon: FileText,  color: "text-rose-400",   label: "Automated Reporting"      },
];

export default function AboutPage() {
  return (
    <PageShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">

        {/* Header */}
        <div className="mb-14">
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight mb-5">
            About VulnAssess
          </h1>
          <p className="text-slate-400 text-lg leading-relaxed mb-4">
            VulnAssess is an open-source, AI-powered vulnerability assessment platform
            built for startups and small security teams who need serious security tooling
            without the enterprise price tag or the complexity.
          </p>
          <p className="text-slate-400 text-lg leading-relaxed">
            The platform automates the full assessment lifecycle: asset discovery,
            vulnerability scanning, AI-powered risk analysis, remediation guidance,
            and report generation — all in one place.
          </p>
        </div>

        {/* Why it exists */}
        <div className="bg-slate-900/40 border border-slate-800/50 rounded-2xl p-6 mb-10">
          <h2 className="text-white font-bold text-xl mb-3">Why it exists</h2>
          <p className="text-slate-400 text-sm leading-relaxed mb-3">
            Most security scanners are built for large enterprise teams. They produce
            massive reports full of noise, require significant expertise to interpret,
            and offer no guidance on what to actually do next.
          </p>
          <p className="text-slate-400 text-sm leading-relaxed">
            Small teams — a two-person startup, a solo developer running infrastructure,
            a small DevOps team — need a tool that tells them: here are the vulnerabilities
            that actually matter, here's the risk, and here's exactly how to fix it.
            VulnAssess is that tool.
          </p>
        </div>

        {/* Capabilities */}
        <div className="mb-10">
          <h2 className="text-white font-bold text-xl mb-5">What it does</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {capabilities.map((c) => {
              const Icon = c.icon;
              return (
                <div key={c.label} className="flex items-center gap-3 bg-slate-900/40 border border-slate-800/50 rounded-xl p-3.5">
                  <Icon className={`w-4 h-4 flex-shrink-0 ${c.color}`} strokeWidth={1.75} />
                  <span className="text-sm text-slate-300 font-medium">{c.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Stack */}
        <div className="mb-10">
          <h2 className="text-white font-bold text-xl mb-5">Technology stack</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {stack.map((s) => (
              <div key={s.label} className="flex items-start gap-3 bg-slate-900/40 border border-slate-800/50 rounded-xl p-4">
                <code className="text-blue-300 font-mono text-xs bg-blue-500/10 px-2 py-1 rounded flex-shrink-0">
                  {s.label}
                </code>
                <span className="text-slate-400 text-sm">{s.desc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Open source */}
        <div className="bg-blue-500/8 border border-blue-500/20 rounded-2xl p-6">
          <div className="flex items-start gap-4">
            <Github className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <h2 className="text-white font-bold text-base mb-2">Open source</h2>
              <p className="text-slate-400 text-sm leading-relaxed mb-4">
                VulnAssess is fully open source. Inspect the code, self-host it,
                contribute improvements, or fork it for your own use.
              </p>
              <a
                href="https://github.com/sjashwant21/vuln-platform"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors"
              >
                <Github className="w-4 h-4" />
                github.com/sjashwant21/vuln-platform
              </a>
            </div>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
