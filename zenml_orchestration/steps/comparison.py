"""ZenML step for building static Opik experiment comparison reports."""

from typing import Annotated, List, Optional

from zenml import ArtifactConfig, step

from zenml_orchestration.artifacts import OpikEvaluationComparison
from zenml_orchestration.comparison import build_comparison_from_sources
from zenml_orchestration.materializers import OpikEvaluationComparisonMaterializer

_COMPARISON_ARTIFACT_TAGS = ["elastic", "opik", "comparison", "html"]


@step(
    enable_cache=False,
    output_materializers={
        "opik_evaluation_comparison": OpikEvaluationComparisonMaterializer,
    },
)
def compare_opik_evaluation_runs_step(
    run_names_or_ids: Optional[List[str]] = None,
    result_json_paths: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    output_html_path: Optional[str] = None,
) -> Annotated[
    OpikEvaluationComparison,
    ArtifactConfig(
        name="opik_evaluation_comparison",
        tags=_COMPARISON_ARTIFACT_TAGS,
    ),
]:
    """Compare completed evaluation result artifacts and return an HTML report."""
    return build_comparison_from_sources(
        run_names_or_ids=run_names_or_ids,
        result_json_paths=result_json_paths,
        labels=labels,
        output_html_path=output_html_path,
    )
