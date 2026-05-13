"""Small ZenML dashboard visualizations for the Elastic Opik PoC."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any, Dict

from zenml.types import HTMLString

_TEMPLATE_PATH = Path(__file__).with_name("opik_experiment_link.html")


def render_opik_experiment_link(summary: Dict[str, Any]) -> HTMLString:
    """Render a compact dashboard link to the Opik experiment."""
    experiment_url = str(summary.get("experiment_url") or "")
    if experiment_url:
        link_html = (
            f'<p><a href="{escape(experiment_url, quote=True)}" target="_blank" '
            'rel="noopener noreferrer">Open Opik experiment</a></p>'
        )
    else:
        link_html = "<p>Opik did not return an experiment URL.</p>"

    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    return HTMLString(
        template.format(
            experiment_name=escape(str(summary.get("experiment_name") or "unknown")),
            project_name=escape(str(summary.get("project_name") or "unknown")),
            dataset_name=escape(str(summary.get("dataset_name") or "unknown")),
            link_html=link_html,
        )
    )


__all__ = ["render_opik_experiment_link"]
