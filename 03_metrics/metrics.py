"""
Metric class definitions for the Elastic PoC evaluation.

Imported by 03_metrics.py (standalone validation), 04_experiments.py, and
05_trace_linking.py. Define or adjust metrics here and they update everywhere.
"""

from typing import Any, List

import pydantic
from opik.evaluation.metrics import BaseMetric
from opik.evaluation.metrics.score_result import ScoreResult
from opik.evaluation.models import LiteLLMChatModel


# ---------------------------------------------------------------------------
# Custom LLM judge — Sequence Fidelity
# ---------------------------------------------------------------------------

class _Output(pydantic.BaseModel):
    score: float
    reason: str


class SequenceFidelity(BaseMetric):
    """Scores whether the answer presents steps in the correct logical order."""

    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__(name="sequence_fidelity")
        self._model = LiteLLMChatModel(model_name=model)

    def score(self, input: str, output: str, **kwargs: Any) -> ScoreResult:
        messages = [
            {"role": "system", "content": (
                "You are evaluating an AI search agent built on Elasticsearch and Kibana. "
                "Some answers describe multi-step processes where order matters."
            )},
            {"role": "user", "content": (
                f"Question: {input}\nAnswer: {output}\n\n"
                "Does the answer present steps or concepts in the correct logical sequence? "
                "Score 1.0 = correct order, 0.5 = minor issue, 0.0 = wrong order or no sequence. "
                'Respond with JSON: {"score": <float>, "reason": "<string>"}'
            )},
        ]
        raw = self._model.generate_chat_completion(messages=messages, response_format=_Output)
        parsed = _Output.model_validate_json(raw["content"])
        return ScoreResult(name=self.name, value=parsed.score, reason=parsed.reason)


# ---------------------------------------------------------------------------
# Custom retrieval metrics
# ---------------------------------------------------------------------------

class PrecisionAtK(BaseMetric):
    def __init__(self, k: int = 3):
        super().__init__(name=f"precision_at_{k}")
        self.k = k

    def score(self, retrieved_ids: List[str], relevant_ids: List[str], **kwargs) -> ScoreResult:
        hits = len(set(retrieved_ids[: self.k]) & set(relevant_ids))
        return ScoreResult(name=self.name, value=hits / self.k if self.k else 0.0)


class RecallAtK(BaseMetric):
    def __init__(self, k: int = 3):
        super().__init__(name=f"recall_at_{k}")
        self.k = k

    def score(self, retrieved_ids: List[str], relevant_ids: List[str], **kwargs) -> ScoreResult:
        if not relevant_ids:
            return ScoreResult(name=self.name, value=0.0)
        hits = len(set(retrieved_ids[: self.k]) & set(relevant_ids))
        return ScoreResult(name=self.name, value=hits / len(relevant_ids))


class F1AtK(BaseMetric):
    def __init__(self, k: int = 3):
        super().__init__(name=f"f1_at_{k}")
        self.k = k

    def score(self, retrieved_ids: List[str], relevant_ids: List[str], **kwargs) -> ScoreResult:
        p = PrecisionAtK(self.k).score(retrieved_ids=retrieved_ids, relevant_ids=relevant_ids).value
        r = RecallAtK(self.k).score(retrieved_ids=retrieved_ids, relevant_ids=relevant_ids).value
        f1 = (2 * p * r) / (p + r) if (p + r) > 0 else 0.0
        return ScoreResult(name=self.name, value=f1)
