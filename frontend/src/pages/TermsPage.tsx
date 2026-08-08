/**
 * TermsPage.tsx — /terms
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
          <Link to="/privacy" className="text-slate-700 hover:text-slate-500 text-xs transition-colors">Privacy Policy</Link>
        </div>
      </footer>
    </div>
  );
}

export default function TermsPage() {
  const updated = "August 8, 2024";
  return (
    <PageShell>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <h1 className="text-4xl font-black text-white tracking-tight mb-2">Terms of Service</h1>
        <p className="text-slate-500 text-sm mb-10">Last updated: {updated}</p>
        <div className="space-y-8 text-slate-400 text-sm leading-relaxed">
          {[
            { title: "Acceptance", body: "By using VulnAssess you agree to these terms. If you do not agree, do not use the platform." },
            { title: "Permitted use", body: "You may only scan assets you own or have explicit written permission to test. Unauthorized scanning of third-party systems is strictly prohibited and may be illegal. VulnAssess is a tool to help you assess your own security posture." },
            { title: "Prohibited use", body: "You may not use VulnAssess to scan systems without authorization, to facilitate attacks on third parties, to circumvent access controls, or to process data in violation of applicable law." },
            { title: "Account responsibility", body: "You are responsible for all activity under your account. Keep your credentials secure. Report unauthorized access immediately." },
            { title: "Data", body: "You own your scan data and reports. We process them only to provide the service. See our Privacy Policy for details." },
            { title: "Disclaimer", body: "VulnAssess is provided as-is. We make no warranty that the platform will identify all vulnerabilities in your systems. Security assessments are snapshots in time." },
            { title: "Limitation of liability", body: "To the maximum extent permitted by law, VulnAssess and its maintainers are not liable for any indirect, incidental, or consequential damages arising from use of the platform." },
            { title: "Changes", body: "We may update these terms. Continued use after changes constitutes acceptance. Material changes will be communicated via the platform." },
            { title: "Contact", body: "Questions? Open an issue on the GitHub repository: github.com/sjashwant21/vuln-platform." },
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
