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

    def trace_linked_task(dataset_item: Dict[str, Any]) -> Dict[str, Any]:
        headers: Dict[str, str] = {}
        inject(headers)

        agent = _load_agent(agent_mode)
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
    """Run the trace-linked Opik evaluation loop and return a small summary."""
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

    experiment_url = getattr(results, "experiment_url", "")
    return {
        "dataset_name": resolved_dataset_name,
        "project_name": resolved_project_name,
        "experiment_name": experiment_name,
        "experiment_url": experiment_url,
        "agent_mode": agent_mode,
        "task_threads": task_threads,
        "judge_model": judge_model,
        "retrieval_k": resolved_retrieval_k,
        "metrics": [metric.name for metric in metrics],
    }


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
