"""Two-step ZenML pipeline for the Elastic Opik PoC."""

from __future__ import annotations

import os
from typing import Annotated, Any, Dict, Tuple

from dotenv import load_dotenv
from zenml import log_metadata, pipeline, step
from zenml.config import DockerSettings
from zenml.types import HTMLString

from zenml_orchestration.dataset_registration import register_opik_dataset
from zenml_orchestration.evaluation import (
    DEFAULT_EXPERIMENT_NAME,
    DEFAULT_JUDGE_MODEL,
    run_trace_linked_evaluation,
)

load_dotenv()

_ENVIRONMENT_KEYS = [
    "OPIK_API_KEY",
    "OPIK_WORKSPACE",
    "OPIK_PROJECT_NAME",
    "DATASET_NAME",
    "OPENROUTER_API_KEY",
    "OPENROUTER_API_BASE",
    "GCS_BUCKET",
    "GCS_OBJECT",
    "RETRIEVAL_K",
    "KIBANA_URL",
    "KIBANA_API_KEY",
    "KIBANA_API_KEY_ID",
    "KIBANA_USERNAME",
    "KIBANA_PASSWORD",
    "KIBANA_AGENT_ID",
    "KIBANA_SPACE",
    "KIBANA_CONNECTOR_ID",
]

_DOCKER_ENVIRONMENT = {
    key: value
    for key in _ENVIRONMENT_KEYS
    if (value := os.getenv(key))
}


@step(enable_cache=False)
def register_dataset_step(
    source: str = "mock",
    update_existing: bool = False,
) -> Annotated[Dict[str, Any], "opik_dataset_registration"]:
    """Register/update the Opik dataset before evaluation."""
    summary = register_opik_dataset(
        source=source,  # type: ignore[arg-type]
        update_existing=update_existing,
    )
    log_metadata(
        metadata={
            "opik_dataset_registration": summary,
        }
    )
    return summary


@step(enable_cache=False)
def run_trace_linked_evaluation_step(
    dataset_info: Dict[str, Any],
    agent_mode: str = "mock",
    experiment_name: str = DEFAULT_EXPERIMENT_NAME,
    task_threads: int = 1,
    judge_model: str = DEFAULT_JUDGE_MODEL,
) -> Tuple[
    Annotated[Dict[str, Any], "opik_evaluation_summary"],
    Annotated[HTMLString, "opik_experiment_link"],
]:
    """Run the Opik trace-linked evaluation after dataset registration."""
    summary = run_trace_linked_evaluation(
        dataset_name=dataset_info["dataset_name"],
        project_name=dataset_info["project_name"],
        experiment_name=experiment_name,
        agent_mode=agent_mode,  # type: ignore[arg-type]
        task_threads=task_threads,
        judge_model=judge_model,
    )
    log_metadata(
        metadata={
            "opik_evaluation": summary,
        }
    )

    experiment_url = summary.get("experiment_url") or ""
    if experiment_url:
        html = HTMLString(
            f'<p><a href="{experiment_url}" target="_blank">Open Opik experiment</a></p>'
        )
    else:
        html = HTMLString("<p>Opik did not return an experiment URL.</p>")

    return summary, html


@pipeline(
    enable_cache=False,
    settings={
        "docker": DockerSettings(
            requirements="requirements.txt",
            environment=_DOCKER_ENVIRONMENT,
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
