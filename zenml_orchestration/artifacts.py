"""Typed ZenML artifacts for the Elastic Opik orchestration layer."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

from pydantic import BaseModel, ConfigDict, Field


class MetricScore(BaseModel):
    """Score for one metric on one dataset item."""

    value: Optional[float] = None
    scoring_failed: bool = False
    reason: Optional[str] = None
    category_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricAggregate(BaseModel):
    """Aggregate statistics for one metric across an experiment."""

    mean: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    std: Optional[float] = None
    values: List[float] = Field(default_factory=list)
    failed_count: int = 0


class EvaluationItemResult(BaseModel):
    """Per-item evaluation result captured from Opik's test results."""

    dataset_item_id: str
    trace_id: Optional[str] = None
    trial_id: int
    input: Optional[Any] = None
    output: Optional[Any] = None
    otel_traceparent: Optional[str] = None
    task_execution_time: Optional[float] = None
    scoring_time: Optional[float] = None
    scores: Dict[str, MetricScore] = Field(default_factory=dict)


class OpikEvaluationResults(BaseModel):
    """Structured score artifact for one Opik evaluation run."""

    model_config = ConfigDict(extra="allow")

    dataset_name: str
    project_name: str
    experiment_id: Optional[str] = None
    dataset_id: Optional[str] = None
    experiment_name: str
    experiment_url: Optional[str] = None
    zenml_run_name: Optional[str] = None
    agent_mode: str
    task_threads: int
    judge_model: str
    retrieval_k: int
    metrics: List[str] = Field(default_factory=list)
    aggregate_scores: Dict[str, MetricAggregate] = Field(default_factory=dict)
    item_results: List[EvaluationItemResult] = Field(default_factory=list)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "OpikEvaluationResults":
        """Build results from a JSON-like payload."""
        return cls.model_validate(payload)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-friendly representation."""
        return self.model_dump(mode="json")

    def score_means(self) -> Dict[str, Optional[float]]:
        """Return metric mean values keyed by metric name."""
        return {
            name: aggregate.mean
            for name, aggregate in self.aggregate_scores.items()
        }


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
    experiment_id: Optional[str] = None
    dataset_id: Optional[str] = None
    agent_mode: str
    task_threads: int
    judge_model: str
    retrieval_k: int
    metrics: List[str] = Field(default_factory=list)
    score_means: Dict[str, Optional[float]] = Field(default_factory=dict)
    failed_counts: Dict[str, int] = Field(default_factory=dict)

    @classmethod
    def from_mapping(cls, summary: Mapping[str, Any]) -> "OpikEvaluationSummary":
        """Build a summary from the dict returned by the Opik evaluation helper."""
        return cls(
            dataset_name=_text(summary.get("dataset_name"), "unknown"),
            project_name=_text(summary.get("project_name"), "unknown"),
            experiment_name=_text(summary.get("experiment_name"), "unknown"),
            experiment_url=_optional_text(summary.get("experiment_url")),
            experiment_id=_optional_text(summary.get("experiment_id")),
            dataset_id=_optional_text(summary.get("dataset_id")),
            agent_mode=_text(summary.get("agent_mode"), "unknown"),
            task_threads=_int(summary.get("task_threads"), default=1),
            judge_model=_text(summary.get("judge_model"), "unknown"),
            retrieval_k=_int(summary.get("retrieval_k"), default=3),
            metrics=[str(metric) for metric in (summary.get("metrics") or [])],
            score_means=dict(summary.get("score_means") or {}),
            failed_counts={
                str(key): int(value)
                for key, value in dict(summary.get("failed_counts") or {}).items()
            },
            **_extra_fields(summary, _SUMMARY_FIELDS),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-friendly dictionary for display and materialization."""
        return self.model_dump(mode="json")


class ComparisonMetricValue(BaseModel):
    """One metric value in a comparison table."""

    value: Optional[float] = None
    delta_from_baseline: Optional[float] = None
    failed_count: int = 0


class ComparisonExperiment(BaseModel):
    """One experiment column in a comparison report."""

    label: str
    experiment_name: str
    experiment_id: Optional[str] = None
    experiment_url: Optional[str] = None
    zenml_run_name: Optional[str] = None
    agent_mode: str
    judge_model: str
    retrieval_k: int
    metrics: Dict[str, ComparisonMetricValue] = Field(default_factory=dict)


class OpikEvaluationComparison(BaseModel):
    """Static comparison report across multiple Opik evaluation result artifacts."""

    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    baseline_label: Optional[str] = None
    metric_names: List[str] = Field(default_factory=list)
    experiments: List[ComparisonExperiment] = Field(default_factory=list)

    @classmethod
    def from_results(
        cls,
        results: List[OpikEvaluationResults],
        *,
        labels: Optional[List[str]] = None,
    ) -> "OpikEvaluationComparison":
        """Build a comparison payload from completed evaluation results."""
        if not results:
            raise ValueError("At least one evaluation result is required.")

        labels = labels or [result.experiment_name for result in results]
        baseline = results[0]
        metric_names = _ordered_metric_names(results)
        baseline_means = baseline.score_means()

        experiments: List[ComparisonExperiment] = []
        for index, result in enumerate(results):
            result_means = result.score_means()
            metric_values: Dict[str, ComparisonMetricValue] = {}
            for metric_name in metric_names:
                value = result_means.get(metric_name)
                baseline_value = baseline_means.get(metric_name)
                delta = _delta(value, baseline_value)
                aggregate = result.aggregate_scores.get(metric_name)
                metric_values[metric_name] = ComparisonMetricValue(
                    value=value,
                    delta_from_baseline=delta,
                    failed_count=aggregate.failed_count if aggregate else 0,
                )

            experiments.append(
                ComparisonExperiment(
                    label=labels[index] if index < len(labels) else result.experiment_name,
                    experiment_name=result.experiment_name,
                    experiment_id=result.experiment_id,
                    experiment_url=result.experiment_url,
                    zenml_run_name=result.zenml_run_name,
                    agent_mode=result.agent_mode,
                    judge_model=result.judge_model,
                    retrieval_k=result.retrieval_k,
                    metrics=metric_values,
                )
            )

        return cls(
            baseline_label=experiments[0].label,
            metric_names=metric_names,
            experiments=experiments,
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "OpikEvaluationComparison":
        """Build a comparison from a JSON-like payload."""
        return cls.model_validate(payload)

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-friendly representation."""
        return self.model_dump(mode="json")


_SUMMARY_FIELDS = {
    "dataset_name",
    "project_name",
    "experiment_name",
    "experiment_url",
    "experiment_id",
    "dataset_id",
    "agent_mode",
    "task_threads",
    "judge_model",
    "retrieval_k",
    "metrics",
    "score_means",
    "failed_counts",
}


def _ordered_metric_names(results: List[OpikEvaluationResults]) -> List[str]:
    names: List[str] = []
    for result in results:
        for metric_name in result.metrics:
            if metric_name not in names:
                names.append(metric_name)
        for metric_name in result.aggregate_scores:
            if metric_name not in names:
                names.append(metric_name)
    return names


def _delta(value: Optional[float], baseline: Optional[float]) -> Optional[float]:
    if value is None or baseline is None:
        return None
    return value - baseline


def _extra_fields(summary: Mapping[str, Any], known_fields: set[str]) -> Dict[str, Any]:
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


__all__ = [
    "ComparisonExperiment",
    "ComparisonMetricValue",
    "EvaluationItemResult",
    "MetricAggregate",
    "MetricScore",
    "OpikEvaluationComparison",
    "OpikEvaluationResults",
    "OpikEvaluationSummary",
]
