import { useState, useEffect, useRef } from "react";
import { motion, useAnimation, useInView, useScroll, useTransform } from "framer-motion";
import {
  Shield,
  Radar,
  Brain,
  Wrench,
  FileText,
  Terminal,
  ChevronRight,
  ArrowRight,
  Github,
  Twitter,
  Linkedin,
  Lock,
  Activity,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Cpu,
  Globe,
  BookOpen,
  Zap,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Utility: scroll-reveal hook
// ─────────────────────────────────────────────────────────────────────────────
function useReveal(threshold = 0.15) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "0px 0px -60px 0px" });
  return { ref, inView };
}

// ─────────────────────────────────────────────────────────────────────────────
// 1. NAVBAR
// ─────────────────────────────────────────────────────────────────────────────
function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
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
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <div className="absolute inset-0 bg-blue-500/30 rounded-lg blur-sm" />
              <div className="relative bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg p-1.5">
                <Shield className="w-5 h-5 text-white" strokeWidth={2.5} />
              </div>
            </div>
            <span className="text-white font-bold text-lg tracking-tight">
              Vuln<span className="text-blue-400">Assess</span>
            </span>
          </div>

          {/* Nav links */}
          <div className="hidden md:flex items-center gap-8">
            {["Features", "Docs", "Pricing", "Blog"].map((item) => (
              <a
                key={item}
                href="#"
                className="text-slate-400 hover:text-white text-sm font-medium transition-colors duration-200"
              >
                {item}
              </a>
            ))}
          </div>

          {/* CTA */}
          <div className="flex items-center gap-3">
            <a
              href="/login"
              className="hidden sm:block text-slate-400 hover:text-white text-sm font-medium transition-colors duration-200"
            >
              Log In
            </a>
            <a
              href="/register"
              className="relative group flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold text-white overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-blue-500 transition-all duration-300 group-hover:from-blue-500 group-hover:to-blue-400" />
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 bg-[radial-gradient(ellipse_at_center,_rgba(147,197,253,0.15)_0%,_transparent_70%)]" />
              <span className="relative">Start Scanning</span>
              <ChevronRight className="relative w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </div>
    </motion.nav>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 2. HERO
// ─────────────────────────────────────────────────────────────────────────────
function DashboardPreview() {
  const metrics = [
    { label: "Critical", value: "3", color: "text-orange-400", bg: "bg-orange-500/10 border-orange-500/20" },
    { label: "High", value: "11", color: "text-yellow-400", bg: "bg-yellow-500/10 border-yellow-500/20" },
    { label: "Patched", value: "47", color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
  ];

  const bars = [40, 65, 50, 75, 60, 85, 94];

  return (
    <motion.div
      animate={{ y: [0, -8, 0] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      className="relative w-full max-w-2xl mx-auto"
    >
      {/* Glow behind window */}
      <div className="absolute -inset-4 bg-gradient-to-r from-blue-600/20 via-purple-600/10 to-blue-600/20 rounded-3xl blur-2xl" />

      <div className="relative bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden shadow-2xl shadow-black/50">
        {/* Window bar */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800/60 bg-slate-950/50">
          <div className="w-3 h-3 rounded-full bg-red-500/70" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
          <div className="w-3 h-3 rounded-full bg-emerald-500/70" />
          <div className="ml-3 flex-1 bg-slate-800/60 rounded-md px-3 py-1 text-xs text-slate-500 font-mono">
            vulnassess.io/dashboard
          </div>
          <Lock className="w-3.5 h-3.5 text-emerald-400" />
        </div>

        {/* Dashboard body */}
        <div className="p-5 space-y-5">
          {/* Score row */}
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-slate-500 uppercase tracking-widest font-medium">Security Score</p>
              <div className="flex items-end gap-2 mt-1">
                <span className="text-4xl font-black text-white">94</span>
                <span className="text-lg font-bold text-emerald-400 mb-1">/100</span>
                <span className="mb-1.5 px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">A</span>
              </div>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-500 uppercase tracking-widest font-medium">Assets Monitored</p>
              <p className="text-2xl font-bold text-white mt-1">1,284</p>
              <p className="text-xs text-emerald-400 flex items-center gap-1 justify-end mt-0.5">
                <TrendingUp className="w-3 h-3" /> +12 this week
              </p>
            </div>
          </div>

          {/* Metric pills */}
          <div className="grid grid-cols-3 gap-2">
            {metrics.map((m) => (
              <div key={m.label} className={`border rounded-xl p-3 ${m.bg}`}>
                <p className={`text-xl font-black ${m.color}`}>{m.value}</p>
                <p className="text-xs text-slate-500 mt-0.5">{m.label}</p>
              </div>
            ))}
          </div>

          {/* Trend chart */}
          <div>
            <p className="text-xs text-slate-500 uppercase tracking-widest font-medium mb-2">Score trend — 7 days</p>
            <div className="flex items-end gap-1 h-12">
              {bars.map((h, i) => (
                <motion.div
                  key={i}
                  initial={{ height: 0 }}
                  animate={{ height: `${h}%` }}
                  transition={{ duration: 0.6, delay: i * 0.07, ease: "easeOut" }}
                  className="flex-1 rounded-t-sm bg-gradient-to-t from-blue-600/60 to-blue-400/40"
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
            <div className="flex justify-between mt-1">
              {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => (
                <span key={i} className="text-[10px] text-slate-600 flex-1 text-center">{d}</span>
              ))}
            </div>
          </div>

          {/* Active scan */}
          <div className="flex items-center justify-between py-2 border-t border-slate-800/40">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
              </span>
              <span className="text-xs text-slate-400 font-mono">Scanning prod-cluster-03...</span>
            </div>
            <span className="text-xs font-bold text-emerald-400">LIVE</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function Hero() {
  return (
    <section className="relative min-h-screen flex flex-col justify-center overflow-hidden pt-20">
      {/* Ambient background blobs */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-gradient-radial from-blue-600/10 to-transparent rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-10 right-10 w-96 h-96 bg-purple-600/8 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-20 left-10 w-64 h-64 bg-blue-500/8 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 lg:py-32">
        <div className="flex flex-col items-center text-center gap-8">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10"
          >
            <Zap className="w-3.5 h-3.5 text-blue-400" />
            <span className="text-xs font-semibold text-blue-400 tracking-wide">AI-POWERED VULNERABILITY MANAGEMENT</span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-5xl sm:text-6xl lg:text-7xl font-black leading-[1.05] tracking-tight max-w-4xl"
          >
            <span className="text-white">Securing your</span>
            <br />
            <span className="text-white">infrastructure at</span>
            <br />
            <span className="text-white">the speed of </span>
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-blue-300 to-purple-400">
              AI.
            </span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="text-lg sm:text-xl text-slate-400 max-w-2xl leading-relaxed"
          >
            Automate asset discovery, correlate threats in real time, and generate
            remediation plans that engineers can act on immediately.
          </motion.p>

          {/* CTA buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center gap-3"
          >
            <a
              href="/register"
              className="group relative flex items-center gap-2 px-7 py-3.5 rounded-xl text-sm font-bold text-white overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-blue-500" />
              <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 shadow-[inset_0_0_20px_rgba(147,197,253,0.2)]" />
              <div className="absolute inset-0 rounded-xl ring-1 ring-inset ring-blue-400/20 group-hover:ring-blue-400/40 transition-all duration-300" />
              <span className="relative">Get Started Free</span>
              <ArrowRight className="relative w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200" />
              {/* Glow effect */}
              <div className="absolute -inset-0.5 bg-blue-500/20 blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300 -z-10" />
            </a>
            <a
              href="/docs"
              className="flex items-center gap-2 px-7 py-3.5 rounded-xl text-sm font-semibold text-slate-300 hover:text-white border border-slate-700/60 hover:border-slate-600 bg-slate-900/50 hover:bg-slate-800/50 transition-all duration-200"
            >
              <BookOpen className="w-4 h-4" />
              View Documentation
            </a>
          </motion.div>

          {/* Trust line */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.45 }}
            className="text-xs text-slate-600 flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500/70" />
            No credit card required · SOC 2 Type II · Scans start in under 60 seconds
          </motion.p>

          {/* Dashboard Preview */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5, ease: "easeOut" }}
            className="w-full mt-4"
          >
            <DashboardPreview />
          </motion.div>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. FEATURES GRID
// ─────────────────────────────────────────────────────────────────────────────
const features = [
  {
    icon: Radar,
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "hover:border-blue-500/50",
    glow: "group-hover:shadow-blue-500/10",
    title: "Automated Attack Surface Discovery",
    description:
      "Continuously enumerate every internet-facing asset — domains, subdomains, IPs, open ports, and cloud services — without any manual seed data. Rogue assets surface before adversaries find them.",
  },
  {
    icon: Brain,
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    border: "hover:border-purple-500/50",
    glow: "group-hover:shadow-purple-500/10",
    title: "AI-Powered Threat Correlation",
    description:
      "Our LLM cross-references active CVEs, CVSS scores, and your specific stack to eliminate false positives — delivering a prioritized threat list ranked by real-world exploitability, not just severity.",
  },
  {
    icon: Wrench,
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "hover:border-emerald-500/50",
    glow: "group-hover:shadow-emerald-500/10",
    title: "Actionable Remediation Playbooks",
    description:
      "Stop reading advisories and start patching. VulnAssess generates environment-aware, step-by-step bash and Ansible scripts your engineers can run immediately — with rollback instructions included.",
  },
  {
    icon: FileText,
    color: "text-orange-400",
    bg: "bg-orange-500/10",
    border: "hover:border-orange-500/50",
    glow: "group-hover:shadow-orange-500/10",
    title: "One-Click Executive Reports",
    description:
      "Export pixel-perfect PDF reports in two modes: an Executive Summary for the C-Suite with risk posture and trend lines, and a Technical Deep Dive with full CVE details for your engineering team.",
  },
];

function FeatureCard({ feature, index }: { feature: typeof features[0]; index: number }) {
  const { ref, inView } = useReveal();
  const Icon = feature.icon;

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.1, ease: "easeOut" }}
      className={`group relative bg-slate-900/50 backdrop-blur-md border border-slate-800/50 ${feature.border} rounded-2xl p-6 transition-all duration-300 hover:-translate-y-1 hover:shadow-xl ${feature.glow}`}
    >
      <div className={`inline-flex p-3 rounded-xl ${feature.bg} mb-4`}>
        <Icon className={`w-6 h-6 ${feature.color}`} strokeWidth={1.75} />
      </div>
      <h3 className="text-white font-bold text-lg mb-2 leading-snug">{feature.title}</h3>
      <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-slate-700/50 to-transparent" />
    </motion.div>
  );
}

function Features() {
  const { ref, inView } = useReveal();

  return (
    <section className="relative py-24 lg:py-32">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-slate-900/30 to-transparent pointer-events-none" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <p className="text-blue-400 text-sm font-semibold uppercase tracking-widest mb-3">Platform Capabilities</p>
          <h2 className="text-4xl sm:text-5xl font-black text-white tracking-tight">
            Everything your SecOps team needs
          </h2>
          <p className="text-slate-400 text-lg mt-4 max-w-2xl mx-auto">
            From discovery to patch, VulnAssess closes the loop on the entire vulnerability lifecycle without stitching together five different tools.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {features.map((f, i) => (
            <FeatureCard key={f.title} feature={f} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. AI SPOTLIGHT
// ─────────────────────────────────────────────────────────────────────────────
const chatMessages = [
  {
    role: "user",
    text: "Analyze CVE-2023-44487 impact on our stack.",
  },
  {
    role: "ai",
    text: (
      <>
        <span className="text-emerald-400 font-semibold">CVE-2023-44487</span> (HTTP/2 Rapid Reset) affects your{" "}
        <span className="text-blue-400">nginx/1.22.1</span> on{" "}
        <span className="text-orange-400">prod-lb-01</span> and{" "}
        <span className="text-orange-400">prod-lb-02</span>. CVSS 7.5 — High.
        Upgrading to <span className="text-emerald-400">nginx 1.24.0</span> patches this immediately.
      </>
    ),
  },
  {
    role: "ai",
    text: (
      <>
        Here's the remediation script:
        <div className="mt-2 bg-slate-950/80 border border-slate-700/40 rounded-lg p-3 font-mono text-xs text-emerald-300 leading-relaxed">
          <span className="text-slate-500"># Patch prod load balancers</span>
          <br />
          <span className="text-blue-400">apt-get update</span>{" && "}
          <span className="text-blue-400">apt-get install</span>{" "}
          <span className="text-yellow-300">nginx=1.24.0-1~jammy</span>
          <br />
          <span className="text-blue-400">nginx -t</span>{" && "}
          <span className="text-blue-400">systemctl reload nginx</span>
          <br />
          <span className="text-slate-500"># Verify patch applied</span>
          <br />
          <span className="text-blue-400">nginx -v</span>
          <br />
          <span className="text-emerald-400"># Expected: nginx version nginx/1.24.0</span>
        </div>
      </>
    ),
  },
];

function AISpotlight() {
  const { ref, inView } = useReveal(0.1);

  return (
    <section className="relative py-24 lg:py-32 overflow-hidden">
      {/* Background accent */}
      <div className="absolute top-1/2 left-0 -translate-y-1/2 w-[500px] h-[500px] bg-purple-600/6 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 right-0 -translate-y-1/2 w-96 h-96 bg-blue-600/6 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div ref={ref} className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 items-center">
          {/* Left: copy */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            <p className="text-purple-400 text-sm font-semibold uppercase tracking-widest mb-3">AI Intelligence Layer</p>
            <h2 className="text-4xl sm:text-5xl font-black text-white tracking-tight leading-tight mb-6">
              Your team's AI
              <br />
              security analyst,
              <br />
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-blue-400">
                never offline.
              </span>
            </h2>
            <p className="text-slate-400 text-lg leading-relaxed mb-8">
              Traditional scanners flood your queue with noise. Our LLM correlates
              CVE data, your actual infrastructure, and threat intelligence feeds to
              surface only what genuinely needs attention.
            </p>

            <div className="space-y-4">
              {[
                {
                  icon: AlertTriangle,
                  color: "text-orange-400",
                  bg: "bg-orange-500/10",
                  title: "Noise eliminated at the source",
                  desc: "97% false-positive reduction means your team only patches real threats.",
                },
                {
                  icon: Activity,
                  color: "text-blue-400",
                  bg: "bg-blue-500/10",
                  title: "Saves 20 hours per engineer, per week",
                  desc: "Triaging CVEs is now automatic. Engineers ship fixes, not spreadsheets.",
                },
                {
                  icon: Cpu,
                  color: "text-emerald-400",
                  bg: "bg-emerald-500/10",
                  title: "Context-aware remediation",
                  desc: "Scripts generated for your exact OS, package manager, and deployment pipeline.",
                },
              ].map((item) => {
                const ItemIcon = item.icon;
                return (
                  <div key={item.title} className="flex items-start gap-4">
                    <div className={`flex-shrink-0 p-2 rounded-lg ${item.bg}`}>
                      <ItemIcon className={`w-4 h-4 ${item.color}`} />
                    </div>
                    <div>
                      <p className="text-white font-semibold text-sm">{item.title}</p>
                      <p className="text-slate-500 text-sm mt-0.5">{item.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>

          {/* Right: Chat UI */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={inView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.1, ease: "easeOut" }}
          >
            <div className="relative">
              <div className="absolute -inset-4 bg-gradient-to-r from-purple-600/15 to-blue-600/15 rounded-3xl blur-2xl" />
              <div className="relative bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 rounded-2xl overflow-hidden">
                {/* Chat window header */}
                <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800/60 bg-slate-950/50">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-500/70" />
                  </div>
                  <div className="flex items-center gap-2 ml-2">
                    <Brain className="w-4 h-4 text-purple-400" />
                    <span className="text-xs font-semibold text-slate-300">VulnAssess AI</span>
                  </div>
                  <div className="ml-auto flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span className="text-[10px] text-slate-500">Model: va-threat-v3</span>
                  </div>
                </div>

                {/* Chat messages */}
                <div className="p-4 space-y-4 min-h-[320px]">
                  {chatMessages.map((msg, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 10 }}
                      animate={inView ? { opacity: 1, y: 0 } : {}}
                      transition={{ duration: 0.4, delay: 0.4 + i * 0.15 }}
                      className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                    >
                      {msg.role === "ai" && (
                        <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center">
                          <Brain className="w-3.5 h-3.5 text-purple-400" />
                        </div>
                      )}
                      <div
                        className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
                          msg.role === "user"
                            ? "bg-blue-600/30 border border-blue-500/30 text-slate-200"
                            : "bg-slate-800/50 border border-slate-700/40 text-slate-300"
                        }`}
                      >
                        {msg.text}
                      </div>
                      {msg.role === "user" && (
                        <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-slate-700/50 border border-slate-600/50 flex items-center justify-center">
                          <span className="text-[10px] font-bold text-slate-300">SR</span>
                        </div>
                      )}
                    </motion.div>
                  ))}

                  {/* Typing indicator */}
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ duration: 0.4, delay: 1.1 }}
                    className="flex gap-3"
                  >
                    <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-purple-500/20 border border-purple-500/30 flex items-center justify-center">
                      <Brain className="w-3.5 h-3.5 text-purple-400" />
                    </div>
                    <div className="bg-slate-800/50 border border-slate-700/40 rounded-xl px-4 py-3 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "0ms" }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "150ms" }} />
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                  </motion.div>
                </div>

                {/* Chat input */}
                <div className="px-4 pb-4">
                  <div className="flex items-center gap-2 bg-slate-950/60 border border-slate-700/50 rounded-xl px-3 py-2.5">
                    <Terminal className="w-4 h-4 text-slate-600" />
                    <span className="text-sm text-slate-600 flex-1 font-mono">Ask about any CVE or asset...</span>
                    <div className="w-6 h-6 rounded-lg bg-blue-600/50 flex items-center justify-center">
                      <ArrowRight className="w-3 h-3 text-blue-300" />
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
// 5. STATS STRIP
// ─────────────────────────────────────────────────────────────────────────────
function StatsStrip() {
  const { ref, inView } = useReveal();
  const stats = [
    { value: "1.2M+", label: "Vulnerabilities assessed" },
    { value: "97%", label: "False-positive reduction" },
    { value: "20hrs", label: "Saved per engineer/week" },
    { value: "<60s", label: "Time to first scan" },
  ];

  return (
    <section className="relative py-16 border-y border-slate-800/40">
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-900/50 to-transparent pointer-events-none" />
      <div ref={ref} className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          {stats.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: i * 0.1 }}
              className="text-center"
            >
              <p className="text-3xl sm:text-4xl font-black bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
                {s.value}
              </p>
              <p className="text-slate-500 text-sm mt-1">{s.label}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. BOTTOM CTA BANNER
// ─────────────────────────────────────────────────────────────────────────────
function BottomCTA() {
  const { ref, inView } = useReveal();

  return (
    <section className="relative py-24 lg:py-32 overflow-hidden">
      {/* Gradient backdrop */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-950/60 via-slate-950 to-purple-950/40" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[400px] bg-gradient-to-r from-blue-600/12 to-purple-600/12 rounded-full blur-3xl" />

      {/* Grid texture overlay */}
      <div
        className="absolute inset-0 opacity-[0.03]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(148,163,184,1) 1px, transparent 1px), linear-gradient(90deg, rgba(148,163,184,1) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      <div className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="space-y-8"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-orange-500/30 bg-orange-500/10 mb-2">
            <AlertTriangle className="w-3.5 h-3.5 text-orange-400" />
            <span className="text-xs font-semibold text-orange-400 tracking-wide">YOUR ATTACK SURFACE IS GROWING DAILY</span>
          </div>

          <h2 className="text-4xl sm:text-5xl lg:text-6xl font-black text-white tracking-tight leading-tight">
            Ready to harden your
            <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
              attack surface?
            </span>
          </h2>

          <p className="text-slate-400 text-lg max-w-2xl mx-auto leading-relaxed">
            Join 2,000+ security teams who've replaced their manual vulnerability
            workflows with VulnAssess. Start your first automated scan in under a minute.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <a
              href="/register"
              className="group relative flex items-center gap-2 px-8 py-4 rounded-xl text-base font-bold text-white overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-r from-blue-600 to-purple-600 transition-all duration-300 group-hover:from-blue-500 group-hover:to-purple-500" />
              <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500/40 to-purple-500/40 blur-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300 -z-10" />
              <Shield className="relative w-5 h-5" />
              <span className="relative">Start Scanning for Free</span>
              <ArrowRight className="relative w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200" />
            </a>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <CheckCircle2 className="w-4 h-4 text-emerald-500/70" />
              Free forever for 3 assets. No card required.
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. FOOTER
// ─────────────────────────────────────────────────────────────────────────────
const footerLinks = {
  Product: ["Features", "Pricing", "Changelog", "Roadmap", "Security"],
  Company: ["About", "Blog", "Careers", "Press", "Contact"],
  Legal: ["Privacy Policy", "Terms of Service", "Cookie Policy", "DPA", "SLA"],
};

function Footer() {
  return (
    <footer className="border-t border-slate-800/50 bg-slate-950/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-10">
          {/* Brand column */}
          <div className="col-span-2 md:col-span-2">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-500/20 rounded-lg blur-sm" />
                <div className="relative bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg p-1.5">
                  <Shield className="w-4 h-4 text-white" strokeWidth={2.5} />
                </div>
              </div>
              <span className="text-white font-bold text-base tracking-tight">
                Vuln<span className="text-blue-400">Assess</span>
              </span>
            </div>
            <p className="text-slate-500 text-sm leading-relaxed max-w-xs mb-6">
              AI-powered vulnerability management for modern security teams. Discover, prioritize, and remediate — automatically.
            </p>
            {/* Social icons */}
            <div className="flex items-center gap-3">
              {[
                { icon: Github, href: "#" },
                { icon: Twitter, href: "#" },
                { icon: Linkedin, href: "#" },
              ].map(({ icon: Icon, href }, i) => (
                <a
                  key={i}
                  href={href}
                  className="w-8 h-8 rounded-lg bg-slate-800/60 border border-slate-700/50 flex items-center justify-center text-slate-500 hover:text-white hover:border-slate-600 transition-all duration-200"
                >
                  <Icon className="w-3.5 h-3.5" />
                </a>
              ))}
            </div>
          </div>

          {/* Link columns */}
          {Object.entries(footerLinks).map(([category, links]) => (
            <div key={category}>
              <p className="text-white font-semibold text-sm mb-4">{category}</p>
              <ul className="space-y-2.5">
                {links.map((link) => (
                  <li key={link}>
                    <a
                      href="#"
                      className="text-slate-500 hover:text-slate-300 text-sm transition-colors duration-200"
                    >
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-12 pt-6 border-t border-slate-800/50 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-slate-600 text-xs">
            © {new Date().getFullYear()} VulnAssess, Inc. All rights reserved.
          </p>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 text-xs text-slate-600">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              All systems operational
            </div>
            <span className="text-slate-700 text-xs">SOC 2 Type II Certified</span>
            <Globe className="w-3.5 h-3.5 text-slate-700" />
          </div>
        </div>
      </div>
    </footer>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ROOT EXPORT: LandingPage
// ─────────────────────────────────────────────────────────────────────────────
export default function LandingPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-white antialiased selection:bg-blue-500/30 selection:text-blue-200">
      {/* Persistent background layer */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(59,130,246,0.08),transparent)]" />
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-slate-700/30 to-transparent" />
      </div>

      <Navbar />
      <main>
        <Hero />
        <StatsStrip />
        <Features />
        <AISpotlight />
        <BottomCTA />
      </main>
      <Footer />
    </div>
  );
}
