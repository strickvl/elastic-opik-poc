"""Backward-compatible import path for the Elastic Opik ZenML pipeline.

New code can import from ``zenml_orchestration.pipelines.elastic_opik``. This
module remains so earlier README snippets and customer copy-paste imports keep
working.
"""

from zenml_orchestration.pipelines.elastic_opik import elastic_opik_zenml_pipeline

__all__ = ["elastic_opik_zenml_pipeline"]
