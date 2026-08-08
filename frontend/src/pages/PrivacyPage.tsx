/**
 * PrivacyPage.tsx — /privacy
 */
import { Link } from "react-router-dom";
import { Shield } from "lucide-react";

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-white antialiased">
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
          <Link to="/" className="text-slate-500 hover:text-slate-300 text-sm transition-colors">← Home</Link>
        </div>
      </nav>
      <main className="relative">{children}</main>
      <footer className="border-t border-slate-800/40 py-6 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
          <p className="text-slate-600 text-xs">© {new Date().getFullYear()} VulnAssess</p>
          <Link to="/terms" className="text-slate-700 hover:text-slate-500 text-xs transition-colors">Terms of Service</Link>
        </div>
      </footer>
    </div>
  );
}

export default function PrivacyPage() {
  const updated = "August 8, 2024";
  return (
    <PageShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h1 className="text-4xl font-black text-white tracking-tight mb-2">Privacy Policy</h1>
        <p className="text-slate-500 text-sm mb-10">Last updated: {updated}</p>
        <div className="prose prose-invert prose-slate max-w-none space-y-8 text-slate-400 text-sm leading-relaxed">
          {[
            { title: "What we collect", body: "When you create an account, we collect your email address and a hashed password. When you run scans, we store the target domain/IP, scan results, and generated reports. We do not collect payment information directly — this is handled by our payment processor." },
            { title: "How we use it", body: "We use your data to operate the VulnAssess platform: running scans, generating reports, and sending you account-related emails (password reset, scan completion). We do not sell your data to third parties." },
            { title: "AI processing", body: "Vulnerability details are sent to Groq's API (llama3-70b-8192) to generate explanations and remediation guidance. This data is transmitted securely (HTTPS). Review Groq's privacy policy at groq.com for how they handle API data." },
            { title: "Data retention", body: "Scan results and reports are retained as long as your account is active. You can delete your account and all associated data at any time from the account settings page." },
            { title: "Security", body: "Passwords are hashed with bcrypt. Data in transit is encrypted via TLS. Access to scan data is restricted to your account (tenant isolation at the database level)." },
            { title: "Cookies", body: "We use a single session cookie for authentication (JWT). We do not use tracking cookies or analytics cookies." },
            { title: "Contact", body: "Questions about this policy? Contact the maintainer via the GitHub repository: github.com/sjashwant21/vuln-platform." },
          ].map((s) => (
            <section key={s.title}>
              <h2 className="text-white font-bold text-base mb-2">{s.title}</h2>
              <p>{s.body}</p>
            </section>
          ))}
        </div>
      </div>
    </PageShell>
  );
}
