"""Two-step ZenML pipeline for the Elastic Opik PoC."""

from typing import Any, Dict, Tuple

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.types import HTMLString

from zenml_orchestration.evaluation import DEFAULT_EXPERIMENT_NAME, DEFAULT_JUDGE_MODEL
from zenml_orchestration.steps import (
    register_dataset_step,
    run_trace_linked_evaluation_step,
)

_RUNTIME_ENVIRONMENT = {
    "OPIK_API_KEY": "${OPIK_API_KEY}",
    "OPIK_WORKSPACE": "${OPIK_WORKSPACE}",
    "OPIK_PROJECT_NAME": "${OPIK_PROJECT_NAME}",
    "DATASET_NAME": "${DATASET_NAME}",
    "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}",
}


@pipeline(
    enable_cache=False,
    tags=["elastic", "opik", "zenml", "trace-linked"],
    settings={
        "docker": DockerSettings(
            requirements="requirements.txt",
            runtime_environment=_RUNTIME_ENVIRONMENT,
        )
    },
)
def elastic_opik_zenml_pipeline(
    dataset_source: str = "mock",
    agent_mode: str = "mock",
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    task_threads: int = 1,
    judge_model: str = DEFAULT_JUDGE_MODEL,
    update_existing: bool = False,
) -> Tuple[Dict[str, Any], HTMLString]:
    """Register the Opik dataset, then run the trace-linked Opik evaluation."""
    dataset_info = register_dataset_step(
        source=dataset_source,
        update_existing=update_existing,
    )
    evaluation_summary, experiment_link = run_trace_linked_evaluation_step(
        dataset_info=dataset_info,
        agent_mode=agent_mode,
        experiment_name=experiment_name,
        task_threads=task_threads,
        judge_model=judge_model,
    )
    return evaluation_summary, experiment_link
