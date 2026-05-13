"""ZenML pipeline for static comparison of completed Opik evaluation runs."""

from typing import List, Optional

from zenml import pipeline

from zenml_orchestration.artifacts import OpikEvaluationComparison
from zenml_orchestration.steps.comparison import compare_opik_evaluation_runs_step


@pipeline(
    enable_cache=False,
    tags=["elastic", "opik", "zenml", "comparison"],
)
def opik_evaluation_comparison_pipeline(
    run_names_or_ids: Optional[List[str]] = None,
    result_json_paths: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    output_html_path: Optional[str] = None,
) -> OpikEvaluationComparison:
    """Generate a static comparison report from prior evaluation artifacts."""
    return compare_opik_evaluation_runs_step(
        run_names_or_ids=run_names_or_ids,
        result_json_paths=result_json_paths,
        labels=labels,
        output_html_path=output_html_path,
    )
