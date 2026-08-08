/**
 * NotFoundPage.tsx — * (catch-all 404 route)
 * Clean, branded 404 that doesn't re-render the landing page.
 */
import { Link } from "react-router-dom";
import { Shield, Home, BookOpen, ArrowRight } from "lucide-react";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white antialiased flex flex-col">
      {/* Ambient glow */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_40%_at_50%_40%,rgba(59,130,246,0.06),transparent)]" />
      </div>

      {/* Nav */}
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
        </div>
      </nav>

      {/* Body */}
      <main className="flex-1 flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          {/* 404 */}
          <p className="text-8xl font-black text-slate-800 select-none mb-2">404</p>
          <h1 className="text-2xl font-black text-white mb-3">Page not found</h1>
          <p className="text-slate-400 text-sm leading-relaxed mb-8">
            The page you're looking for doesn't exist or has been moved.
          </p>

          {/* Quick links */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              to="/"
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-500 transition-colors"
            >
              <Home className="w-4 h-4" />
              Back to home
            </Link>
            <Link
              to="/docs"
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-300 border border-slate-700/60 hover:border-slate-600 hover:text-white bg-slate-900/50 hover:bg-slate-800/50 transition-all"
            >
              <BookOpen className="w-4 h-4" />
              Documentation
            </Link>
          </div>

          {/* Quick nav */}
          <div className="mt-10 border-t border-slate-800/40 pt-6">
            <p className="text-xs text-slate-600 mb-4 uppercase tracking-wider font-medium">You might be looking for</p>
            <div className="flex flex-wrap justify-center gap-3">
              {[
                { label: "Pricing",   to: "/pricing"   },
                { label: "Security",  to: "/security"  },
                { label: "Glossary",  to: "/glossary"  },
                { label: "Changelog", to: "/changelog" },
                { label: "About",     to: "/about"     },
                { label: "Contact",   to: "/contact"   },
              ].map((l) => (
                <Link
                  key={l.to}
                  to={l.to}
                  className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                >
                  <ArrowRight className="w-3 h-3" />
                  {l.label}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-800/40 py-5">
        <p className="text-center text-slate-700 text-xs">© {new Date().getFullYear()} VulnAssess</p>
      </footer>
    </div>
  );
}
