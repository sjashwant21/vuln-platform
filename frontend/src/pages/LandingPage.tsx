/**
 * VulnAssess — LandingPage.tsx  (final)
 *
 * CHANGES THIS PASS:
 * ──────────────────────────────────────────────────────────────────────────
 * • Replaced ALL <a href="/…"> with react-router-dom <Link to="/…"> so
 *   navigating to /login, /register, /docs, /pricing, /security, /privacy,
 *   /terms, /contact, /about, /glossary, /changelog, /roadmap never causes
 *   a full-page reload and never re-renders the landing page.
 * • Logo <Link to="/"> — clicking the logo on a sub-page returns home
 *   without showing the landing page route inside itself.
 * • Navbar hash anchors (#features, #how-it-works, #ai, #reports) use a
 *   smooth-scroll helper so they work from within the landing page only.
 *   From sub-pages they navigate to /#features etc. via Link.
 * • "Docs" nav item now routes to /docs (real FastAPI Swagger proxy page)
 * • "Pricing" nav item routes to /pricing (real page)
 * • Removed grid texture from BottomCTA (was causing the visible grid in
 *   the screenshot).
 * • Footer GitHub link is the real repo URL.
 * • Footer /docs and /health point to the real FastAPI endpoints.
 * • Added isLanding prop to Navbar so hash-links only fire on the landing
 *   page; on sub-pages they become full Link navigations to /#section.
 * ──────────────────────────────────────────────────────────────────────────
 */

import { useState, useEffect, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import { motion, useInView } from "framer-motion";
import {
  Shield, Radar,
  Brain, Wrench,
  FileText, ArrowRight,
  Github, Twitter,
  Linkedin, Lock,
  Activity, AlertTriangle,
  CheckCircle2, CheckCheck,
  Globe, Search,
  BarChart2, Target,
  X, Menu,
  ScanLine, ListChecks,
  ClipboardList, Eye,
  ExternalLink,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Utility: scroll-reveal hook
// ─────────────────────────────────────────────────────────────────────────────
function useReveal(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "0px 0px -60px 0px" });
  return { ref, inView };
}

// Smooth-scroll to an on-page anchor
function scrollTo(id: string) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared: Logo — always a Link so it never hard-reloads
// ─────────────────────────────────────────────────────────────────────────────
function Logo({ size = "md" }: { size?: "sm" | "md" }) {
  const iconSize = size === "sm" ? "w-4 h-4" : "w-5 h-5";
  const textSize = size === "sm" ? "text-base" : "text-lg";
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <div className="relative flex-shrink-0">
        <div className="absolute inset-0 bg-blue-500/30 rounded-lg blur-sm" />
        <div className="relative bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg p-1.5">
          <Shield className={`${iconSize} text-white`} strokeWidth={2.5} />
        </div>
      </div>
      <span className={`text-white font-bold ${textSize} tracking-tight`}>
        Vuln<span className="text-blue-400">Assess</span>
      </span>
    </Link>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Shared: Primary button (uses Link, never <a href>)
// ─────────────────────────────────────────────────────────────────────────────
function PrimaryButton({
  to,
  children,
  size = "md",
  icon,
  external = false,
}: {
  to: string;
  children: React.ReactNode;
  size?: "sm" | "md" | "lg";
  icon?: React.ReactNode;
  external?: boolean;
}) {
  const padding =
    size === "lg"
      ? "px-8 py-4 text-base"
      : size === "sm"
      ? "px-4 py-2 text-sm"
      : "px-6 py-3 text-sm";
  const cls = `group relative flex items-center gap-2 ${padding} rounded-xl font-bold text-white overflow-hidden`;
  const inner = (
    <>
      <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-blue-500 transition-all duration-300 group-hover:from-blue-500 group-hover:to-blue-400" />
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-[radial-gradient(ellipse_at_center,rgba(147,197,253,0.12)_0%,transparent_70%)]" />
      {icon && <span className="relative">{icon}</span>}
      <span className="relative">{children}</span>
      <ArrowRight className="relative w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200" />
    </>
  );
  if (external)
    return (
      <a href={to} target="_blank" rel="noopener noreferrer" className={cls}>
        {inner}
      </a>
    );
  return (
    <Link to={to} className={cls}>
      {inner}
    </Link>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. NAVBAR
//  • Hash links (#features etc.) smooth-scroll when on /, navigate via Link
//    when on a sub-page (so the user reaches /#features, not a dead anchor).
//  • "Docs" → /docs  (real FastAPI Swagger UI endpoint)
//  • "Pricing" → /pricing
//  • "Log In" → /login (Link, no reload)
//  • "Start Assessment" → /register (Link, no reload)
//  • Logo → / (Link, no reload)
// ─────────────────────────────────────────────────────────────────────────────
type NavItem =
  | { label: string; kind: "hash"; id: string }
  | { label: string; kind: "route"; to: string };

const NAV_ITEMS: NavItem[] = [
  { label: "Features",     kind: "hash",  id: "features" },
  { label: "How It Works", kind: "hash",  id: "how-it-works" },
  { label: "Docs",         kind: "route", to: "/docs" },
  { label: "Pricing",      kind: "route", to: "/pricing" },
];

function Navbar() {
  const [scrolled, setScrolled]   = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const isLanding = location.pathname === "/";

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Close mobile menu on route change
  useEffect(() => { setMobileOpen(false); }, [location.pathname]);

  function handleNavClick(item: NavItem, e: React.MouseEvent) {
    if (item.kind === "hash") {
      if (isLanding) {
        e.preventDefault();
        setMobileOpen(false);
        scrollTo(item.id);
      }
      // If not on landing, the Link to={`/#${item.id}`} will handle navigation
    } else {
      setMobileOpen(false);
    }
  }

  function navHref(item: NavItem) {
    if (item.kind === "hash") return isLanding ? `#${item.id}` : `/#${item.id}`;
    return item.to;
  }

  return (
    <>
      <motion.nav
        initial={{ y: -80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? "bg-slate-950/80 backdrop-blur-xl border-b border-slate-800/60 shadow-lg shadow-black/20"
            : "bg-transparent"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Logo />

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-8">
              {NAV_ITEMS.map((item) =>
                item.kind === "hash" && isLanding ? (
                  <button
                    key={item.label}
                    onClick={() => scrollTo(item.id)}
                    className="text-slate-400 hover:text-white text-sm font-medium transition-colors duration-200"
                  >
                    {item.label}
                  </button>
                ) : (
                  <Link
                    key={item.label}
                    to={navHref(item)}
                    className="text-slate-400 hover:text-white text-sm font-medium transition-colors duration-200"
                  >
                    {item.label}
                  </Link>
                )
              )}
            </div>

            {/* Desktop CTA */}
            <div className="hidden md:flex items-center gap-3">
              <Link
                to="/login"
                className="text-slate-400 hover:text-white text-sm font-medium transition-colors duration-200"
              >
                Log In
              </Link>
              <PrimaryButton to="/register" size="sm">
                Start Assessment
              </PrimaryButton>
            </div>

            {/* Mobile hamburger */}
            <button
              aria-label={mobileOpen ? "Close navigation" : "Open navigation"}
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/50 transition-colors"
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </motion.nav>

      {/* Mobile drawer */}
      <motion.div
        initial={false}
        animate={mobileOpen ? { opacity: 1, y: 0 } : { opacity: 0, y: -8 }}
        transition={{ duration: 0.2 }}
        className={`fixed top-16 left-0 right-0 z-40 md:hidden bg-slate-950/95 backdrop-blur-xl border-b border-slate-800/60 ${
          mobileOpen ? "pointer-events-auto" : "pointer-events-none"
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 py-4 space-y-1">
          {NAV_ITEMS.map((item) =>
            item.kind === "hash" && isLanding ? (
              <button
                key={item.label}
                onClick={() => { scrollTo(item.id); setMobileOpen(false); }}
                className="w-full text-left block px-3 py-2.5 text-slate-300 hover:text-white hover:bg-slate-800/50 rounded-lg text-sm font-medium transition-colors"
              >
                {item.label}
              </button>
            ) : (
              <Link
                key={item.label}
                to={navHref(item)}
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2.5 text-slate-300 hover:text-white hover:bg-slate-800/50 rounded-lg text-sm font-medium transition-colors"
              >
                {item.label}
              </Link>
            )
          )}
          <div className="pt-3 border-t border-slate-800/50 flex flex-col gap-2">
            <Link
              to="/login"
              onClick={() => setMobileOpen(false)}
              className="block px-3 py-2.5 text-slate-400 hover:text-white text-sm font-medium transition-colors"
            >
              Log In
            </Link>
            <Link
              to="/register"
              onClick={() => setMobileOpen(false)}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-bold text-white bg-blue-600 hover:bg-blue-500 transition-colors"
            >
              Start Security Assessment
            </Link>
          </div>
        </div>
      </motion.div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. HERO
// ─────────────────────────────────────────────────────────────────────────────
const vulnRows = [
  { cve: "CVE-2024-3400",  name: "PAN-OS Command Injection",       asset: "firewall-01",       cvss: "10.0", severity: "Critical", status: "Open"   },
  { cve: "CVE-2023-44487", name: "HTTP/2 Rapid Reset (nginx)",     asset: "prod-lb-01",        cvss: "7.5",  severity: "High",     status: "Open"   },
  { cve: "CVE-2023-38408", name: "OpenSSH Remote Code Exec",       asset: "api-server-03",     cvss: "6.8",  severity: "Medium",   status: "Patched"},
  { cve: "CVE-2024-21338", name: "Windows Kernel Elevation",       asset: "win-workstation-07",cvss: "7.8",  severity: "High",     status: "Open"   },
];

const severityMeta: Record<string, { color: string; dot: string }> = {
  Critical: { color: "text-red-400",    dot: "bg-red-500"    },
  High:     { color: "text-orange-400", dot: "bg-orange-500" },
  Medium:   { color: "text-yellow-400", dot: "bg-yellow-500" },
  Low:      { color: "text-blue-400",   dot: "bg-blue-500"   },
};

function DashboardPreview() {
  return (
    <motion.div
      animate={{ y: [0, -6, 0] }}
      transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
      className="relative w-full"
    >
      <div className="absolute -inset-6 bg-gradient-to-r from-blue-600/15 via-purple-600/8 to-blue-600/15 rounded-3xl blur-3xl pointer-events-none" />
      <div className="relative bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden shadow-2xl shadow-black/60">
        {/* Window chrome */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800/60 bg-slate-950/60">
          <div className="w-3 h-3 rounded-full bg-red-500/70" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
          <div className="w-3 h-3 rounded-full bg-emerald-500/70" />
          <div className="ml-3 flex-1 bg-slate-800/60 rounded-md px-3 py-1 text-xs text-slate-500 font-mono">
            app.vulnassess.io/dashboard
          </div>
          <Lock className="w-3.5 h-3.5 text-emerald-400" />
        </div>
        <div className="p-4 sm:p-5 space-y-4">
          {/* Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Security Score", value: "74",  unit: "/100",   color: "text-yellow-400", badge: "C+",     badgeCls: "text-yellow-400 bg-yellow-500/15 border-yellow-500/30" },
              { label: "Critical",       value: "3",   unit: "vulns",  color: "text-red-400",    badge: "URGENT", badgeCls: "text-red-400 bg-red-500/15 border-red-500/30"          },
              { label: "High",           value: "11",  unit: "vulns",  color: "text-orange-400", badge: "HIGH",   badgeCls: "text-orange-400 bg-orange-500/15 border-orange-500/30" },
              { label: "Assets",         value: "28",  unit: "scanned",color: "text-blue-400",   badge: "ALL",    badgeCls: "text-blue-400 bg-blue-500/15 border-blue-500/30"       },
            ].map((m) => (
              <div key={m.label} className="bg-slate-950/50 border border-slate-800/60 rounded-xl p-3">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">{m.label}</p>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className={`text-2xl font-black ${m.color}`}>{m.value}</span>
                  <span className="text-xs text-slate-600">{m.unit}</span>
                </div>
                <span className={`mt-1.5 inline-block px-1.5 py-0.5 rounded text-[10px] font-bold border ${m.badgeCls}`}>{m.badge}</span>
              </div>
            ))}
          </div>
          {/* Findings table */}
          <div className="bg-slate-950/40 border border-slate-800/50 rounded-xl overflow-hidden">
            <div className="px-4 py-2.5 border-b border-slate-800/50 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">Active Findings</span>
              <div className="flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-60" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
                </span>
                <span className="text-[10px] text-slate-500 font-mono">Scan running…</span>
              </div>
            </div>
            <div className="divide-y divide-slate-800/40">
              {vulnRows.map((row, i) => {
                const meta = severityMeta[row.severity] ?? severityMeta.Low;
                return (
                  <div key={i} className="flex items-center gap-3 px-4 py-2.5 hover:bg-slate-800/20 transition-colors">
                    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${meta.dot}`} />
                    <span className="font-mono text-[11px] text-slate-500 w-28 flex-shrink-0">{row.cve}</span>
                    <span className="text-xs text-slate-300 flex-1 min-w-0 truncate">{row.name}</span>
                    <span className="text-[11px] text-slate-500 font-mono hidden sm:block w-24 flex-shrink-0 truncate">{row.asset}</span>
                    <span className="text-[11px] font-mono text-slate-400 w-8 text-right flex-shrink-0">{row.cvss}</span>
                    <span className={`text-[10px] font-bold flex-shrink-0 ${meta.color}`}>{row.severity}</span>
                    <span className={`hidden sm:block text-[10px] font-medium flex-shrink-0 px-1.5 py-0.5 rounded ${row.status === "Patched" ? "text-emerald-400 bg-emerald-500/10" : "text-slate-400 bg-slate-800/50"}`}>
                      {row.status}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          {/* AI strip */}
          <div className="flex items-start gap-3 bg-blue-500/8 border border-blue-500/20 rounded-xl px-3.5 py-3">
            <Brain className="w-4 h-4 text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-semibold text-blue-300">AI Risk Analysis</p>
              <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">
                CVE-2024-3400 on <span className="text-orange-400 font-mono">firewall-01</span> is actively exploited in the wild. Patch immediately — exposure time increases risk of lateral movement.
              </p>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function Hero() {
  return (
    <section id="hero" className="relative min-h-screen flex flex-col justify-center overflow-hidden pt-20">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[900px] h-[600px] bg-gradient-to-b from-blue-600/8 to-transparent rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-16 right-0 w-80 h-80 bg-purple-600/6 rounded-full blur-3xl pointer-events-none" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <div className="flex flex-col items-center text-center gap-7">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10">
            <ScanLine className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-xs font-semibold text-blue-400 tracking-wide">AI-POWERED VULNERABILITY ASSESSMENT</span>
          </motion.div>

          <motion.h1 initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.08 }}
            className="text-5xl sm:text-6xl lg:text-7xl font-black leading-[1.05] tracking-tight max-w-4xl">
            <span className="text-white">Find the vulnerabilities</span>
            <br className="hidden sm:block" />
            <span className="text-white"> that </span>
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-blue-300 to-purple-400">actually matter.</span>
          </motion.h1>

          <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.16 }}
            className="text-lg sm:text-xl text-slate-400 max-w-2xl leading-relaxed">
            VulnAssess gives startups and small security teams automated vulnerability scanning,
            AI-powered risk prioritization, and clear remediation steps — without needing a
            full-time security engineer.
          </motion.p>

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.24 }}
            className="flex flex-col sm:flex-row items-center gap-3">
            <PrimaryButton to="/register" size="md" icon={<Shield className="w-4 h-4" />}>
              Start Security Assessment
            </PrimaryButton>
            <Link to="/demo"
              className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-slate-300 hover:text-white border border-slate-700/60 hover:border-slate-600 bg-slate-900/50 hover:bg-slate-800/50 transition-all duration-200">
              <Eye className="w-4 h-4" />
              Explore Demo
            </Link>
          </motion.div>

          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 0.38 }}
            className="text-xs text-slate-600 flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500/60" />
            No credit card required · Free tier available · First scan in under 2 minutes
          </motion.p>

          <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.44, ease: "easeOut" }}
            className="w-full max-w-4xl mt-4">
            <DashboardPreview />
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. TRUST STRIP
// ─────────────────────────────────────────────────────────────────────────────
const trustItems = [
  { icon: Brain,      label: "AI-Assisted Analysis"       },
  { icon: BarChart2,  label: "CVSS-Based Prioritization"  },
  { icon: ScanLine,   label: "Automated Assessment"       },
  { icon: Target,     label: "Asset-Level Visibility"     },
  { icon: FileText,   label: "Automated Reporting"        },
  { icon: ListChecks, label: "Remediation Guidance"       },
];

function TrustStrip() {
  const { ref, inView } = useReveal();
  return (
    <section className="relative border-y border-slate-800/40 py-10 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-slate-950 via-slate-900/30 to-slate-950 pointer-events-none" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.p ref={ref} initial={{ opacity: 0 }} animate={inView ? { opacity: 1 } : {}} transition={{ duration: 0.5 }}
          className="text-center text-xs font-semibold text-slate-600 uppercase tracking-widest mb-7">
          What VulnAssess covers
        </motion.p>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-4">
          {trustItems.map((item, i) => {
            const Icon = item.icon;
            return (
              <motion.div key={item.label} initial={{ opacity: 0, y: 12 }} animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.4, delay: i * 0.06 }} className="flex flex-col items-center gap-2 text-center">
                <Icon className="w-5 h-5 text-slate-500" strokeWidth={1.5} />
                <span className="text-xs text-slate-500 font-medium leading-snug">{item.label}</span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. PROBLEM → SOLUTION
// ─────────────────────────────────────────────────────────────────────────────
const problems = [
  { icon: AlertTriangle, problem: "Scanner noise you can't triage",         solution: "AI filters findings by real-world exploitability, not just CVSS numbers.",                   solutionIcon: Brain    },
  { icon: Search,        problem: "No visibility into your asset inventory",solution: "Automated discovery maps every exposed asset — known and unknown.",                          solutionIcon: Radar    },
  { icon: ClipboardList, problem: "Advisories that don't tell you what to do",solution:"Step-by-step remediation playbooks generated for your exact environment.",                  solutionIcon: Wrench   },
  { icon: FileText,      problem: "Reporting takes hours of manual work",    solution: "Executive and technical reports generated automatically after each scan.",                   solutionIcon: FileText },
];

function ProblemSolution() {
  const { ref, inView } = useReveal(0.1);
  return (
    <section id="features" className="relative py-20 lg:py-28 overflow-hidden">
      <div className="absolute right-0 top-1/2 -translate-y-1/2 w-[400px] h-[400px] bg-orange-600/4 rounded-full blur-3xl pointer-events-none" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div ref={ref} initial={{ opacity: 0, y: 20 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.5 }}
          className="text-center mb-14">
          <p className="text-orange-400 text-sm font-semibold uppercase tracking-widest mb-3">The Problem</p>
          <h2 className="text-4xl sm:text-5xl font-black text-white tracking-tight">Security tools weren't built for small teams.</h2>
          <p className="text-slate-400 text-lg mt-4 max-w-2xl mx-auto leading-relaxed">
            Scanners flood you with hundreds of findings. Advisories give you CVE IDs without context.
            Prioritization is guesswork. VulnAssess changes that.
          </p>
        </motion.div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {problems.map((item, i) => {
            const ProbIcon = item.icon;
            const SolIcon = item.solutionIcon;
            return (
              <motion.div key={item.problem} initial={{ opacity: 0, y: 30 }} animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5, delay: i * 0.09 }}
                className="bg-slate-900/40 border border-slate-800/50 rounded-2xl p-5 hover:border-slate-700/60 transition-colors duration-200">
                <div className="flex items-start gap-3 pb-4 border-b border-slate-800/40">
                  <div className="flex-shrink-0 p-2 rounded-lg bg-red-500/10"><ProbIcon className="w-4 h-4 text-red-400" /></div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">The problem</p>
                    <p className="text-sm text-slate-300 font-medium">{item.problem}</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 pt-4">
                  <div className="flex-shrink-0 p-2 rounded-lg bg-emerald-500/10"><SolIcon className="w-4 h-4 text-emerald-400" /></div>
                  <div>
                    <p className="text-xs font-semibold text-emerald-500/80 uppercase tracking-wider mb-1">VulnAssess solves it</p>
                    <p className="text-sm text-slate-300">{item.solution}</p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. HOW IT WORKS
// ─────────────────────────────────────────────────────────────────────────────
const steps = [
  { number: "01", icon: Radar,    title: "Discover",    color: "text-blue-400",   bg: "bg-blue-500/10",   borderColor: "border-blue-500/30",   description: "Connect your domain or IP ranges. VulnAssess enumerates assets automatically — subdomains, open ports, services, and tech stack."                                          },
  { number: "02", icon: ScanLine, title: "Analyze",     color: "text-purple-400", bg: "bg-purple-500/10", borderColor: "border-purple-500/30", description: "Vulnerability scanning runs against every discovered asset. CVE matching, CVSS scoring, and service fingerprinting happen automatically."                          },
  { number: "03", icon: Target,   title: "Prioritize",  color: "text-orange-400", bg: "bg-orange-500/10", borderColor: "border-orange-500/30", description: "The AI layer filters scanner noise and ranks findings by real-world risk — exploitability, exposure, and your specific environment."                              },
  { number: "04", icon: Wrench,   title: "Remediate",   color: "text-emerald-400",bg: "bg-emerald-500/10",borderColor: "border-emerald-500/30",description: "For each finding, VulnAssess generates specific remediation steps and tracks resolution. Export a full report when you're done."                                 },
];

function HowItWorks() {
  const { ref, inView } = useReveal(0.1);
  return (
    <section id="how-it-works" className="relative py-20 lg:py-28">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-900/20 to-transparent pointer-events-none" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div ref={ref} initial={{ opacity: 0, y: 20 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.5 }}
          className="text-center mb-14">
          <p className="text-blue-400 text-sm font-semibold uppercase tracking-widest mb-3">Workflow</p>
          <h2 className="text-4xl sm:text-5xl font-black text-white tracking-tight">From zero to assessed in minutes.</h2>
          <p className="text-slate-400 text-lg mt-4 max-w-xl mx-auto">No agents to install. No complex configuration. Connect and scan.</p>
        </motion.div>
        <div className="relative grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="hidden lg:block absolute top-10 left-[12.5%] right-[12.5%] h-px bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-emerald-500/20" />
          {steps.map((step, i) => {
            const Icon = step.icon;
            return (
              <motion.div key={step.title} initial={{ opacity: 0, y: 30 }} animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.5, delay: 0.1 + i * 0.1 }}
                className={`relative bg-slate-900/50 border ${step.borderColor} backdrop-blur-md rounded-2xl p-5 flex flex-col gap-3`}>
                <div className="flex items-center justify-between">
                  <div className={`p-2.5 rounded-xl ${step.bg}`}><Icon className={`w-5 h-5 ${step.color}`} strokeWidth={1.75} /></div>
                  <span className={`text-2xl font-black ${step.color} opacity-20`}>{step.number}</span>
                </div>
                <div>
                  <h3 className={`font-bold text-lg ${step.color}`}>{step.title}</h3>
                  <p className="text-slate-400 text-sm mt-1.5 leading-relaxed">{step.description}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. FEATURES GRID
// ─────────────────────────────────────────────────────────────────────────────
const features = [
  { icon: Radar,      color: "text-blue-400",   bg: "bg-blue-500/10",   border: "hover:border-blue-500/40",   title: "Automated Vulnerability Assessment", description: "Schedule recurring scans or trigger on demand. VulnAssess covers your entire perimeter without manual configuration for each target."                               },
  { icon: Brain,      color: "text-purple-400", bg: "bg-purple-500/10", border: "hover:border-purple-500/40", title: "AI Risk Analysis",                   description: "The AI layer reads each vulnerability in context — your stack, exposure, and current threat intelligence — to separate real risk from scanner noise."         },
  { icon: BarChart2,  color: "text-orange-400", bg: "bg-orange-500/10", border: "hover:border-orange-500/40", title: "CVSS-Based Prioritization",          description: "Every finding is scored using CVSS v3 with environmental adjustments. See Critical, High, Medium, and Low findings ranked by actionability."                },
  { icon: Globe,      color: "text-cyan-400",   bg: "bg-cyan-500/10",   border: "hover:border-cyan-500/40",   title: "Asset Discovery",                    description: "Automatically enumerate subdomains, IPs, open ports, running services, and software versions across your entire internet-exposed surface."                  },
  { icon: Search,     color: "text-indigo-400", bg: "bg-indigo-500/10", border: "hover:border-indigo-500/40", title: "Vulnerability Intelligence",          description: "Each CVE is enriched with public exploit availability, patch status, affected version ranges, and vendor advisory links — all in one place."              },
  { icon: Wrench,     color: "text-emerald-400",bg: "bg-emerald-500/10",border: "hover:border-emerald-500/40",title: "Remediation Guidance",               description: "Concrete fix instructions per finding: package versions to install, configuration changes to make, and verification steps to confirm the patch worked." },
  { icon: Activity,   color: "text-yellow-400", bg: "bg-yellow-500/10", border: "hover:border-yellow-500/40", title: "Security Health Scoring",            description: "Track your overall security posture as a score over time. Spot regressions immediately and demonstrate improvement to stakeholders."                    },
  { icon: FileText,   color: "text-rose-400",   bg: "bg-rose-500/10",   border: "hover:border-rose-500/40",   title: "Automated Security Reports",         description: "Export PDF/DOCX reports in two formats: an executive summary with risk posture and trends, and a technical report with full CVE details."          },
];

function FeatureCard({ feature, index }: { feature: typeof features[0]; index: number }) {
  const { ref, inView } = useReveal();
  const Icon = feature.icon;
  return (
    <motion.div ref={ref} initial={{ opacity: 0, y: 32 }} animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: (index % 4) * 0.08, ease: "easeOut" }}
      className={`group relative bg-slate-900/40 backdrop-blur-md border border-slate-800/50 ${feature.border} rounded-2xl p-5 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg`}>
      <div className={`inline-flex p-2.5 rounded-xl ${feature.bg} mb-4`}><Icon className={`w-5 h-5 ${feature.color}`} strokeWidth={1.75} /></div>
      <h3 className="text-white font-bold text-[15px] mb-2 leading-snug">{feature.title}</h3>
      <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
    </motion.div>
  );
}

function Features() {
  const { ref, inView } = useReveal();
  return (
    <section className="relative py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div ref={ref} initial={{ opacity: 0, y: 20 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.5 }}
          className="text-center mb-14">
          <p className="text-blue-400 text-sm font-semibold uppercase tracking-widest mb-3">Platform Capabilities</p>
          <h2 className="text-4xl sm:text-5xl font-black text-white tracking-tight">The full assessment lifecycle, automated.</h2>
          <p className="text-slate-400 text-lg mt-4 max-w-2xl mx-auto">Every step from discovery to report is handled in one platform.</p>
        </motion.div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f, i) => <FeatureCard key={f.title} feature={f} index={i} />)}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. AI DIFFERENTIATION
// ─────────────────────────────────────────────────────────────────────────────
const aiCapabilities = [
  { title: "Explains findings in plain language",        body: "Each vulnerability gets an AI-written explanation: what it is, why it matters, and what an attacker could do with it — without requiring you to read the CVE advisory."                                                              },
  { title: "Contextualizes risk for your environment",   body: "The same CVE carries different risk on an internet-facing API vs. an internal dev server. The AI factors in exposure, asset criticality, and exploitability before assigning priority."                                              },
  { title: "Generates specific remediation steps",       body: "Rather than linking to an advisory, VulnAssess generates the exact commands and configuration changes needed for your OS, package manager, and runtime version."                                                                     },
  { title: "Identifies which findings to fix first",     body: "When you have 47 open vulnerabilities, the AI identifies the 3 that represent the most immediate real-world risk — so your team knows exactly where to start."                                                                      },
];

function AIDifferentiation() {
  const { ref, inView } = useReveal(0.1);
  return (
    <section id="ai" className="relative py-20 lg:py-28 overflow-hidden">
      <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-purple-600/5 rounded-full blur-3xl pointer-events-none" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div ref={ref} className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start">
          <motion.div initial={{ opacity: 0, x: -24 }} animate={inView ? { opacity: 1, x: 0 } : {}} transition={{ duration: 0.6, ease: "easeOut" }}>
            <p className="text-purple-400 text-sm font-semibold uppercase tracking-widest mb-3">AI Layer</p>
            <h2 className="text-4xl sm:text-5xl font-black text-white tracking-tight leading-tight mb-5">
              Not "AI-powered."<br />
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">Concretely useful.</span>
            </h2>
            <p className="text-slate-400 text-lg leading-relaxed mb-8">
              Security tools slap "AI" on everything. Here's exactly what the AI in VulnAssess does.
            </p>
            <div className="space-y-5">
              {aiCapabilities.map((cap, i) => (
                <motion.div key={cap.title} initial={{ opacity: 0, x: -16 }} animate={inView ? { opacity: 1, x: 0 } : {}}
                  transition={{ duration: 0.4, delay: 0.2 + i * 0.1 }} className="flex gap-3">
                  <div className="flex-shrink-0 mt-0.5 w-5 h-5 rounded-full bg-purple-500/20 border border-purple-500/40 flex items-center justify-center">
                    <CheckCheck className="w-3 h-3 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-white font-semibold text-sm">{cap.title}</p>
                    <p className="text-slate-500 text-sm mt-0.5 leading-relaxed">{cap.body}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, x: 24 }} animate={inView ? { opacity: 1, x: 0 } : {}} transition={{ duration: 0.6, delay: 0.1, ease: "easeOut" }}>
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-r from-purple-600/12 to-blue-600/12 rounded-3xl blur-2xl" />
              <div className="relative bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden">
                <div className="flex items-center gap-2.5 px-4 py-3 border-b border-slate-800/60 bg-slate-950/60">
                  <Brain className="w-4 h-4 text-purple-400" />
                  <span className="text-xs font-semibold text-slate-300">AI Analysis — CVE-2024-3400</span>
                </div>
                <div className="p-4 space-y-4 text-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-mono text-xs text-slate-500">CVE-2024-3400 · CVSS 10.0</p>
                      <p className="text-white font-bold mt-0.5">PAN-OS GlobalProtect Command Injection</p>
                    </div>
                    <span className="flex-shrink-0 px-2 py-1 rounded-lg text-xs font-bold text-red-400 bg-red-500/15 border border-red-500/30">CRITICAL</span>
                  </div>
                  <div className="bg-slate-800/40 rounded-xl p-3.5 border border-slate-700/30">
                    <p className="text-[11px] font-semibold text-purple-400 uppercase tracking-wider mb-2">AI Explanation</p>
                    <p className="text-slate-300 text-sm leading-relaxed">
                      This vulnerability allows an unauthenticated attacker to run OS commands on your firewall. In practice this means full device compromise and potential network-wide lateral movement.
                    </p>
                  </div>
                  <div className="bg-orange-500/8 rounded-xl p-3.5 border border-orange-500/20">
                    <p className="text-[11px] font-semibold text-orange-400 uppercase tracking-wider mb-2">Risk Context</p>
                    <p className="text-slate-300 text-sm leading-relaxed">
                      Your <span className="font-mono text-orange-300">firewall-01</span> is internet-facing with GlobalProtect enabled. This vulnerability is under active exploitation. Treat as incident response priority.
                    </p>
                  </div>
                  <div className="bg-emerald-500/8 rounded-xl p-3.5 border border-emerald-500/20">
                    <p className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider mb-2">Remediation Steps</p>
                    <div className="space-y-1.5">
                      {["Upgrade PAN-OS to 11.1.2-h3 or later","Disable GlobalProtect portal if upgrade is not immediately possible","Enable threat signatures 95187 and 95189 if using Threat Prevention"].map((step, j) => (
                        <div key={j} className="flex items-start gap-2">
                          <span className="flex-shrink-0 w-4 h-4 rounded-full bg-emerald-500/20 text-emerald-400 text-[10px] font-bold flex items-center justify-center mt-0.5">{j + 1}</span>
                          <p className="text-slate-300 text-xs leading-relaxed">{step}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. REPORT PREVIEW
// ─────────────────────────────────────────────────────────────────────────────
const reportFindings = [
  { cve: "CVE-2024-3400",  title: "PAN-OS Command Injection",               cvss: "10.0", severity: "Critical", asset: "firewall-01",   status: "Open"   },
  { cve: "CVE-2024-21338", title: "Windows Kernel Elevation of Privilege",  cvss: "7.8",  severity: "High",     asset: "win-ws-07",     status: "Open"   },
  { cve: "CVE-2023-44487", title: "HTTP/2 Rapid Reset Attack",              cvss: "7.5",  severity: "High",     asset: "prod-lb-01",    status: "Open"   },
  { cve: "CVE-2023-38408", title: "OpenSSH Remote Code Execution",          cvss: "6.8",  severity: "Medium",   asset: "api-server-03", status: "Patched"},
  { cve: "CVE-2023-32315", title: "Openfire Authentication Bypass",         cvss: "9.8",  severity: "Critical", asset: "chat-internal", status: "Open"   },
];

function ReportPreview() {
  const { ref, inView } = useReveal(0.1);
  return (
    <section id="reports" className="relative py-20 lg:py-28 overflow-hidden">
      <div className="absolute right-0 top-1/4 w-[500px] h-[500px] bg-blue-600/5 rounded-full blur-3xl pointer-events-none" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div ref={ref} initial={{ opacity: 0, y: 20 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.5 }}
          className="text-center mb-12">
          <p className="text-blue-400 text-sm font-semibold uppercase tracking-widest mb-3">Assessment Reports</p>
          <h2 className="text-4xl sm:text-5xl font-black text-white tracking-tight">Reports your team will actually use.</h2>
          <p className="text-slate-400 text-lg mt-4 max-w-xl mx-auto">Every assessment generates a complete security report automatically. No copy-pasting from scanner outputs.</p>
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 40 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.7, delay: 0.1 }} className="relative">
          <div className="absolute -inset-6 bg-gradient-to-b from-blue-600/8 via-transparent to-purple-600/8 rounded-3xl blur-3xl pointer-events-none" />
          <div className="relative bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden shadow-2xl">
            <div className="bg-slate-950/70 border-b border-slate-800/60 px-5 py-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <FileText className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-bold text-white">Security Assessment Report</span>
                </div>
                <p className="text-xs text-slate-500 font-mono">Target: acme-corp.com · Scan ID: VA-2024-0847 · Generated Aug 8, 2024</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="px-2 py-1 rounded-lg text-xs font-bold text-orange-400 bg-orange-500/15 border border-orange-500/30">C+ · Score 74/100</span>
                <span className="px-2 py-1 rounded-lg text-xs text-slate-400 bg-slate-800/60 border border-slate-700/40">PDF / DOCX Export</span>
              </div>
            </div>
            <div className="p-5 space-y-5">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[{ label: "Total Findings", value: "47", color: "text-white" },{ label: "Critical", value: "5", color: "text-red-400" },{ label: "High", value: "11", color: "text-orange-400" },{ label: "Resolved", value: "8", color: "text-emerald-400" }].map((s) => (
                  <div key={s.label} className="bg-slate-950/50 border border-slate-800/50 rounded-xl p-3 text-center">
                    <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Severity Distribution</p>
                <div className="flex gap-1 h-3 rounded-full overflow-hidden">
                  <div className="bg-red-500" style={{ width: "10.6%" }} /><div className="bg-orange-500" style={{ width: "23.4%" }} /><div className="bg-yellow-500" style={{ width: "38.3%" }} /><div className="bg-blue-500" style={{ width: "27.7%" }} />
                </div>
                <div className="flex gap-4 mt-2">
                  {[{ label: "Critical", color: "bg-red-500", count: 5 },{ label: "High", color: "bg-orange-500", count: 11 },{ label: "Medium", color: "bg-yellow-500", count: 18 },{ label: "Low", color: "bg-blue-500", count: 13 }].map((s) => (
                    <div key={s.label} className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-sm ${s.color}`} />
                      <span className="text-[11px] text-slate-500">{s.label} ({s.count})</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Critical Findings</p>
                <div className="bg-slate-950/40 border border-slate-800/50 rounded-xl overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-slate-800/50">
                          <th className="text-left px-3 py-2 text-slate-600 font-medium">CVE</th>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium hidden sm:table-cell">Finding</th>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium">CVSS</th>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium">Severity</th>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium hidden md:table-cell">Asset</th>
                          <th className="text-left px-3 py-2 text-slate-600 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/30">
                        {reportFindings.map((row, i) => {
                          const meta = severityMeta[row.severity] ?? severityMeta.Low;
                          return (
                            <tr key={i} className="hover:bg-slate-800/20 transition-colors">
                              <td className="px-3 py-2.5 font-mono text-slate-500">{row.cve}</td>
                              <td className="px-3 py-2.5 text-slate-300 hidden sm:table-cell max-w-[180px] truncate">{row.title}</td>
                              <td className="px-3 py-2.5 font-mono text-slate-400">{row.cvss}</td>
                              <td className={`px-3 py-2.5 font-bold ${meta.color}`}>{row.severity}</td>
                              <td className="px-3 py-2.5 font-mono text-slate-500 hidden md:table-cell">{row.asset}</td>
                              <td className={`px-3 py-2.5 font-medium ${row.status === "Patched" ? "text-emerald-400" : "text-slate-400"}`}>{row.status}</td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between pt-1">
                <p className="text-xs text-slate-600">Executive PDF and technical DOCX available for export after each scan</p>
                <Link to="/register" className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors">
                  <span>Generate your report</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 9. BOTTOM CTA  — grid texture removed
// ─────────────────────────────────────────────────────────────────────────────
function BottomCTA() {
  const { ref, inView } = useReveal();
  return (
    <section className="relative py-24 lg:py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-950/50 via-slate-950 to-purple-950/30" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-gradient-to-r from-blue-600/10 to-purple-600/10 rounded-full blur-3xl" />
      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <motion.div ref={ref} initial={{ opacity: 0, y: 28 }} animate={inView ? { opacity: 1, y: 0 } : {}} transition={{ duration: 0.6, ease: "easeOut" }}
          className="space-y-7">
          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white tracking-tight leading-tight">
            Find the vulnerabilities<br />that matter.<br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">Fix what matters first.</span>
          </h2>
          <p className="text-slate-400 text-lg max-w-xl mx-auto leading-relaxed">
            VulnAssess gives small security teams the same visibility as a full enterprise security program — without the overhead.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <PrimaryButton to="/register" size="lg" icon={<Shield className="w-5 h-5" />}>
              Start Security Assessment
            </PrimaryButton>
            <Link to="/demo"
              className="flex items-center gap-2 px-6 py-4 rounded-xl text-base font-semibold text-slate-300 hover:text-white border border-slate-700/60 hover:border-slate-600 bg-slate-900/50 hover:bg-slate-800/50 transition-all duration-200">
              <Eye className="w-4 h-4" />Explore Demo
            </Link>
          </div>
          <p className="text-xs text-slate-600 flex items-center justify-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500/60" />
            Free tier available · No credit card required
          </p>
        </motion.div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 10. FOOTER — all links use Link or proper external <a>
// Real endpoints: /docs (FastAPI Swagger), /health, /v1 — from the repo.
// Real GitHub: https://github.com/sjashwant21/vuln-platform
// ─────────────────────────────────────────────────────────────────────────────
type FooterLink = { label: string; to?: string; href?: string; badge?: string };
const footerSections: Record<string, FooterLink[]> = {
  Product: [
    { label: "Features",          to: "/#features"      },
    { label: "How It Works",      to: "/#how-it-works"  },
    { label: "Start Assessment",  to: "/register"       },
    { label: "Log In",            to: "/login"          },
    { label: "Pricing",           to: "/pricing",       badge: "soon" },
  ],
  Resources: [
    { label: "API Documentation", href: "/docs"          },          // real FastAPI Swagger
    { label: "API Health",        href: "/health"        },          // real health endpoint
    { label: "GitHub Repository", href: "https://github.com/sjashwant21/vuln-platform" },
    { label: "NVD CVE Database",  href: "https://nvd.nist.gov/vuln/search" },
  ],
  Platform: [
    { label: "Vulnerability Scanning", to: "/#features"    },
    { label: "AI Risk Analysis",       to: "/#ai"          },
    { label: "Assessment Reports",     to: "/#reports"     },
    { label: "CVSS Prioritization",    to: "/#features"    },
    { label: "Asset Discovery",        to: "/#features"    },
  ],
  Security: [
    { label: "Security Policy",         to: "/security",           badge: "soon" },
    { label: "Responsible Disclosure",  to: "/security/disclosure",badge: "soon" },
    { label: "Data Handling",           to: "/security/data",      badge: "soon" },
    { label: "Auth Docs",               href: "/docs#/auth"        },
  ],
  Legal: [
    { label: "Privacy Policy",    to: "/privacy",  badge: "soon" },
    { label: "Terms of Service",  to: "/terms",    badge: "soon" },
    { label: "Open Source",       href: "https://github.com/sjashwant21/vuln-platform" },
  ],
};

const stackBadges = ["FastAPI", "React + Vite", "Groq AI", "PostgreSQL", "Celery + Redis"];

function FooterLink({ link }: { link: FooterLink }) {
  const cls = "group flex items-center gap-1.5 text-slate-500 hover:text-slate-300 text-sm transition-colors duration-200";
  const badge = link.badge ? (
    <span className="text-[9px] font-bold text-slate-700 bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded">{link.badge}</span>
  ) : null;

  if (link.href) {
    const isExternal = link.href.startsWith("http");
    return (
      <a href={link.href} target={isExternal ? "_blank" : undefined}
        rel={isExternal ? "noopener noreferrer" : undefined} className={cls}>
        {link.label}{badge}
      </a>
    );
  }
  return (
    <Link to={link.to!} className={cls}>{link.label}{badge}</Link>
  );
}

function Footer() {
  return (
    <footer className="border-t border-slate-800/50 bg-slate-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-14 pb-10">
        <div className="grid grid-cols-2 md:grid-cols-6 gap-8 mb-12">
          {/* Brand */}
          <div className="col-span-2 md:col-span-1 flex flex-col gap-4">
            <Logo size="sm" />
            <p className="text-slate-500 text-sm leading-relaxed">
              AI-powered vulnerability assessment. FastAPI backend, React + Vite frontend, Groq AI analysis.
            </p>
            <div className="flex items-center gap-2">
              <a href="https://github.com/sjashwant21/vuln-platform" target="_blank" rel="noopener noreferrer" aria-label="GitHub"
                className="w-7 h-7 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-center text-slate-500 hover:text-white hover:border-slate-600 transition-all duration-200">
                <Github className="w-3.5 h-3.5" />
              </a>
              <a href="#" aria-label="Twitter"
                className="w-7 h-7 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-center text-slate-500 hover:text-white hover:border-slate-600 transition-all duration-200">
                <Twitter className="w-3.5 h-3.5" />
              </a>
              <a href="#" aria-label="LinkedIn"
                className="w-7 h-7 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-center text-slate-500 hover:text-white hover:border-slate-600 transition-all duration-200">
                <Linkedin className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* Columns */}
          {Object.entries(footerSections).map(([category, links]) => (
            <div key={category}>
              <p className="text-white font-semibold text-xs uppercase tracking-wider mb-4">{category}</p>
              <ul className="space-y-2.5">
                {links.map((link) => (
                  <li key={link.label}><FooterLink link={link} /></li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Stack row */}
        <div className="flex flex-wrap items-center gap-2 pb-8 border-b border-slate-800/40">
          <span className="text-[11px] text-slate-700 font-medium uppercase tracking-wider mr-1">Built with</span>
          {stackBadges.map((b) => (
            <span key={b} className="text-[10px] font-mono font-medium text-slate-600 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded">{b}</span>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-slate-700 text-xs">
            © {new Date().getFullYear()} VulnAssess · Built by{" "}
            <a href="https://github.com/sjashwant21" target="_blank" rel="noopener noreferrer"
              className="text-slate-600 hover:text-slate-400 transition-colors">@sjashwant21</a>
          </p>
          <div className="flex items-center gap-5">
            <a href="/health" className="flex items-center gap-1.5 text-xs text-slate-700 hover:text-slate-500 transition-colors" title="API health endpoint">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/60" />API health
            </a>
            <a href="/docs" className="text-xs text-slate-700 hover:text-slate-500 transition-colors font-mono">/docs</a>
            <a href="https://github.com/sjashwant21/vuln-platform" target="_blank" rel="noopener noreferrer"
              className="text-xs text-slate-700 hover:text-slate-500 transition-colors">Open Source</a>
          </div>
        </div>
      </div>
    </footer>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ROOT EXPORT
// ─────────────────────────────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white antialiased selection:bg-blue-500/30 selection:text-blue-200">
      <div className="fixed inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_90%_40%_at_50%_-10%,rgba(59,130,246,0.07),transparent)]" />
      </div>
      <Navbar />
      <main id="main-content">
        <Hero />
        <TrustStrip />
        <ProblemSolution />
        <HowItWorks />
        <Features />
        <AIDifferentiation />
        <ReportPreview />
        <BottomCTA />
      </main>
      <Footer />
    </div>
  );
}
