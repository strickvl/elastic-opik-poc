"""Small ZenML dashboard visualizations for the Elastic Opik PoC."""

from html import escape
from pathlib import Path
from string import Template
from typing import Any, Dict, Iterable, Mapping

from zenml.types import HTMLString

_REPORT_TEMPLATE_PATH = Path(__file__).with_name("opik_evaluation_report.html")
_EXPERIMENT_LINK_TEMPLATE_PATH = Path(__file__).with_name("opik_experiment_link.html")


def render_opik_evaluation_report(summary: Any) -> HTMLString:
    """Render a compact dashboard report for the Opik evaluation summary."""
    summary_dict = _as_dict(summary)
    experiment_url = _text(summary_dict.get("experiment_url"))
    metrics = summary_dict.get("metrics") or []

    template = Template(_REPORT_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return HTMLString(
        template.safe_substitute(
            experiment_name=escape(_text(summary_dict.get("experiment_name"), "unknown")),
            project_name=escape(_text(summary_dict.get("project_name"), "unknown")),
            dataset_name=escape(_text(summary_dict.get("dataset_name"), "unknown")),
            agent_mode=escape(_text(summary_dict.get("agent_mode"), "unknown")),
            metrics_mode=escape(_metrics_mode(metrics)),
            judge_model=escape(_text(summary_dict.get("judge_model"), "unknown")),
            task_threads=escape(_text(summary_dict.get("task_threads"), "unknown")),
            retrieval_k=escape(_text(summary_dict.get("retrieval_k"), "unknown")),
            metric_count=escape(str(len(metrics))),
            metrics_html=_metric_pills(metrics),
            link_html=_opik_link_html(experiment_url, button=True),
            trace_note=escape(_trace_note(_text(summary_dict.get("agent_mode")))),
        )
    )


def render_opik_experiment_link(summary: Any) -> HTMLString:
    """Render a small one-click link artifact for the Opik experiment."""
    summary_dict = _as_dict(summary)
    template = _EXPERIMENT_LINK_TEMPLATE_PATH.read_text(encoding="utf-8")
    return HTMLString(
        template.format(
            experiment_name=escape(_text(summary_dict.get("experiment_name"), "unknown")),
            project_name=escape(_text(summary_dict.get("project_name"), "unknown")),
            dataset_name=escape(_text(summary_dict.get("dataset_name"), "unknown")),
            link_html=_opik_link_html(_text(summary_dict.get("experiment_url"))),
        )
    )


def _as_dict(summary: Any) -> Dict[str, Any]:
    if hasattr(summary, "to_dict"):
        return dict(summary.to_dict())
    if hasattr(summary, "model_dump"):
        return dict(summary.model_dump(mode="json"))
    if isinstance(summary, Mapping):
        return dict(summary)
    raise TypeError(f"Unsupported Opik summary type: {type(summary)!r}")


def _opik_link_html(experiment_url: str, *, button: bool = False) -> str:
    if not experiment_url:
        return '<span class="muted">Opik did not return an experiment URL.</span>'

    style = (
        "background:#0077cc;border-radius:10px;color:white;display:inline-block;"
        "font-weight:750;padding:10px 14px;text-decoration:none;"
    )
    class_name = "elastic-button" if button else ""
    style_attr = "" if button else f' style="{style}"'
    return (
        f'<a class="{class_name}" href="{escape(experiment_url, quote=True)}"'
        f'{style_attr} target="_blank" rel="noopener noreferrer">'
        "Open Opik experiment</a>"
    )


def _metric_pills(metrics: Iterable[Any]) -> str:
    items = [escape(str(metric)) for metric in metrics]
    if not items:
        return '<span class="muted">No metric names returned.</span>'
    return "\n".join(f'<span class="metric-pill">{item}</span>' for item in items)


def _metrics_mode(metrics: Iterable[Any]) -> str:
    metric_names = {str(metric) for metric in metrics}
    llm_judges = {"factuality", "groundedness", "relevance", "sequence_fidelity"}
    retrieval_prefixes = ("precision_at_", "recall_at_", "f1_at_")
    has_llm = bool(metric_names & llm_judges)
    has_retrieval = any(
        metric_name.startswith(retrieval_prefixes) for metric_name in metric_names
    )
    if has_llm and has_retrieval:
        return "LLM judges + retrieval metrics"
    if has_llm:
        return "LLM judge metrics"
    if has_retrieval:
        return "Retrieval metrics"
    return "Custom metrics"


def _trace_note(agent_mode: str) -> str:
    if agent_mode == "real":
        return "Real mode: Opik Trace links should open the Kibana span tree when trace propagation is configured end-to-end."
    return "Mock mode: traceparent injection is recorded, but real Opik Trace links require the remote Kibana agent path."


def _text(value: Any, default: str = "") -> str:
    if value is None or value == "":
        return default
    return str(value)


__all__ = ["render_opik_evaluation_report", "render_opik_experiment_link"]
