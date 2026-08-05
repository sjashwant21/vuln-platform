"""
PDF renderer — Jinja2 HTML → xhtml2pdf PDF.

Pipeline:
  ReportData + charts → Jinja2 HTML string → xhtml2pdf → PDF bytes

xhtml2pdf is synchronous. We run it in a thread-pool executor
via asyncio.get_event_loop().run_in_executor() to avoid blocking
the async event loop during rendering (which can take 1-5 seconds).

xhtml2pdf is 100% pure Python (built on ReportLab + html5lib),
so it runs fine in Vercel's serverless environment with no system deps.
"""

from __future__ import annotations

import asyncio
import io
from pathlib import Path
from typing import Any

import structlog

from app.domain.models.report import ReportData, ReportType

logger = structlog.get_logger(__name__)

_TEMPLATE_DIR = Path(__file__).parent.parent / "templates"

_TEMPLATE_MAP = {
    ReportType.EXECUTIVE: "executive.html",
    ReportType.TECHNICAL: "technical.html",
    ReportType.VULNERABILITY: "vulnerability.html",
    ReportType.COMPLIANCE: "compliance.html",
}


class PDFRenderer:
    """Renders ReportData to PDF bytes via Jinja2 + xhtml2pdf."""

    def __init__(self) -> None:
        self._jinja_env = self._make_jinja_env()

    def _make_jinja_env(self) -> Any:
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        return Environment(
            loader=FileSystemLoader(str(_TEMPLATE_DIR)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def render(
        self,
        report_data: ReportData,
        charts: dict[str, str],  # name → SVG string
    ) -> bytes:
        """
        Render ReportData to PDF bytes asynchronously.
        Jinja2 rendering is sync; xhtml2pdf is sync.
        Both run in a thread-pool executor.
        """
        loop = asyncio.get_event_loop()

        # Step 1: render HTML (fast, but Jinja2 is sync)
        html_str = await loop.run_in_executor(None, self._render_html, report_data, charts)

        # Step 2: convert HTML → PDF (slow, CPU-bound)
        pdf_bytes = await loop.run_in_executor(None, self._html_to_pdf, html_str)

        logger.info(
            "pdf_rendered",
            report_type=report_data.report_type.value,
            size_kb=round(len(pdf_bytes) / 1024, 1),
        )
        return pdf_bytes

    def _render_html(self, report_data: ReportData, charts: dict[str, str]) -> str:
        template_name = _TEMPLATE_MAP.get(report_data.report_type, "executive.html")
        template = self._jinja_env.get_template(template_name)
        return template.render(report_data=report_data, charts=charts)

    @staticmethod
    def _html_to_pdf(html_str: str) -> bytes:
        """Convert an HTML string to PDF bytes using xhtml2pdf (pure Python)."""
        from xhtml2pdf import pisa  # noqa: PLC0415

        buf = io.BytesIO()
        result = pisa.CreatePDF(
            src=html_str,
            dest=buf,
            encoding="utf-8",
        )
        if result.err:
            raise RuntimeError(
                f"xhtml2pdf conversion failed with {result.err} error(s). "
                "Check the HTML template for unsupported CSS or malformed markup."
            )
        buf.seek(0)
        return buf.read()

    def render_html_preview(
        self,
        report_data: ReportData,
        charts: dict[str, str],
    ) -> str:
        """Return the raw HTML string (for browser preview without PDF conversion)."""
        return self._render_html(report_data, charts)
