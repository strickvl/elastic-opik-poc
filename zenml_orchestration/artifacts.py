"""Typed ZenML artifacts for the Elastic Opik orchestration layer."""

from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field


class OpikEvaluationSummary(BaseModel):
    """Small typed wrapper around the Opik evaluation summary dictionary.

    The runtime helper naturally produces a plain dictionary. Wrapping it in a
    named Pydantic model gives ZenML a specific Python type to attach a custom
    materializer and dashboard visualization to, without changing the actual
    fields customers care about.
    """

    model_config = ConfigDict(extra="allow")

    dataset_name: str
    project_name: str
    experiment_name: str
    experiment_url: Optional[str] = None
    agent_mode: str
    task_threads: int
    judge_model: str
    retrieval_k: int
    metrics: List[str] = Field(default_factory=list)

    @classmethod
    def from_mapping(cls, summary: Mapping[str, Any]) -> "OpikEvaluationSummary":
        """Build a summary from the dict returned by the Opik evaluation helper."""
        return cls(
            dataset_name=_text(summary.get("dataset_name"), "unknown"),
            project_name=_text(summary.get("project_name"), "unknown"),
            experiment_name=_text(summary.get("experiment_name"), "unknown"),
            experiment_url=_optional_text(summary.get("experiment_url")),
            agent_mode=_text(summary.get("agent_mode"), "unknown"),
            task_threads=_int(summary.get("task_threads"), default=1),
            judge_model=_text(summary.get("judge_model"), "unknown"),
            retrieval_k=_int(summary.get("retrieval_k"), default=3),
            metrics=[str(metric) for metric in (summary.get("metrics") or [])],
            **_extra_fields(summary),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-friendly dictionary for display and materialization."""
        return self.model_dump(mode="json")


def _extra_fields(summary: Mapping[str, Any]) -> Dict[str, Any]:
    known_fields = {
        "dataset_name",
        "project_name",
        "experiment_name",
        "experiment_url",
        "agent_mode",
        "task_threads",
        "judge_model",
        "retrieval_k",
        "metrics",
    }
    return {key: value for key, value in summary.items() if key not in known_fields}


def _int(value: Any, *, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


def _optional_text(value: Any) -> Optional[str]:
    text = _text(value)
    return text or None


def _text(value: Any, default: str = "") -> str:
    if value is None or value == "":
        return default
    return str(value)


__all__ = ["OpikEvaluationSummary"]
