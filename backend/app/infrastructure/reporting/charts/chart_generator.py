"""
ChartGenerator — pure matplotlib SVG/PNG chart generation for PDF reports.

All methods return an SVG string by default (for embedding in HTML/PDF via xhtml2pdf).
Pass as_png=True to get PNG bytes instead (for DOCX embedding).

Uses the Agg non-interactive backend so this works in serverless environments
(no display required).
"""

from __future__ import annotations

import io
from typing import Any

# Use non-interactive Agg backend before any other matplotlib import
import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# ── Colour palette (matches the HTML template) ──────────────────────────────
_COLOURS = {
    "critical": "#DC2626",
    "high":     "#EA580C",
    "medium":   "#D97706",
    "low":      "#2563EB",
    "info":     "#6B7280",
    "ok":       "#16A34A",
    "accent":   "#4F46E5",
    "bg":       "#F9FAFB",
    "border":   "#E5E7EB",
}

_FIG_DPI = 96  # screen-resolution DPI; keeps file sizes small


def _fig_to_svg(fig: plt.Figure) -> str:
    """Render a matplotlib Figure to an SVG string."""
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)
    return buf.getvalue()


def _fig_to_png(fig: plt.Figure) -> bytes:
    """Render a matplotlib Figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=_FIG_DPI, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


class ChartGenerator:
    """Generates report charts as SVG strings or PNG bytes."""

    # ── Health gauge ────────────────────────────────────────────────────────

    def health_gauge(self, score: int | float, *, as_png: bool = False) -> str | bytes:
        """
        Half-donut gauge showing the security health score (0-100).
        Green ≥70, Amber 40-69, Red <40.
        """
        score = max(0, min(100, float(score)))
        colour = (
            _COLOURS["ok"] if score >= 70
            else _COLOURS["medium"] if score >= 40
            else _COLOURS["critical"]
        )

        fig, ax = plt.subplots(figsize=(3.2, 2.0), dpi=_FIG_DPI)
        fig.patch.set_alpha(0)
        ax.set_aspect("equal")
        ax.axis("off")

        # Background arc
        _theta1, _theta2 = 180.0, 0.0  # half-circle, left→right
        filled = score / 100.0

        bg = mpatches.Wedge(
            (0, 0), 1.0, 0, 180, width=0.30,
            facecolor="#E5E7EB", edgecolor="none",
        )
        ax.add_patch(bg)

        # Filled arc
        end_angle = 180 - filled * 180
        fg = mpatches.Wedge(
            (0, 0), 1.0, end_angle, 180, width=0.30,
            facecolor=colour, edgecolor="none",
        )
        ax.add_patch(fg)

        # Score text
        label = (
            "A — Excellent" if score >= 90
            else "B — Good" if score >= 70
            else "C — Fair" if score >= 50
            else "D — Poor" if score >= 30
            else "F — Critical"
        )
        ax.text(0, -0.05, f"{int(score)}", ha="center", va="center",
                fontsize=22, fontweight="bold", color=colour)
        ax.text(0, -0.42, label, ha="center", va="center",
                fontsize=7, color="#374151")
        ax.text(0, 0.55, "Security Health Score", ha="center", va="center",
                fontsize=7, color="#6B7280")

        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-0.6, 1.2)

        return _fig_to_png(fig) if as_png else _fig_to_svg(fig)

    # ── Severity donut ───────────────────────────────────────────────────────

    def severity_donut(
        self,
        dist: dict[str, int],
        *,
        as_png: bool = False,
    ) -> str | bytes:
        """Donut chart of vulnerability severity distribution."""
        keys   = ["critical", "high", "medium", "low", "info"]
        values = [max(0, dist.get(k, 0)) for k in keys]
        colours = [_COLOURS[k] for k in keys]
        labels  = [k.capitalize() for k in keys]

        # Filter zero slices
        filtered = [(v, c, lbl) for v, c, lbl in zip(values, colours, labels) if v > 0]
        if not filtered:
            filtered = [(1, "#E5E7EB", "None")]

        vals, cols, lbls = zip(*filtered)

        fig, ax = plt.subplots(figsize=(3.2, 2.4), dpi=_FIG_DPI)
        fig.patch.set_alpha(0)
        ax.set_aspect("equal")

        wedges, _ = ax.pie(
            vals,
            colors=cols,
            startangle=90,
            wedgeprops={"width": 0.45, "edgecolor": "white", "linewidth": 1.5},
        )

        total = sum(vals)
        ax.text(0, 0, f"{total}\nTotal", ha="center", va="center",
                fontsize=9, fontweight="bold", color="#1F2937")

        ax.legend(
            wedges, [f"{lbl} ({v})" for lbl, v in zip(lbls, vals)],
            loc="lower center", bbox_to_anchor=(0.5, -0.28),
            ncol=3, fontsize=6, frameon=False,
        )
        ax.set_title("Severity Distribution", fontsize=8, color="#374151", pad=4)

        return _fig_to_png(fig) if as_png else _fig_to_svg(fig)

    # ── Risk trend line ──────────────────────────────────────────────────────

    def risk_trend(
        self,
        trend_points: list[dict[str, Any]],
        *,
        as_png: bool = False,
    ) -> str | bytes:
        """Line chart showing vulnerability counts over time."""
        if not trend_points:
            fig, ax = plt.subplots(figsize=(5.0, 2.0), dpi=_FIG_DPI)
            fig.patch.set_alpha(0)
            ax.text(0.5, 0.5, "No trend data available", ha="center", va="center",
                    transform=ax.transAxes, color="#6B7280")
            ax.axis("off")
            return _fig_to_png(fig) if as_png else _fig_to_svg(fig)

        dates = [p.get("date", i) for i, p in enumerate(trend_points)]
        x = list(range(len(dates)))

        fig, ax = plt.subplots(figsize=(5.0, 2.4), dpi=_FIG_DPI)
        fig.patch.set_alpha(0)
        ax.set_facecolor("white")

        for key, colour, label in [
            ("critical", _COLOURS["critical"], "Critical"),
            ("high",     _COLOURS["high"],     "High"),
            ("medium",   _COLOURS["medium"],   "Medium"),
            ("low",      _COLOURS["low"],      "Low"),
        ]:
            vals = [p.get(key, 0) for p in trend_points]
            ax.plot(x, vals, color=colour, linewidth=1.5, label=label, marker="o",
                    markersize=3)

        if len(dates) <= 12:
            ax.set_xticks(x)
            ax.set_xticklabels(
                [str(d)[:10] if hasattr(d, "__str__") else str(d) for d in dates],
                fontsize=5, rotation=30, ha="right",
            )
        ax.tick_params(labelsize=6)
        ax.set_ylabel("Count", fontsize=6, color="#6B7280")
        ax.legend(fontsize=6, loc="upper right", frameon=False)
        ax.set_title("Vulnerability Trend", fontsize=8, color="#374151")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

        return _fig_to_png(fig) if as_png else _fig_to_svg(fig)

    # ── Asset risk bars ──────────────────────────────────────────────────────

    def asset_risk_bars(
        self,
        assets: list[dict[str, Any]],
        *,
        as_png: bool = False,
    ) -> str | bytes:
        """Horizontal bar chart of risk scores per asset."""
        if not assets:
            fig, ax = plt.subplots(figsize=(5.0, 1.5), dpi=_FIG_DPI)
            fig.patch.set_alpha(0)
            ax.text(0.5, 0.5, "No asset data", ha="center", va="center",
                    transform=ax.transAxes, color="#6B7280")
            ax.axis("off")
            return _fig_to_png(fig) if as_png else _fig_to_svg(fig)

        top = sorted(assets, key=lambda a: a.get("risk_score", 0), reverse=True)[:10]
        names  = [a.get("display_name") or a.get("ip_address", "Unknown") for a in top]
        scores = [a.get("risk_score", 0) for a in top]
        colours = [
            _COLOURS["critical"] if s >= 80
            else _COLOURS["high"] if s >= 50
            else _COLOURS["medium"] if s >= 25
            else _COLOURS["low"]
            for s in scores
        ]

        fig_h = max(1.8, 0.35 * len(names))
        fig, ax = plt.subplots(figsize=(5.0, fig_h), dpi=_FIG_DPI)
        fig.patch.set_alpha(0)
        ax.set_facecolor("white")

        y = list(range(len(names)))
        ax.barh(y, scores, color=colours, edgecolor="white", height=0.6)
        ax.set_yticks(y)
        ax.set_yticklabels([n[:22] for n in names], fontsize=6)
        ax.set_xlabel("Risk Score", fontsize=6, color="#6B7280")
        ax.set_xlim(0, 105)
        ax.tick_params(labelsize=6)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_title("Asset Risk Scores", fontsize=8, color="#374151")
        ax.invert_yaxis()

        return _fig_to_png(fig) if as_png else _fig_to_svg(fig)

    # ── Severity by asset stacked bars ──────────────────────────────────────

    def severity_by_asset_stacked(
        self,
        assets: list[dict[str, Any]],
        *,
        as_png: bool = False,
    ) -> str | bytes:
        """Stacked bar chart of critical/high/medium/low per asset."""
        if not assets:
            fig, ax = plt.subplots(figsize=(5.0, 1.5), dpi=_FIG_DPI)
            fig.patch.set_alpha(0)
            ax.axis("off")
            return _fig_to_png(fig) if as_png else _fig_to_svg(fig)

        top = sorted(
            assets,
            key=lambda a: (a.get("vuln_critical", 0) * 4 + a.get("vuln_high", 0) * 3
                           + a.get("vuln_medium", 0) * 2 + a.get("vuln_low", 0)),
            reverse=True,
        )[:10]

        names = [a.get("display_name") or a.get("ip_address", "Unknown") for a in top]
        crit   = [a.get("vuln_critical", 0) for a in top]
        high   = [a.get("vuln_high", 0)     for a in top]
        medium = [a.get("vuln_medium", 0)   for a in top]
        low    = [a.get("vuln_low", 0)      for a in top]

        x = np.arange(len(names))
        fig_h = max(2.0, 0.35 * len(names))
        fig, ax = plt.subplots(figsize=(5.5, fig_h), dpi=_FIG_DPI)
        fig.patch.set_alpha(0)
        ax.set_facecolor("white")

        ax.barh(x, crit,   color=_COLOURS["critical"], label="Critical", height=0.6)
        ax.barh(x, high,   left=crit, color=_COLOURS["high"], label="High", height=0.6)
        ax.barh(x, medium, left=np.add(crit, high), color=_COLOURS["medium"], label="Medium", height=0.6)
        ax.barh(x, low,    left=np.add(np.add(crit, high), medium), color=_COLOURS["low"], label="Low", height=0.6)

        ax.set_yticks(x)
        ax.set_yticklabels([n[:22] for n in names], fontsize=6)
        ax.set_xlabel("Vulnerability Count", fontsize=6, color="#6B7280")
        ax.tick_params(labelsize=6)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=6, loc="lower right", frameon=False)
        ax.set_title("Vulnerabilities by Asset", fontsize=8, color="#374151")
        ax.invert_yaxis()

        return _fig_to_png(fig) if as_png else _fig_to_svg(fig)

    # ── Compliance bars ──────────────────────────────────────────────────────

    def compliance_bars(
        self,
        frameworks: list[dict[str, Any]],
        *,
        as_png: bool = False,
    ) -> str | bytes:
        """Grouped bar chart showing compliance/non-compliant/partial per framework."""
        if not frameworks:
            fig, ax = plt.subplots(figsize=(5.0, 1.5), dpi=_FIG_DPI)
            fig.patch.set_alpha(0)
            ax.axis("off")
            return _fig_to_png(fig) if as_png else _fig_to_svg(fig)

        names       = [f.get("framework", "Unknown") for f in frameworks]
        compliant   = [f.get("compliant", 0)     for f in frameworks]
        non_comp    = [f.get("non_compliant", 0)  for f in frameworks]
        partial     = [f.get("partial", 0)        for f in frameworks]

        x = np.arange(len(names))
        width = 0.28

        fig, ax = plt.subplots(figsize=(5.5, 2.5), dpi=_FIG_DPI)
        fig.patch.set_alpha(0)
        ax.set_facecolor("white")

        ax.bar(x - width, compliant, width, color=_COLOURS["ok"],       label="Compliant")
        ax.bar(x,         partial,   width, color=_COLOURS["medium"],    label="Partial")
        ax.bar(x + width, non_comp,  width, color=_COLOURS["critical"],  label="Non-Compliant")

        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=6, rotation=15, ha="right")
        ax.set_ylabel("Controls", fontsize=6, color="#6B7280")
        ax.tick_params(labelsize=6)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(fontsize=6, frameon=False)
        ax.set_title("Compliance Overview", fontsize=8, color="#374151")

        return _fig_to_png(fig) if as_png else _fig_to_svg(fig)
