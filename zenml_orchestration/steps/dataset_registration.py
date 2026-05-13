"""ZenML step for registering the Opik dataset."""

from typing import Annotated, Any, Dict

from zenml import ArtifactConfig, log_metadata, step

from zenml_orchestration.dataset_registration import register_opik_dataset

_DATASET_ARTIFACT_TAGS = ["elastic", "opik", "dataset"]


@step(enable_cache=False)
def register_dataset_step(
    source: str = "mock",
    update_existing: bool = False,
) -> Annotated[
    Dict[str, Any],
    ArtifactConfig(name="opik_dataset_registration", tags=_DATASET_ARTIFACT_TAGS),
]:
    """Register/update the Opik dataset before evaluation."""
    summary = register_opik_dataset(
        source=source,  # type: ignore[arg-type]
        update_existing=update_existing,
    )

    log_metadata(
        metadata={
            "dataset_name": summary.get("dataset_name"),
            "project_name": summary.get("project_name"),
            "source": summary.get("source"),
            "inserted": summary.get("inserted"),
            "updated": summary.get("updated"),
            "skipped": summary.get("skipped"),
            "unchanged": summary.get("unchanged"),
            "changed_not_updated": summary.get("changed_not_updated"),
            "total_items_after": summary.get("total_items_after"),
            "update_existing": update_existing,
        }
    )
    return summary
