"""Small ZenML dashboard visualizations for the Elastic Opik PoC."""

from html import escape
from pathlib import Path
from string import Template
from typing import Any, Dict, Iterable, Mapping

from zenml.types import HTMLString

_REPORT_TEMPLATE_PATH = Path(__file__).with_name("opik_evaluation_report.html")
_RESULTS_TEMPLATE_PATH = Path(__file__).with_name("opik_evaluation_results.html")
_COMPARISON_TEMPLATE_PATH = Path(__file__).with_name("opik_comparison_report.html")
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


def render_opik_evaluation_results(results: Any) -> HTMLString:
    """Render aggregate and per-item scores for one Opik evaluation run."""
    results_dict = _as_dict(results)
    template = Template(_RESULTS_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return HTMLString(
        template.safe_substitute(
            experiment_link=_opik_link_html(_text(results_dict.get("experiment_url"))),
            score_cards=_score_cards(results_dict.get("aggregate_scores") or {}),
            item_rows=_item_rows(results_dict.get("item_results") or []),
        )
    )


def render_opik_comparison_report(comparison: Any) -> HTMLString:
    """Render a static comparison report across evaluation result artifacts."""
    comparison_dict = _as_dict(comparison)
    experiments = comparison_dict.get("experiments") or []
    metric_names = comparison_dict.get("metric_names") or []
    template = Template(_COMPARISON_TEMPLATE_PATH.read_text(encoding="utf-8"))
    return HTMLString(
        template.safe_substitute(
            baseline_label=escape(_text(comparison_dict.get("baseline_label"), "first run")),
            generated_at=escape(_text(comparison_dict.get("generated_at"), "unknown")),
            header_row=_comparison_header(experiments),
            metric_rows=_comparison_metric_rows(metric_names, experiments),
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


def _score_cards(aggregate_scores: Mapping[str, Any]) -> str:
    if not aggregate_scores:
        return '<span class="muted">No aggregate scores were captured.</span>'
    cards = []
    for metric_name, score in aggregate_scores.items():
        score_dict = dict(score or {})
        failed_count = int(score_dict.get("failed_count") or 0)
        failed_html = f'<div class="failed">{failed_count} failed</div>' if failed_count else ""
        cards.append(
            '<div class="score-card">'
            f'<span class="metric-name">{escape(str(metric_name))}</span>'
            f'<span class="metric-value">{_format_optional_float(score_dict.get("mean"))}</span>'
            f'{failed_html}'
            '</div>'
        )
    return "\n".join(cards)


def _item_rows(item_results: Iterable[Any]) -> str:
    rows = []
    for item in item_results:
        item_dict = dict(item or {})
        scores = dict(item_dict.get("scores") or {})
        score_text = ", ".join(
            f"{name}: {_format_optional_float((score or {}).get('value'))}"
            for name, score in scores.items()
        )
        rows.append(
            "<tr>"
            f"<td>{escape(_text(item_dict.get('dataset_item_id'), 'unknown'))}</td>"
            f"<td>{escape(_truncate(_text(item_dict.get('input')), 120))}</td>"
            f"<td>{escape(score_text or 'No scores')}</td>"
            f"<td>{escape(_truncate(_text(item_dict.get('otel_traceparent')), 72))}</td>"
            "</tr>"
        )
    return "\n".join(rows) or '<tr><td colspan="4" class="muted">No per-item rows captured.</td></tr>'


def _comparison_header(experiments: Iterable[Any]) -> str:
    headers = ['<th>Metric</th>']
    for index, experiment in enumerate(experiments):
        exp = dict(experiment or {})
        label = escape(_text(exp.get("label"), f"Experiment {index + 1}"))
        url = _text(exp.get("experiment_url"))
        label_html = f'<a class="experiment-link" href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{label}</a>' if url else label
        class_name = ' class="baseline"' if index == 0 else ""
        zenml_run = _text(exp.get("zenml_run_name"))
        run_html = f'<div class="small">ZenML: {escape(zenml_run)}</div>' if zenml_run else ""
        headers.append(f'<th{class_name}>{label_html}<div class="small">{escape(_text(exp.get("experiment_name")))}</div>{run_html}</th>')
    return "<tr>" + "".join(headers) + "</tr>"


def _comparison_metric_rows(metric_names: Iterable[Any], experiments: Iterable[Any]) -> str:
    experiments_list = [dict(experiment or {}) for experiment in experiments]
    rows = []
    for metric_name in metric_names:
        metric_key = str(metric_name)
        cells = [f'<td class="metric">{escape(metric_key)}</td>']
        for experiment in experiments_list:
            metric = dict((experiment.get("metrics") or {}).get(metric_key) or {})
            cells.append(
                "<td>"
                f'<div class="value">{_format_optional_float(metric.get("value"))}</div>'
                f'{_delta_html(metric.get("delta_from_baseline"))}'
                f'{_failed_html(metric.get("failed_count"))}'
                "</td>"
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return "\n".join(rows) or '<tr><td class="muted">No metrics available.</td></tr>'


def _delta_html(delta: Any) -> str:
    delta_value = _coerce_float(delta)
    if delta_value is None:
        return '<div class="small">baseline / n/a</div>'
    if delta_value > 0:
        return f'<div class="delta-pos">+{delta_value:.4f}</div>'
    if delta_value < 0:
        return f'<div class="delta-neg">{delta_value:.4f}</div>'
    return '<div class="delta-zero">±0.0000</div>'


def _failed_html(failed_count: Any) -> str:
    failed = int(failed_count or 0)
    return f'<div class="failed">{failed} failed</div>' if failed else ""


def _format_optional_float(value: Any) -> str:
    float_value = _coerce_float(value)
    if float_value is None:
        return "—"
    return f"{float_value:.4f}"


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


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


__all__ = [
    "render_opik_comparison_report",
    "render_opik_evaluation_report",
    "render_opik_evaluation_results",
    "render_opik_experiment_link",
]
