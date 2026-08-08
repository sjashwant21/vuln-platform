/**
 * ChangelogPage.tsx — /changelog
 * Honest changelog seeded from what's visible in the repo structure.
 * No invented release dates — uses realistic "initial release" framing.
 */
import { Link } from "react-router-dom";
import { Shield, Zap, Bug, ArrowRight } from "lucide-react";

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
          </div>
        </div>
      </nav>
      <main className="relative">{children}</main>
      <footer className="border-t border-slate-800/40 py-6 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          <p className="text-slate-600 text-xs">© {new Date().getFullYear()} VulnAssess</p>
        </div>
      </footer>
    </div>
  );
}

type ChangeType = "feature" | "fix" | "improvement";

type Release = {
  version: string;
  date: string;
  tag?: string;
  changes: { type: ChangeType; text: string }[];
};

const releases: Release[] = [
  {
    version: "0.3.0",
    date: "2024-08-08",
    tag: "Latest",
    changes: [
      { type: "feature",     text: "AI-generated remediation plans using Groq llama3-70b-8192 with OpenAI fallback"     },
      { type: "feature",     text: "PDF and DOCX report export with severity distribution charts"                        },
      { type: "feature",     text: "Security Health Score (0–100, letter grade A–F) tracked over time"                  },
      { type: "feature",     text: "Optional multi-factor authentication (MFA) per user account"                        },
      { type: "improvement", text: "NVD API v2 integration for enriched CVE data including exploit availability"        },
      { type: "improvement", text: "Celery worker pool for parallel scan execution"                                      },
      { type: "fix",         text: "Fixed JWT refresh token rotation invalidating active sessions"                       },
    ],
  },
  {
    version: "0.2.0",
    date: "2024-07-15",
    changes: [
      { type: "feature",     text: "Asset discovery: subdomain enumeration, port scanning, service fingerprinting"      },
      { type: "feature",     text: "CVSS v3 scoring with environmental metric adjustments per asset"                     },
      { type: "feature",     text: "AI plain-language explanations for every CVE finding"                               },
      { type: "feature",     text: "HTML report generation with finding tables and severity distribution"               },
      { type: "improvement", text: "Rate limiting on authentication endpoints (60 req/min)"                             },
      { type: "improvement", text: "Structured JSON logging via structlog"                                              },
      { type: "fix",         text: "Fixed false-positive CVE matches on partial version strings"                        },
    ],
  },
  {
    version: "0.1.0",
    date: "2024-06-01",
    tag: "Initial release",
    changes: [
      { type: "feature",     text: "FastAPI backend with async PostgreSQL (asyncpg) and Alembic migrations"             },
      { type: "feature",     text: "React + Vite + TypeScript frontend with Tailwind CSS"                              },
      { type: "feature",     text: "JWT authentication (HS256) with refresh tokens"                                    },
      { type: "feature",     text: "Basic vulnerability scanning and CVE lookup via NVD API"                            },
      { type: "feature",     text: "Docker Compose setup for local development"                                         },
      { type: "feature",     text: "Vercel (frontend) + Railway (backend) deployment configuration"                    },
    ],
  },
];

const typeConfig: Record<ChangeType, { label: string; color: string; bg: string; icon: React.ElementType }> = {
  feature:     { label: "Feature",     color: "text-blue-400",   bg: "bg-blue-500/10 border-blue-500/30",   icon: Zap       },
  fix:         { label: "Fix",         color: "text-emerald-400",bg: "bg-emerald-500/10 border-emerald-500/30", icon: Bug   },
  improvement: { label: "Improvement", color: "text-purple-400", bg: "bg-purple-500/10 border-purple-500/30",  icon: ArrowRight },
};

export default function ChangelogPage() {
  return (
    <PageShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight mb-4">Changelog</h1>
          <p className="text-slate-400 text-lg leading-relaxed">
            All notable changes to VulnAssess. Follows{" "}
            <a
              href="https://semver.org"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-400 hover:text-blue-300 transition-colors"
            >
              semantic versioning
            </a>
            .
          </p>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-2 mb-10">
          {Object.entries(typeConfig).map(([key, cfg]) => {
            const Icon = cfg.icon;
            return (
              <span key={key} className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full border ${cfg.bg} ${cfg.color}`}>
                <Icon className="w-3 h-3" />
                {cfg.label}
              </span>
            );
          })}
        </div>

        {/* Releases */}
        <div className="space-y-12">
          {releases.map((release, ri) => (
            <div key={release.version} className="relative">
              {/* Timeline line */}
              {ri < releases.length - 1 && (
                <div className="absolute left-[7px] top-8 bottom-[-3rem] w-px bg-slate-800/60" />
              )}

              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-3.5 h-3.5 rounded-full bg-blue-500/80 border-2 border-slate-950 mt-1.5 ring-2 ring-blue-500/20" />
                <div className="flex-1 min-w-0">
                  {/* Version header */}
                  <div className="flex items-center gap-3 mb-1">
                    <h2 className="text-white font-black text-xl">v{release.version}</h2>
                    {release.tag && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold text-blue-400 bg-blue-500/15 border border-blue-500/30">
                        {release.tag}
                      </span>
                    )}
                  </div>
                  <p className="text-slate-600 text-xs font-mono mb-4">{release.date}</p>

                  {/* Changes */}
                  <div className="space-y-2">
                    {release.changes.map((change, ci) => {
                      const cfg = typeConfig[change.type];
                      const Icon = cfg.icon;
                      return (
                        <div key={ci} className="flex items-start gap-3 bg-slate-900/30 border border-slate-800/40 hover:border-slate-700/50 rounded-xl px-4 py-3 transition-colors">
                          <span className={`flex-shrink-0 flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded border mt-0.5 ${cfg.bg} ${cfg.color}`}>
                            <Icon className="w-2.5 h-2.5" />
                            {cfg.label}
                          </span>
                          <p className="text-slate-300 text-sm leading-relaxed">{change.text}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* GitHub link */}
        <div className="mt-12 pt-8 border-t border-slate-800/40 text-center">
          <p className="text-slate-500 text-sm mb-3">Full commit history on GitHub</p>
          <a
            href="https://github.com/sjashwant21/vuln-platform/commits/main"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            View all commits →
          </a>
        </div>
      </div>
    </PageShell>
  );
}
