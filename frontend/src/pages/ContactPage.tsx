/**
 * ContactPage.tsx — /contact
 * Simple contact form that posts to the real FastAPI endpoint /v1/contact
 * (or falls back gracefully if not yet implemented).
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { Shield, Mail, Github, Send, CheckCircle2, AlertTriangle } from "lucide-react";

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

type FormState = "idle" | "sending" | "success" | "error";

export default function ContactPage() {
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });
  const [state, setState] = useState<FormState>("idle");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setState("sending");
    try {
      const res = await fetch("/v1/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setState(res.ok ? "success" : "error");
    } catch {
      // If /v1/contact isn't implemented yet, fall back gracefully
      setState("error");
    }
  }

  const inputCls =
    "w-full bg-slate-900/60 border border-slate-800/60 hover:border-slate-700/80 focus:border-blue-500/60 rounded-xl px-4 py-3 text-sm text-white placeholder:text-slate-600 outline-none transition-colors duration-200";

  return (
    <PageShell>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16">

          {/* Left: copy */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Mail className="w-5 h-5 text-blue-400" />
              <span className="text-blue-400 text-sm font-semibold uppercase tracking-widest">Contact</span>
            </div>
            <h1 className="text-4xl sm:text-5xl font-black text-white tracking-tight mb-4">
              Get in touch.
            </h1>
            <p className="text-slate-400 text-lg leading-relaxed mb-8">
              Have a question about VulnAssess, found a bug, or want to contribute?
              Reach out via the form or directly through GitHub.
            </p>

            <div className="space-y-4">
              <div className="flex items-start gap-4 bg-slate-900/40 border border-slate-800/50 rounded-xl p-4">
                <Github className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-white font-semibold text-sm">GitHub</p>
                  <p className="text-slate-500 text-sm mt-0.5">
                    Open issues, PRs, or discussions on the repository.
                  </p>
                  <a
                    href="https://github.com/sjashwant21/vuln-platform"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300 text-sm mt-1.5 inline-block transition-colors"
                  >
                    github.com/sjashwant21/vuln-platform →
                  </a>
                </div>
              </div>

              <div className="flex items-start gap-4 bg-slate-900/40 border border-slate-800/50 rounded-xl p-4">
                <AlertTriangle className="w-5 h-5 text-orange-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-white font-semibold text-sm">Security vulnerabilities</p>
                  <p className="text-slate-500 text-sm mt-0.5">
                    Do not open a public GitHub issue for security bugs.
                    Use GitHub Security Advisories instead.
                  </p>
                  <a
                    href="https://github.com/sjashwant21/vuln-platform/security"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-orange-400 hover:text-orange-300 text-sm mt-1.5 inline-block transition-colors"
                  >
                    Report privately →
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* Right: form */}
          <div>
            {state === "success" ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 text-center py-16">
                <CheckCircle2 className="w-12 h-12 text-emerald-400" />
                <h2 className="text-xl font-bold text-white">Message sent</h2>
                <p className="text-slate-400 text-sm max-w-xs">
                  Thanks for reaching out. We'll get back to you as soon as possible.
                </p>
                <button
                  onClick={() => { setState("idle"); setForm({ name: "", email: "", subject: "", message: "" }); }}
                  className="text-blue-400 hover:text-blue-300 text-sm transition-colors"
                >
                  Send another →
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4" noValidate>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                      Name
                    </label>
                    <input
                      type="text"
                      required
                      value={form.name}
                      onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                      placeholder="Your name"
                      className={inputCls}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                      Email
                    </label>
                    <input
                      type="email"
                      required
                      value={form.email}
                      onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                      placeholder="you@company.com"
                      className={inputCls}
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                    Subject
                  </label>
                  <input
                    type="text"
                    required
                    value={form.subject}
                    onChange={e => setForm(f => ({ ...f, subject: e.target.value }))}
                    placeholder="What's this about?"
                    className={inputCls}
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
                    Message
                  </label>
                  <textarea
                    required
                    rows={6}
                    value={form.message}
                    onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                    placeholder="Describe your question, bug, or feedback…"
                    className={`${inputCls} resize-none`}
                  />
                </div>

                {state === "error" && (
                  <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3">
                    <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                    <p className="text-sm text-red-300">
                      Couldn't send the message. Try{" "}
                      <a
                        href="https://github.com/sjashwant21/vuln-platform/issues"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline"
                      >
                        opening a GitHub issue
                      </a>{" "}
                      instead.
                    </p>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={state === "sending"}
                  className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="w-4 h-4" />
                  {state === "sending" ? "Sending…" : "Send message"}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </PageShell>
  );
}
