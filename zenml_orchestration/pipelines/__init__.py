"""ZenML pipeline definitions for the Elastic Opik PoC."""

from zenml_orchestration.pipelines.elastic_opik import elastic_opik_zenml_pipeline
from zenml_orchestration.pipelines.opik_comparison import (
    opik_evaluation_comparison_pipeline,
)

__all__ = ["elastic_opik_zenml_pipeline", "opik_evaluation_comparison_pipeline"]
