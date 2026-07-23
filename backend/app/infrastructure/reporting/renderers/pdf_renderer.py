"""
PDF renderer — Jinja2 HTML → WeasyPrint PDF.

Pipeline:
  ReportData + charts → Jinja2 HTML string → WeasyPrint → PDF bytes

WeasyPrint is synchronous. We run it in a thread-pool executor
via asyncio.get_event_loop().run_in_executor() to avoid blocking
the async event loop during rendering (which can take 1-5 seconds).

Font embedding: WeasyPrint bundles DejaVu fonts so PDFs are self-contained
and render consistently across platforms.
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
    ReportType.EXECUTIVE:     "executive.html",
    ReportType.TECHNICAL:     "technical.html",
    ReportType.VULNERABILITY: "vulnerability.html",
    ReportType.COMPLIANCE:    "compliance.html",
}


class PDFRenderer:
    """Renders ReportData to PDF bytes via Jinja2 + WeasyPrint."""

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
        charts:      dict[str, str],   # name → SVG string
    ) -> bytes:
        """
        Render ReportData to PDF bytes asynchronously.
        Jinja2 rendering is sync; WeasyPrint is sync.
        Both run in a thread-pool executor.
        """
        loop = asyncio.get_event_loop()

        # Step 1: render HTML (fast, but Jinja2 is sync)
        html_str = await loop.run_in_executor(
            None, self._render_html, report_data, charts
        )

        # Step 2: convert HTML → PDF (slow, CPU-bound)
        pdf_bytes = await loop.run_in_executor(
            None, self._html_to_pdf, html_str
        )

        logger.info(
            "pdf_rendered",
            report_type=report_data.report_type.value,
            size_kb=round(len(pdf_bytes) / 1024, 1),
        )
        return pdf_bytes

    def _render_html(self, report_data: ReportData, charts: dict[str, str]) -> str:
        template_name = _TEMPLATE_MAP.get(report_data.report_type, "executive.html")
        template      = self._jinja_env.get_template(template_name)
        return template.render(report_data=report_data, charts=charts)

    @staticmethod
    def _html_to_pdf(html_str: str) -> bytes:
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration

        font_config = FontConfiguration()
        html_doc    = HTML(string=html_str, base_url=str(_TEMPLATE_DIR))

        buf = io.BytesIO()
        html_doc.write_pdf(
            buf,
            font_config=font_config,
            optimize_images=True,
            uncompressed_pdf=False,
        )
        buf.seek(0)
        return buf.read()

    def render_html_preview(
        self,
        report_data: ReportData,
        charts:      dict[str, str],
    ) -> str:
        """Return the raw HTML string (for browser preview without PDF conversion)."""
        return self._render_html(report_data, charts)
