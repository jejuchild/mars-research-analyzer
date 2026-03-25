"""HTML report generator."""

import json
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from config import REPORT_DIR

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _tojson_safe(x):
    """JSON dump that is safe inside <script> tags (not HTML-escaped)."""
    return Markup(json.dumps(x, indent=2, ensure_ascii=False, default=str))


def generate_report(analysis_results: dict, output_name: str = None) -> Path:
    """Generate HTML report from analysis results."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=True,
    )
    env.filters["tojson_pretty"] = _tojson_safe

    template = env.get_template("report.html")

    if not output_name:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"mars_research_report_{timestamp}"

    html = template.render(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        **analysis_results,
    )

    output_path = REPORT_DIR / f"{output_name}.html"
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"Report generated: {output_path}")
    return output_path
