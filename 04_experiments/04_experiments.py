"""
Step 04 — Experiments

opik.evaluate() runs each task function against every dataset item, scores the
results with the metrics defined in 03_metrics.py, and logs everything to Opik
as a named experiment. Experiments are pinned to a specific dataset version so
results are always reproducible.

This script demonstrates:
  - The full eval loop with all test plan metrics
  - experiment_config capturing git SHA, model, and agent version for reproducibility
  - Retrieval metrics (Precision@K, Recall@K, F1@K) compared against ground truth

⚠  Scores will be low / random until call_kibana_agent() in kibana_agent.py is
   replaced with the real Kibana API.

Docs: https://www.comet.com/docs/opik/evaluation/evaluate_your_llm/

Usage:
    python 04_experiments/04_experiments.py
"""

import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))           # root
sys.path.insert(0, str(Path(__file__).parent.parent / "03_metrics"))  # metrics

import opik
from opik.evaluation.metrics import AnswerRelevance, ContextPrecision, Hallucination

from kibana_agent import DATASET_NAME, K, PROJECT_NAME, task_fn
from metrics import F1AtK, PrecisionAtK, RecallAtK, SequenceFidelity


def get_git_metadata():
    def _run(cmd):
        try:
            return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return "unknown"
    return {
        "git_sha": _run(["git", "rev-parse", "--short=8", "HEAD"]),
        "git_branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
    }

client = opik.Opik()
dataset = client.get_dataset(name=DATASET_NAME)

experiment_config = {
    **get_git_metadata(),
    "model": "gpt-4o",
    "agent_version": "kibana-8.14.0",
    "ranking_size": K,
    "dataset": DATASET_NAME,
}

print(f"Config: {experiment_config}\n")

results = opik.evaluate(
    dataset=dataset,
    task=task_fn,
    scoring_metrics=[
        Hallucination(name="factuality"),
        ContextPrecision(name="groundedness"),
        AnswerRelevance(name="relevance"),
        SequenceFidelity(),
        PrecisionAtK(k=K),
        RecallAtK(k=K),
        F1AtK(k=K),
    ],
    experiment_name="elastic-agent-baseline",
    experiment_config=experiment_config,
    project_name=PROJECT_NAME,
    task_threads=4,
)

print(f"\nDone. View results: {results.experiment_url}")
print("See 04_experiments.md for the UI checklist.")
