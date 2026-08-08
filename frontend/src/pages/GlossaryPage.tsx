/**
 * GlossaryPage.tsx — /glossary
 * CVE/CVSS/security terms glossary. Grounded in real definitions.
 * Useful for non-expert users (startup founders, devs) using VulnAssess.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Shield, Search, BookOpen } from "lucide-react";

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
            <Link to="/docs" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">Docs</Link>
          </div>
        </div>
      </nav>
      <main className="relative">{children}</main>
      <footer className="border-t border-slate-800/40 py-6 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          <p className="text-slate-600 text-xs">© {new Date().getFullYear()} VulnAssess</p>
          <Link to="/docs" className="text-slate-700 hover:text-slate-500 text-xs transition-colors">Documentation</Link>
        </div>
      </footer>
    </div>
  );
}

type Term = { term: string; abbr?: string; def: string; related?: string[] };

const terms: Term[] = [
  { term: "Attack Surface",        def: "The sum of all the different points where an attacker could try to enter or extract data from an environment — every exposed service, port, domain, or API endpoint.", related: ["Asset Discovery", "Exposure"] },
  { term: "Asset Discovery",       def: "The process of automatically enumerating all internet-facing resources owned by a target organization: domains, subdomains, IP addresses, open ports, and running services.", related: ["Attack Surface"] },
  { term: "CVE",                   abbr: "Common Vulnerabilities and Exposures", def: "A standardized identifier for a publicly known software vulnerability. Each CVE has a unique ID (e.g. CVE-2024-3400) and is maintained by MITRE with NVD as the primary data source.", related: ["CVSS", "NVD"] },
  { term: "CVSS",                  abbr: "Common Vulnerability Scoring System", def: "A framework for rating the severity of software vulnerabilities on a scale of 0–10. CVSS v3 considers Base, Temporal, and Environmental metrics. Scores map to: Low (0–3.9), Medium (4.0–6.9), High (7.0–8.9), Critical (9.0–10.0).", related: ["CVE", "Severity"] },
  { term: "CWE",                   abbr: "Common Weakness Enumeration", def: "A community-developed list of software and hardware weaknesses (e.g. CWE-79: Cross-site Scripting, CWE-89: SQL Injection). CVEs reference CWEs to categorize the underlying weakness type.", related: ["CVE"] },
  { term: "Exposure",              def: "Whether a vulnerability is reachable from the internet. A high-CVSS vulnerability on an internal-only system carries lower real-world risk than the same vulnerability on an internet-facing server.", related: ["Attack Surface", "CVSS"] },
  { term: "False Positive",        def: "A vulnerability finding that is reported by a scanner but does not actually exist or is not exploitable in the target environment. High false-positive rates are a key pain point with traditional scanners.", related: ["Remediation"] },
  { term: "Finding",               def: "A single vulnerability detected during a VulnAssess scan. Each finding includes a CVE ID, CVSS score, affected asset, severity level, AI explanation, and remediation guidance.", related: ["CVE", "CVSS", "Severity"] },
  { term: "NVD",                   abbr: "National Vulnerability Database", def: "The US government repository of vulnerability management data, maintained by NIST. VulnAssess queries the NVD API to enrich findings with CVSS scores, CWE categories, and affected version ranges.", related: ["CVE", "CVSS"] },
  { term: "Patch",                 def: "A software update that fixes a vulnerability. VulnAssess remediation guidance specifies the exact version to upgrade to and how to apply the patch for your environment.", related: ["Remediation"] },
  { term: "Remediation",          def: "The process of fixing a vulnerability — typically by applying a patch, changing a configuration, disabling a service, or implementing a compensating control. VulnAssess generates specific remediation steps for each finding.", related: ["Finding", "Patch"] },
  { term: "Security Health Score", def: "VulnAssess's aggregate measure of an organization's vulnerability posture, expressed as a score from 0–100 and a letter grade (A–F). The score accounts for open finding count, severity distribution, asset exposure, and remediation velocity.", related: ["Finding", "Severity"] },
  { term: "Severity",              def: "The risk level assigned to a finding based on CVSS score: Critical (9.0–10.0), High (7.0–8.9), Medium (4.0–6.9), Low (0–3.9). VulnAssess also applies AI contextual scoring that may adjust effective priority above or below raw CVSS.", related: ["CVSS", "Finding"] },
  { term: "Threat Intelligence",   def: "Data about known attacker techniques, active exploits, and real-world attack campaigns. VulnAssess incorporates threat intelligence to flag CVEs that are actively being exploited, raising their effective priority.", related: ["CVE", "Exposure"] },
  { term: "Vulnerability",         def: "A weakness in software, hardware, or configuration that could be exploited by an attacker to gain unauthorized access, execute code, or cause harm. Not all vulnerabilities are exploitable in all environments.", related: ["CVE", "CWE", "Finding"] },
];

export default function GlossaryPage() {
  const [query, setQuery] = useState("");
  const filtered = terms.filter(
    (t) =>
      t.term.toLowerCase().includes(query.toLowerCase()) ||
      (t.abbr ?? "").toLowerCase().includes(query.toLowerCase()) ||
      t.def.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <PageShell>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="w-5 h-5 text-blue-400" />
            <span className="text-blue-400 text-sm font-semibold uppercase tracking-widest">Glossary</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight mb-4">
            Security terms explained.
          </h1>
          <p className="text-slate-400 text-lg leading-relaxed">
            Plain-language definitions of the security and vulnerability management
            terms you'll encounter in VulnAssess reports and findings.
          </p>
        </div>

        {/* Search */}
        <div className="relative mb-8">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search terms…"
            className="w-full bg-slate-900/60 border border-slate-800/60 hover:border-slate-700/80 focus:border-blue-500/60 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder:text-slate-600 outline-none transition-colors"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400 text-xs"
            >
              Clear
            </button>
          )}
        </div>

        {/* Terms */}
        {filtered.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-12">No terms matching "{query}"</p>
        ) : (
          <div className="space-y-3">
            {filtered.map((t) => (
              <div
                key={t.term}
                id={t.term.toLowerCase().replace(/ /g, "-")}
                className="bg-slate-900/40 border border-slate-800/50 hover:border-slate-700/60 rounded-2xl p-5 transition-colors"
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <div>
                    <h2 className="text-white font-bold text-base">{t.term}</h2>
                    {t.abbr && (
                      <p className="text-slate-500 text-xs mt-0.5">{t.abbr}</p>
                    )}
                  </div>
                </div>
                <p className="text-slate-400 text-sm leading-relaxed">{t.def}</p>
                {t.related && t.related.length > 0 && (
                  <div className="flex items-center gap-2 mt-3 flex-wrap">
                    <span className="text-[11px] text-slate-600 font-medium">Related:</span>
                    {t.related.map((r) => (
                      <a
                        key={r}
                        href={`#${r.toLowerCase().replace(/ /g, "-")}`}
                        className="text-[11px] text-blue-500 hover:text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded transition-colors"
                      >
                        {r}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </PageShell>
  );
}
