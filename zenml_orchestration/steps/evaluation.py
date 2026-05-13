"""ZenML step for running the trace-linked Opik evaluation."""

from typing import Annotated, Any, Dict, Tuple

from zenml import ArtifactConfig, log_metadata, step
from zenml.types import HTMLString

from zenml_orchestration.artifacts import OpikEvaluationSummary
from zenml_orchestration.evaluation import (
    DEFAULT_EXPERIMENT_NAME,
    DEFAULT_JUDGE_MODEL,
    run_trace_linked_evaluation,
)
from zenml_orchestration.materializers import OpikEvaluationSummaryMaterializer
from zenml_orchestration.visualizations import render_opik_experiment_link

_EVALUATION_ARTIFACT_TAGS = ["elastic", "opik", "evaluation", "trace-linked"]
_EXPERIMENT_LINK_ARTIFACT_TAGS = ["elastic", "opik", "html", "trace-linked"]


@step(
    enable_cache=False,
    output_materializers={
        "opik_evaluation_summary": OpikEvaluationSummaryMaterializer,
    },
)
def run_trace_linked_evaluation_step(
    dataset_info: Dict[str, Any],
    agent_mode: str = "mock",
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    task_threads: int = 1,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> Tuple[
    Annotated[
        OpikEvaluationSummary,
        ArtifactConfig(
            name="opik_evaluation_summary",
            tags=_EVALUATION_ARTIFACT_TAGS,
        ),
    ],
    Annotated[
        HTMLString,
        ArtifactConfig(
            name="opik_experiment_link",
            tags=_EXPERIMENT_LINK_ARTIFACT_TAGS,
        ),
    ],
]:
    """Run the Opik trace-linked evaluation after dataset registration."""
    summary = OpikEvaluationSummary.from_mapping(
        run_trace_linked_evaluation(
            dataset_name=dataset_info["dataset_name"],
            project_name=dataset_info["project_name"],
            experiment_name=experiment_name,
            agent_mode=agent_mode,  # type: ignore[arg-type]
            task_threads=task_threads,
            judge_model=judge_model,
        )
    )

    summary_dict = summary.to_dict()
    metrics = summary_dict.get("metrics") or []
    log_metadata(
        metadata={
            "dataset_name": summary_dict.get("dataset_name"),
            "project_name": summary_dict.get("project_name"),
            "experiment_name": summary_dict.get("experiment_name"),
            "experiment_url": summary_dict.get("experiment_url"),
            "agent_mode": summary_dict.get("agent_mode"),
            "task_threads": summary_dict.get("task_threads"),
            "judge_model": summary_dict.get("judge_model"),
            "retrieval_k": summary_dict.get("retrieval_k"),
            "metrics": metrics,
            "metric_count": len(metrics),
        }
    )

    return summary, render_opik_experiment_link(summary)
