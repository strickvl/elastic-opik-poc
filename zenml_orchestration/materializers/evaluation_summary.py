"""Materializer for the typed Opik evaluation summary artifact."""

import hashlib
import json
import os
from typing import Any, Dict, Type

from zenml.enums import ArtifactType, VisualizationType
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer

from zenml_orchestration.artifacts import OpikEvaluationSummary
from zenml_orchestration.visualizations import render_opik_evaluation_report


class OpikEvaluationSummaryMaterializer(BaseMaterializer):
    """Persist Opik evaluation summaries and attach a dashboard HTML report."""

    ASSOCIATED_TYPES = (OpikEvaluationSummary,)
    ASSOCIATED_ARTIFACT_TYPE = ArtifactType.DATA

    def __init__(self, uri: str, artifact_store: Any = None):
        """Create stable paths for the raw JSON and HTML visualization."""
        super().__init__(uri, artifact_store)
        self.data_path = os.path.join(self.uri, "data.json")
        self.report_path = os.path.join(self.uri, "evaluation_report.html")

    def load(self, data_type: Type[Any]) -> OpikEvaluationSummary:
        """Load the typed summary from its JSON representation."""
        del data_type
        with fileio.open(self.data_path, "r") as f:
            return OpikEvaluationSummary.from_mapping(json.load(f))

    def save(self, data: OpikEvaluationSummary) -> None:
        """Save the summary as JSON so it remains easy to inspect/export."""
        with fileio.open(self.data_path, "w") as f:
            json.dump(data.to_dict(), f, indent=2)

    def save_visualizations(
        self, data: OpikEvaluationSummary
    ) -> Dict[str, VisualizationType]:
        """Attach raw JSON and a customer-friendly HTML report to the artifact."""
        with fileio.open(self.report_path, "w") as f:
            f.write(str(render_opik_evaluation_report(data)))

        return {
            self.report_path.replace("\\", "/"): VisualizationType.HTML,
            self.data_path.replace("\\", "/"): VisualizationType.JSON,
        }

    def extract_metadata(self, data: OpikEvaluationSummary) -> Dict[str, Any]:
        """Expose the main run facts in the ZenML metadata tab."""
        summary = data.to_dict()
        return {
            "dataset_name": summary.get("dataset_name"),
            "project_name": summary.get("project_name"),
            "experiment_name": summary.get("experiment_name"),
            "experiment_url": summary.get("experiment_url"),
            "agent_mode": summary.get("agent_mode"),
            "task_threads": summary.get("task_threads"),
            "judge_model": summary.get("judge_model"),
            "retrieval_k": summary.get("retrieval_k"),
            "metric_count": len(summary.get("metrics") or []),
        }

    def compute_content_hash(self, data: OpikEvaluationSummary) -> str:
        """Hash the JSON payload for deterministic artifact identity."""
        hash_ = hashlib.md5(usedforsecurity=False)
        hash_.update(self.__class__.__name__.encode())
        hash_.update(json.dumps(data.to_dict(), sort_keys=True).encode())
        return hash_.hexdigest()
