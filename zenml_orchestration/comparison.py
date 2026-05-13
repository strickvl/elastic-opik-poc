"""Helpers for comparing completed Opik evaluation result artifacts."""

import json
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from zenml.client import Client

from zenml_orchestration.artifacts import (
    OpikEvaluationComparison,
    OpikEvaluationResults,
)
from zenml_orchestration.visualizations import render_opik_comparison_report

_RESULTS_ARTIFACT_NAME = "opik_evaluation_results"
_EVALUATION_STEP_NAME = "run_trace_linked_evaluation_step"


def build_comparison_from_sources(
    *,
    run_names_or_ids: Optional[Sequence[str]] = None,
    result_json_paths: Optional[Sequence[str]] = None,
    labels: Optional[Sequence[str]] = None,
    output_html_path: Optional[str] = None,
) -> OpikEvaluationComparison:
    """Load evaluation results and build a static comparison artifact."""
    results, inferred_labels = _load_results(
        run_names_or_ids=run_names_or_ids or [],
        result_json_paths=result_json_paths or [],
    )
    label_list = list(labels or inferred_labels)
    comparison = OpikEvaluationComparison.from_results(results, labels=label_list)

    if output_html_path:
        output_path = Path(output_html_path).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(str(render_opik_comparison_report(comparison)), encoding="utf-8")

    return comparison


def _load_results(
    *,
    run_names_or_ids: Sequence[str],
    result_json_paths: Sequence[str],
) -> Tuple[List[OpikEvaluationResults], List[str]]:
    results: List[OpikEvaluationResults] = []
    labels: List[str] = []

    for run_name_or_id in run_names_or_ids:
        result = load_results_from_zenml_run(run_name_or_id)
        results.append(result)
        labels.append(run_name_or_id)

    for path in result_json_paths:
        result = load_results_from_json(path)
        results.append(result)
        labels.append(Path(path).stem)

    if not results:
        raise ValueError(
            "Provide at least one ZenML run name/id or one evaluation results JSON path."
        )
    return results, labels


def _first_artifact_version(artifact_output: object) -> object | None:
    """Return the first artifact version from ZenML's list-or-singleton output shape."""
    if artifact_output is None:
        return None
    if isinstance(artifact_output, list):
        return artifact_output[0] if artifact_output else None
    return artifact_output


def load_results_from_json(path: str) -> OpikEvaluationResults:
    """Load an OpikEvaluationResults artifact from a downloaded JSON file."""
    with Path(path).expanduser().open("r", encoding="utf-8") as f:
        return OpikEvaluationResults.from_mapping(json.load(f))


def load_results_from_zenml_run(run_name_or_id: str) -> OpikEvaluationResults:
    """Load the `opik_evaluation_results` artifact from a completed ZenML run."""
    client = Client()
    run = client.get_pipeline_run(run_name_or_id, hydrate=True)
    step = run.steps.get(_EVALUATION_STEP_NAME) if run.steps else None
    if step is None:
        raise ValueError(
            f"Run {run_name_or_id!r} does not contain step {_EVALUATION_STEP_NAME!r}."
        )

    artifact_output = (step.outputs or {}).get(_RESULTS_ARTIFACT_NAME)
    artifact_version = _first_artifact_version(artifact_output)
    if artifact_version is None:
        raise ValueError(
            f"Run {run_name_or_id!r} does not contain artifact {_RESULTS_ARTIFACT_NAME!r}. "
            "Re-run the evaluation pipeline after this change, or pass a downloaded JSON file."
        )

    loaded = artifact_version.load()
    if isinstance(loaded, OpikEvaluationResults):
        payload = loaded.to_dict()
    elif isinstance(loaded, dict):
        payload = loaded
    elif hasattr(loaded, "to_dict"):
        payload = loaded.to_dict()
    else:
        raise TypeError(
            f"Unsupported evaluation results artifact type from run {run_name_or_id!r}: {type(loaded)!r}"
        )

    payload["zenml_run_name"] = run.name
    return OpikEvaluationResults.from_mapping(payload)


__all__ = [
    "build_comparison_from_sources",
    "load_results_from_json",
    "load_results_from_zenml_run",
]
