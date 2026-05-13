"""Import-safe helpers for trace-linked Opik evaluation.

Importing this module does not import ``kibana_agent.py``. That matters because
``kibana_agent.py`` configures OpenTelemetry exporters and reads required env vars
when it is imported.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional

from dotenv import load_dotenv

AgentMode = Literal["mock", "real"]
DEFAULT_EXPERIMENT_NAME = "elastic-agent-trace-linked-zenml"
DEFAULT_JUDGE_MODEL = "openrouter/anthropic/claude-sonnet-4.5"

_REPO_ROOT = Path(__file__).resolve().parent.parent
_METRICS_DIR = _REPO_ROOT / "03_metrics"


def build_step05_metrics(
    *,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    retrieval_k: int = 3,
) -> List[Any]:
    """Build the metric list used by the Step 05 evaluation."""
    _ensure_metrics_path()

    from opik.evaluation.metrics import AnswerRelevance, ContextPrecision, Hallucination
    from metrics import F1AtK, PrecisionAtK, RecallAtK, SequenceFidelity

    return [
        Hallucination(model=judge_model, name="factuality"),
        ContextPrecision(model=judge_model, name="groundedness"),
        AnswerRelevance(model=judge_model, name="relevance"),
        SequenceFidelity(model=judge_model),
        PrecisionAtK(k=retrieval_k),
        RecallAtK(k=retrieval_k),
        F1AtK(k=retrieval_k),
    ]


def make_trace_linked_task(
    *,
    agent_mode: AgentMode = "mock",
    judge_model: str = DEFAULT_JUDGE_MODEL,
    retrieval_k: int = 3,
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """Create an Opik task that injects W3C trace context into the agent call.

    ``judge_model`` and ``retrieval_k`` are accepted here so the task factory can
    mirror the evaluation configuration, even though only metrics use them today.
    """
    del judge_model, retrieval_k

    from opentelemetry.propagate import inject

    agent = _load_agent(agent_mode)

    def trace_linked_task(dataset_item: Dict[str, Any]) -> Dict[str, Any]:
        headers: Dict[str, str] = {}
        inject(headers)

        response = agent(dataset_item["input"], headers=headers)
        context = getattr(response, "context", None) or [
            str(doc_id) for doc_id in response.retrieved_documents
        ]

        return {
            "output": response.text,
            "context": context,
            "retrieved_ids": response.retrieved_documents,
            "relevant_ids": dataset_item.get("relevant_doc_ids", []),
            "otel_traceparent": headers.get("traceparent", ""),
        }

    return trace_linked_task


def run_trace_linked_evaluation(
    *,
    dataset_name: Optional[str] = None,
    project_name: Optional[str] = None,
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    agent_mode: AgentMode = "mock",
    task_threads: int = 1,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    retrieval_k: Optional[int] = None,
) -> Dict[str, Any]:
    """Run the trace-linked Opik evaluation loop and return ZenML-ready payloads."""
    load_dotenv()

    import opik

    resolved_dataset_name = dataset_name or os.environ["DATASET_NAME"]
    resolved_project_name = project_name or os.environ["OPIK_PROJECT_NAME"]
    resolved_retrieval_k = retrieval_k or int(os.environ.get("RETRIEVAL_K", "3"))

    client = opik.Opik()
    dataset = client.get_dataset(name=resolved_dataset_name)
    metrics = build_step05_metrics(
        judge_model=judge_model,
        retrieval_k=resolved_retrieval_k,
    )
    task = make_trace_linked_task(
        agent_mode=agent_mode,
        judge_model=judge_model,
        retrieval_k=resolved_retrieval_k,
    )

    results = opik.evaluate(
        dataset=dataset,
        task=task,
        scoring_metrics=metrics,
        experiment_name=experiment_name,
        experiment_config={
            **get_git_metadata(),
            "agent_mode": agent_mode,
            "judge_model": judge_model,
            "ranking_size": resolved_retrieval_k,
            "dataset": resolved_dataset_name,
        },
        project_name=resolved_project_name,
        task_threads=task_threads,
    )

    result_payload = _evaluation_results_payload(
        results=results,
        dataset_name=resolved_dataset_name,
        project_name=resolved_project_name,
        experiment_name=experiment_name,
        agent_mode=agent_mode,
        task_threads=task_threads,
        judge_model=judge_model,
        retrieval_k=resolved_retrieval_k,
        metric_names=[metric.name for metric in metrics],
    )
    return {
        "summary": _evaluation_summary_payload(result_payload),
        "results": result_payload,
    }


def _evaluation_results_payload(
    *,
    results: Any,
    dataset_name: str,
    project_name: str,
    experiment_name: str,
    agent_mode: AgentMode,
    task_threads: int,
    judge_model: str,
    retrieval_k: int,
    metric_names: List[str],
) -> Dict[str, Any]:
    """Convert Opik's EvaluationResult object into JSON-friendly data."""
    aggregate_scores = _aggregate_score_payload(results)
    item_results = [_test_result_payload(result) for result in results.test_results]
    failed_counts = _failed_counts(results.test_results)

    for metric_name in metric_names:
        aggregate_scores.setdefault(
            metric_name,
            {
                "mean": None,
                "min": None,
                "max": None,
                "std": None,
                "values": [],
                "failed_count": failed_counts.get(metric_name, 0),
            },
        )
        aggregate_scores[metric_name]["failed_count"] = failed_counts.get(metric_name, 0)

    return {
        "dataset_name": dataset_name,
        "project_name": project_name,
        "experiment_id": _optional_text(getattr(results, "experiment_id", None)),
        "dataset_id": _optional_text(getattr(results, "dataset_id", None)),
        "experiment_name": _optional_text(getattr(results, "experiment_name", None)) or experiment_name,
        "experiment_url": _optional_text(getattr(results, "experiment_url", None)),
        "agent_mode": agent_mode,
        "task_threads": task_threads,
        "judge_model": judge_model,
        "retrieval_k": retrieval_k,
        "metrics": metric_names,
        "aggregate_scores": aggregate_scores,
        "item_results": item_results,
    }


def _evaluation_summary_payload(result_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build the small run summary from the richer result payload."""
    aggregate_scores = result_payload.get("aggregate_scores") or {}
    return {
        "dataset_name": result_payload.get("dataset_name"),
        "project_name": result_payload.get("project_name"),
        "experiment_id": result_payload.get("experiment_id"),
        "dataset_id": result_payload.get("dataset_id"),
        "experiment_name": result_payload.get("experiment_name"),
        "experiment_url": result_payload.get("experiment_url"),
        "agent_mode": result_payload.get("agent_mode"),
        "task_threads": result_payload.get("task_threads"),
        "judge_model": result_payload.get("judge_model"),
        "retrieval_k": result_payload.get("retrieval_k"),
        "metrics": result_payload.get("metrics") or [],
        "score_means": {
            name: score.get("mean") for name, score in aggregate_scores.items()
        },
        "failed_counts": {
            name: int(score.get("failed_count") or 0)
            for name, score in aggregate_scores.items()
        },
    }


def _aggregate_score_payload(results: Any) -> Dict[str, Dict[str, Any]]:
    """Extract aggregate metric statistics from Opik's result object."""
    view = results.aggregate_evaluation_scores()
    return {
        metric_name: {
            "mean": _safe_float(statistics.mean),
            "min": _safe_float(statistics.min),
            "max": _safe_float(statistics.max),
            "std": _safe_float(statistics.std),
            "values": [_safe_float(value) for value in statistics.values if _safe_float(value) is not None],
            "failed_count": 0,
        }
        for metric_name, statistics in view.aggregated_scores.items()
    }


def _test_result_payload(result: Any) -> Dict[str, Any]:
    """Extract one per-item Opik test result into JSON-friendly data."""
    test_case = result.test_case
    task_output = test_case.task_output or {}
    dataset_item_content = test_case.dataset_item_content or {}
    return {
        "dataset_item_id": str(test_case.dataset_item_id),
        "trace_id": _optional_text(test_case.trace_id),
        "trial_id": int(result.trial_id),
        "input": dataset_item_content.get("input"),
        "output": task_output.get("output"),
        "otel_traceparent": task_output.get("otel_traceparent"),
        "task_execution_time": _safe_float(result.task_execution_time),
        "scoring_time": _safe_float(result.scoring_time),
        "scores": {
            score.name: {
                "value": _safe_float(score.value),
                "scoring_failed": bool(score.scoring_failed),
                "reason": _optional_text(score.reason),
                "category_name": _optional_text(score.category_name),
                "metadata": score.metadata or {},
            }
            for score in result.score_results
        },
    }


def _failed_counts(test_results: List[Any]) -> Dict[str, int]:
    """Count failed score computations by metric name."""
    counts: Dict[str, int] = {}
    for result in test_results:
        for score in result.score_results:
            if score.scoring_failed:
                counts[score.name] = counts.get(score.name, 0) + 1
    return counts


def _safe_float(value: Any) -> Optional[float]:
    """Return a float unless the value is missing or non-finite."""
    if value is None:
        return None
    try:
        float_value = float(value)
    except (TypeError, ValueError):
        return None
    if float_value != float_value or float_value in (float("inf"), float("-inf")):
        return None
    return float_value


def _optional_text(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(value)


def get_git_metadata() -> Dict[str, str]:
    """Return best-effort git metadata for experiment config."""

    def _run(cmd: List[str]) -> str:
        try:
            return subprocess.check_output(
                cmd,
                cwd=_REPO_ROOT,
                stderr=subprocess.DEVNULL,
            ).decode().strip()
        except Exception:
            return "unknown"

    return {
        "git_sha": _run(["git", "rev-parse", "--short=8", "HEAD"]),
        "git_branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
    }


def _load_agent(agent_mode: AgentMode) -> Callable[..., Any]:
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    from kibana_agent import call_kibana_agent, call_real_kibana_agent

    if agent_mode == "mock":
        return call_kibana_agent
    if agent_mode == "real":
        return call_real_kibana_agent
    raise ValueError(f"Unsupported agent mode: {agent_mode!r}")


def _ensure_metrics_path() -> None:
    if str(_METRICS_DIR) not in sys.path:
        sys.path.insert(0, str(_METRICS_DIR))
