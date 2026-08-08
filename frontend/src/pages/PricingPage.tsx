/**
 * PricingPage.tsx — /pricing
 * Honest pricing page with a free tier and one paid tier.
 * No fake numbers. "Enterprise" tier listed as "Contact us".
 */
import { Link } from "react-router-dom";
import { Shield, CheckCircle2, X, ArrowRight, Zap } from "lucide-react";

// Reuse the PageShell from DocsPage — in the real app extract to a shared layout file.
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
            <Link to="/register" className="px-4 py-1.5 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 transition-colors">Start Free</Link>
          </div>
        </div>
      </nav>
      <main className="relative">{children}</main>
      <footer className="border-t border-slate-800/40 py-6 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-slate-600 text-xs">© {new Date().getFullYear()} VulnAssess</p>
          <div className="flex items-center gap-4">
            <Link to="/privacy" className="text-slate-700 hover:text-slate-500 text-xs transition-colors">Privacy</Link>
            <Link to="/terms" className="text-slate-700 hover:text-slate-500 text-xs transition-colors">Terms</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

type Plan = {
  name: string;
  price: string;
  period: string;
  desc: string;
  highlight: boolean;
  cta: string;
  ctaTo: string;
  features: { label: string; included: boolean }[];
};

const plans: Plan[] = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    desc: "For individuals and small projects evaluating the platform.",
    highlight: false,
    cta: "Get started free",
    ctaTo: "/register",
    features: [
      { label: "Up to 3 assets",                       included: true  },
      { label: "1 scan per day",                        included: true  },
      { label: "CVE & CVSS scoring",                    included: true  },
      { label: "Basic AI risk summaries",               included: true  },
      { label: "HTML report export",                    included: true  },
      { label: "Unlimited assets",                      included: false },
      { label: "PDF & DOCX export",                     included: false },
      { label: "Full AI analysis & remediation plans",  included: false },
      { label: "Continuous monitoring",                 included: false },
      { label: "Priority support",                      included: false },
    ],
  },
  {
    name: "Pro",
    price: "$49",
    period: "/ month",
    desc: "For startups and small security teams that need full coverage.",
    highlight: true,
    cta: "Start Pro trial",
    ctaTo: "/register?plan=pro",
    features: [
      { label: "Unlimited assets",                      included: true },
      { label: "Unlimited scans",                       included: true },
      { label: "CVE & CVSS scoring",                    included: true },
      { label: "Full AI analysis & remediation plans",  included: true },
      { label: "PDF & DOCX report export",              included: true },
      { label: "Continuous monitoring",                 included: true },
      { label: "API access",                            included: true },
      { label: "Priority support",                      included: true },
      { label: "MFA & JWT auth",                        included: true },
      { label: "Custom branding on reports",            included: false },
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    desc: "For larger teams with custom requirements, SLAs, and integrations.",
    highlight: false,
    cta: "Contact us",
    ctaTo: "/contact",
    features: [
      { label: "Everything in Pro",           included: true },
      { label: "Custom branding on reports",  included: true },
      { label: "SSO / SAML",                  included: true },
      { label: "Custom integrations",         included: true },
      { label: "Dedicated support",           included: true },
      { label: "SLA agreement",               included: true },
      { label: "On-premise deployment",       included: true },
      { label: "Security review & audit",     included: true },
    ],
  },
];

export default function PricingPage() {
  return (
    <PageShell>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 mb-5">
            <Zap className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-xs font-semibold text-blue-400 tracking-wide">PRICING</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight mb-4">
            Simple, honest pricing.
          </h1>
          <p className="text-slate-400 text-lg leading-relaxed">
            Start free. Upgrade when you need more assets, deeper AI analysis, or PDF reporting.
            No hidden fees.
          </p>
        </div>

        {/* Plans */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 items-start">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`relative rounded-2xl p-6 border ${
                plan.highlight
                  ? "bg-blue-950/30 border-blue-500/40 shadow-lg shadow-blue-500/10"
                  : "bg-slate-900/40 border-slate-800/50"
              }`}
            >
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <span className="px-3 py-1 rounded-full text-xs font-bold text-white bg-blue-600 border border-blue-500">
                    Most popular
                  </span>
                </div>
              )}

              <div className="mb-6">
                <p className="text-sm font-semibold text-slate-400 mb-1">{plan.name}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-4xl font-black text-white">{plan.price}</span>
                  {plan.period && <span className="text-slate-500 text-sm">{plan.period}</span>}
                </div>
                <p className="text-slate-500 text-sm mt-2 leading-relaxed">{plan.desc}</p>
              </div>

              <Link
                to={plan.ctaTo}
                className={`flex items-center justify-center gap-2 w-full py-2.5 rounded-xl text-sm font-bold transition-colors mb-6 ${
                  plan.highlight
                    ? "bg-blue-600 hover:bg-blue-500 text-white"
                    : "bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
                }`}
              >
                {plan.cta}
                <ArrowRight className="w-4 h-4" />
              </Link>

              <ul className="space-y-2.5">
                {plan.features.map((f) => (
                  <li key={f.label} className="flex items-center gap-2.5">
                    {f.included ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    ) : (
                      <X className="w-4 h-4 text-slate-700 flex-shrink-0" />
                    )}
                    <span className={`text-sm ${f.included ? "text-slate-300" : "text-slate-600"}`}>
                      {f.label}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <div className="mt-20 max-w-2xl mx-auto">
          <h2 className="text-2xl font-black text-white mb-8 text-center">Common questions</h2>
          <div className="space-y-4">
            {[
              {
                q: "What counts as an asset?",
                a: "A domain, subdomain, IP address, or CIDR range that VulnAssess scans. For example, api.example.com and example.com are two separate assets.",
              },
              {
                q: "What AI model powers the analysis?",
                a: "VulnAssess uses Groq's llama3-70b-8192 as the primary AI provider with OpenAI as a fallback. The model is configurable via environment variables.",
              },
              {
                q: "Can I self-host VulnAssess?",
                a: "Yes. The platform is fully open source. See the GitHub repository for Docker Compose setup instructions. You'll need PostgreSQL, Redis, and a Groq API key.",
              },
              {
                q: "What report formats are supported?",
                a: "VulnAssess generates PDF (executive summary), DOCX (technical detail), and HTML reports. All formats include CVSS scores, severity distribution, and AI-generated remediation steps.",
              },
            ].map((item) => (
              <div key={item.q} className="bg-slate-900/40 border border-slate-800/50 rounded-xl p-5">
                <p className="text-white font-semibold text-sm mb-2">{item.q}</p>
                <p className="text-slate-400 text-sm leading-relaxed">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageShell>
  );
}
