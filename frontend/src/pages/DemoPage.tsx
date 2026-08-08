/**
 * DemoPage.tsx — /demo
 * Interactive demo walkthrough. Shows the platform workflow with realistic
 * static data — no backend calls needed, so it works before sign-up.
 */
import { useState } from "react";
import { Link }     from "react-router-dom";
import {
  Shield, Radar, Brain, Wrench, FileText,
  ArrowRight, Lock, CheckCircle2, AlertTriangle,
  ScanLine, Target, BarChart2, ChevronRight,
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
            <Link
              to="/register"
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 transition-colors"
            >
              Start Free <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </nav>
      <main className="relative">{children}</main>
      <footer className="border-t border-slate-800/40 py-6 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-slate-600 text-xs">© {new Date().getFullYear()} VulnAssess</p>
          <Link to="/register" className="text-blue-400 hover:text-blue-300 text-xs transition-colors">
            Ready to scan your own assets? Start free →
          </Link>
        </div>
      </footer>
    </div>
  );
}

// ── Demo data ─────────────────────────────────────────────────────────────────
const demoSteps = [
  {
    id: "discover",
    icon: Radar,
    label: "01 · Discover",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    activeBorder: "border-blue-500/60",
    title: "Asset Discovery",
    desc: "VulnAssess enumerates all internet-facing assets for the target domain automatically.",
    preview: <DiscoverPreview />,
  },
  {
    id: "scan",
    icon: ScanLine,
    label: "02 · Analyze",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    border: "border-purple-500/30",
    activeBorder: "border-purple-500/60",
    title: "Vulnerability Scan",
    desc: "Every asset is scanned for known CVEs. CVSS scoring and service fingerprinting run automatically.",
    preview: <ScanPreview />,
  },
  {
    id: "prioritize",
    icon: Target,
    label: "03 · Prioritize",
    color: "text-orange-400",
    bg: "bg-orange-500/10",
    border: "border-orange-500/30",
    activeBorder: "border-orange-500/60",
    title: "AI Prioritization",
    desc: "The AI ranks findings by real-world risk, not just CVSS. Noise is filtered out automatically.",
    preview: <PrioritizePreview />,
  },
  {
    id: "remediate",
    icon: Wrench,
    label: "04 · Remediate",
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    activeBorder: "border-emerald-500/60",
    title: "Remediation & Reporting",
    desc: "Step-by-step fix instructions and a full PDF/DOCX report — generated automatically.",
    preview: <RemediatePreview />,
  },
];

// ── Step previews ─────────────────────────────────────────────────────────────
function WindowChrome({ url }: { url: string }) {
  return (
    <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800/60 bg-slate-950/60">
      <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
      <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
      <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
      <div className="ml-2 flex-1 bg-slate-800/60 rounded-md px-3 py-1 text-xs text-slate-500 font-mono truncate">{url}</div>
      <Lock className="w-3 h-3 text-emerald-400 flex-shrink-0" />
    </div>
  );
}

const discoveredAssets = [
  { host: "acme-corp.com",          type: "Domain",    ports: "80, 443",     service: "nginx 1.22.1"   },
  { host: "api.acme-corp.com",      type: "Subdomain", ports: "443",         service: "FastAPI"        },
  { host: "admin.acme-corp.com",    type: "Subdomain", ports: "443",         service: "React SPA"      },
  { host: "internal.acme-corp.com", type: "Subdomain", ports: "8080",        service: "Tomcat 9.0.65"  },
  { host: "192.168.1.45",           type: "IP",        ports: "22, 443",     service: "OpenSSH 8.2p1"  },
];

function DiscoverPreview() {
  return (
    <div className="bg-slate-900/70 border border-slate-700/50 rounded-2xl overflow-hidden">
      <WindowChrome url="app.vulnassess.io/scans/VA-2024-0847/assets" />
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-semibold text-slate-400">Discovered Assets</span>
          <span className="text-xs text-emerald-400 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Discovery running…
          </span>
        </div>
        <div className="bg-slate-950/50 border border-slate-800/50 rounded-xl overflow-hidden">
          <div className="divide-y divide-slate-800/30">
            {discoveredAssets.map((a, i) => (
              <div key={i} className="flex items-center gap-3 px-3 py-2.5 hover:bg-slate-800/20 transition-colors">
                <span className="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0" />
                <span className="font-mono text-xs text-slate-300 flex-1 min-w-0 truncate">{a.host}</span>
                <span className="text-[10px] text-slate-600 hidden sm:block w-20 flex-shrink-0">{a.type}</span>
                <span className="text-[10px] font-mono text-slate-500 hidden sm:block w-16 flex-shrink-0">{a.ports}</span>
                <span className="text-[10px] text-slate-500 hidden md:block flex-shrink-0">{a.service}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-600">5 assets found · 0 errors</span>
          <span className="text-blue-400">+ 2 scanning…</span>
        </div>
      </div>
    </div>
  );
}

const scanFindings = [
  { cve: "CVE-2024-3400",  name: "PAN-OS Command Injection",  asset: "firewall-01",  cvss: "10.0", sev: "Critical" },
  { cve: "CVE-2023-44487", name: "HTTP/2 Rapid Reset",        asset: "acme-corp.com",cvss: "7.5",  sev: "High"     },
  { cve: "CVE-2023-38408", name: "OpenSSH RCE",               asset: "192.168.1.45", cvss: "6.8",  sev: "Medium"   },
  { cve: "CVE-2022-42889", name: "Apache Text4Shell",         asset: "api.acme-corp",cvss: "9.8",  sev: "Critical" },
];
const sevColor: Record<string, string> = {
  Critical: "text-red-400", High: "text-orange-400", Medium: "text-yellow-400", Low: "text-blue-400",
};

function ScanPreview() {
  return (
    <div className="bg-slate-900/70 border border-slate-700/50 rounded-2xl overflow-hidden">
      <WindowChrome url="app.vulnassess.io/scans/VA-2024-0847/findings" />
      <div className="p-4 space-y-3">
        <div className="grid grid-cols-4 gap-2 mb-1">
          {[{ l: "Critical", v: "5", c: "text-red-400", b: "bg-red-500/10 border-red-500/20" },
            { l: "High",     v: "11",c: "text-orange-400",b: "bg-orange-500/10 border-orange-500/20" },
            { l: "Medium",   v: "18",c: "text-yellow-400",b: "bg-yellow-500/10 border-yellow-500/20" },
            { l: "Low",      v: "13",c: "text-blue-400",   b: "bg-blue-500/10 border-blue-500/20"    },
          ].map(m => (
            <div key={m.l} className={`border rounded-lg p-2 text-center ${m.b}`}>
              <p className={`text-lg font-black ${m.c}`}>{m.v}</p>
              <p className="text-[10px] text-slate-500">{m.l}</p>
            </div>
          ))}
        </div>
        <div className="bg-slate-950/50 border border-slate-800/50 rounded-xl overflow-hidden">
          <div className="divide-y divide-slate-800/30">
            {scanFindings.map((f, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-2.5 hover:bg-slate-800/20 transition-colors">
                <span className="font-mono text-[10px] text-slate-500 w-28 flex-shrink-0">{f.cve}</span>
                <span className="text-xs text-slate-300 flex-1 min-w-0 truncate">{f.name}</span>
                <span className="text-[10px] font-mono text-slate-500 w-8 text-right flex-shrink-0">{f.cvss}</span>
                <span className={`text-[10px] font-bold flex-shrink-0 ${sevColor[f.sev]}`}>{f.sev}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function PrioritizePreview() {
  return (
    <div className="bg-slate-900/70 border border-slate-700/50 rounded-2xl overflow-hidden">
      <WindowChrome url="app.vulnassess.io/scans/VA-2024-0847/priority" />
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-2 mb-1 bg-blue-500/8 border border-blue-500/20 rounded-xl px-3 py-2.5">
          <Brain className="w-4 h-4 text-blue-400 flex-shrink-0" />
          <p className="text-xs text-slate-300 leading-relaxed">
            AI filtered <span className="text-blue-300 font-semibold">31 low-risk findings</span>.
            Focus on these <span className="text-red-300 font-semibold">3 critical items</span> first.
          </p>
        </div>
        {[
          { rank: 1, cve: "CVE-2024-3400",  name: "PAN-OS Command Injection",  reason: "Actively exploited · internet-facing",  sev: "Critical", urgency: "Patch now"      },
          { rank: 2, cve: "CVE-2022-42889", name: "Apache Text4Shell",         reason: "Public PoC · api.acme-corp exposed",    sev: "Critical", urgency: "Patch this week" },
          { rank: 3, cve: "CVE-2023-44487", name: "HTTP/2 Rapid Reset",        reason: "DoS risk · prod load balancer",         sev: "High",     urgency: "Patch this week" },
        ].map((f) => (
          <div key={f.rank} className="bg-slate-950/50 border border-slate-800/50 rounded-xl p-3 space-y-1.5">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-800 text-slate-400 text-[10px] font-bold flex items-center justify-center">
                  {f.rank}
                </span>
                <span className="text-sm text-white font-semibold">{f.name}</span>
              </div>
              <span className={`text-[10px] font-bold flex-shrink-0 ${sevColor[f.sev]}`}>{f.sev}</span>
            </div>
            <p className="text-xs text-slate-500 pl-7 font-mono">{f.cve}</p>
            <div className="flex items-center gap-2 pl-7">
              <AlertTriangle className="w-3 h-3 text-orange-400 flex-shrink-0" />
              <p className="text-xs text-slate-400">{f.reason}</p>
              <span className="ml-auto text-[10px] font-bold text-orange-400 bg-orange-500/10 px-1.5 py-0.5 rounded">{f.urgency}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RemediatePreview() {
  return (
    <div className="bg-slate-900/70 border border-slate-700/50 rounded-2xl overflow-hidden">
      <WindowChrome url="app.vulnassess.io/scans/VA-2024-0847/report" />
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-400" />
            <span className="text-sm font-bold text-white">Security Assessment Report</span>
          </div>
          <span className="text-xs text-orange-400 bg-orange-500/15 border border-orange-500/30 px-2 py-0.5 rounded-lg font-bold">C+ · 74/100</span>
        </div>
        <div className="bg-emerald-500/8 border border-emerald-500/20 rounded-xl p-3">
          <p className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider mb-2">Remediation — CVE-2024-3400</p>
          <div className="space-y-1.5">
            {["Upgrade PAN-OS to 11.1.2-h3 or later","Disable GlobalProtect portal if upgrade not possible","Enable threat signatures 95187 and 95189"].map((s, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i+1}</span>
                <p className="text-slate-300 text-xs leading-relaxed">{s}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {[["PDF Export", "Executive summary"], ["DOCX Export", "Technical detail"]].map(([t, d]) => (
            <div key={t} className="flex items-center gap-2 bg-slate-950/50 border border-slate-800/50 rounded-lg p-2.5">
              <FileText className="w-4 h-4 text-slate-500 flex-shrink-0" />
              <div>
                <p className="text-xs font-semibold text-slate-300">{t}</p>
                <p className="text-[10px] text-slate-600">{d}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500/70" />
          Report auto-generated after each scan
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function DemoPage() {
  const [active, setActive] = useState(0);
  const step = demoSteps[active];
  const Icon = step.icon;

  return (
    <PageShell>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 mb-5">
            <ScanLine className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-xs font-semibold text-blue-400 tracking-wide">INTERACTIVE DEMO</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight mb-4">
            See VulnAssess in action.
          </h1>
          <p className="text-slate-400 text-lg leading-relaxed">
            Walk through a complete security assessment — from asset discovery
            to prioritized findings and automated reports.
          </p>
        </div>

        {/* Step tabs */}
        <div className="flex flex-wrap justify-center gap-2 mb-8">
          {demoSteps.map((s, i) => {
            const SIcon = s.icon;
            const isActive = i === active;
            return (
              <button
                key={s.id}
                onClick={() => setActive(i)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold border transition-all duration-200 ${
                  isActive
                    ? `${s.color} ${s.bg} ${s.activeBorder} border`
                    : "text-slate-500 border-slate-800/50 bg-slate-900/30 hover:border-slate-700/60 hover:text-slate-300"
                }`}
              >
                <SIcon className="w-4 h-4" />
                <span className="hidden sm:inline">{s.label}</span>
                <span className="sm:hidden">{s.label.split("·")[0].trim()}</span>
              </button>
            );
          })}
        </div>

        {/* Main demo area */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start">
          {/* Left: description */}
          <div className="lg:col-span-2 space-y-4">
            <div className={`inline-flex p-3 rounded-2xl ${step.bg}`}>
              <Icon className={`w-6 h-6 ${step.color}`} strokeWidth={1.75} />
            </div>
            <h2 className="text-2xl font-black text-white">{step.title}</h2>
            <p className="text-slate-400 leading-relaxed">{step.desc}</p>

            {/* Step navigation */}
            <div className="flex items-center gap-3 pt-4">
              <button
                onClick={() => setActive(i => Math.max(0, i - 1))}
                disabled={active === 0}
                className="px-4 py-2 rounded-lg text-sm font-semibold text-slate-400 border border-slate-800/50 hover:border-slate-700 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                ← Prev
              </button>
              <button
                onClick={() => setActive(i => Math.min(demoSteps.length - 1, i + 1))}
                disabled={active === demoSteps.length - 1}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            {/* Progress dots */}
            <div className="flex items-center gap-2 pt-1">
              {demoSteps.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setActive(i)}
                  className={`h-1.5 rounded-full transition-all duration-300 ${
                    i === active ? "w-6 bg-blue-500" : "w-1.5 bg-slate-700 hover:bg-slate-600"
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Right: preview */}
          <div className="lg:col-span-3">
            {step.preview}
          </div>
        </div>

        {/* CTA */}
        <div className="mt-16 text-center border-t border-slate-800/40 pt-12">
          <h2 className="text-2xl font-black text-white mb-3">Ready to scan your own assets?</h2>
          <p className="text-slate-400 mb-6">Free tier available. First scan in under 2 minutes.</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/register"
              className="flex items-center gap-2 px-7 py-3.5 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-500 transition-colors"
            >
              <Shield className="w-4 h-4" />
              Start Security Assessment
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/pricing"
              className="text-slate-400 hover:text-white text-sm transition-colors"
            >
              View pricing →
            </Link>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
