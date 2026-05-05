"""
Step 03 — Metrics Standalone Validation

Defines and calls each metric from the Elastic PoC test plan in isolation,
before running them inside an experiment loop in Step 04.

LLM judges (require OPENAI_API_KEY):
    Factuality       — does the answer contain claims not supported by the context?
    Groundedness     — is the retrieved context ranked in order of relevance?
    Relevance        — does the answer address the question?
    SequenceFidelity — does the answer follow the correct order when sequence matters?

Retrieval metrics (no LLM):
    Precision@K, Recall@K, F1@K

The metric classes are importable — 04_experiments.py imports them directly
from utils.py rather than redefining them.

Docs: https://www.comet.com/docs/opik/evaluation/metrics/overview/

Usage:
    python 03_metrics/03_metrics.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # root
sys.path.insert(0, str(Path(__file__).parent))          # 03_metrics/

from opik.evaluation.metrics import AnswerRelevance, ContextPrecision, Hallucination

from kibana_agent import K, call_kibana_agent
from metrics import F1AtK, PrecisionAtK, RecallAtK, SequenceFidelity


# ---------------------------------------------------------------------------
# Main — call the agent and score its output with each metric
# ---------------------------------------------------------------------------

def main():
    INPUT    = "What is ELSER and how does it enable semantic search?"
    EXPECTED = "ELSER is a sparse embedding model trained by Elastic that enables semantic search without a separate embedding service."

    response = call_kibana_agent(INPUT)
    OUTPUT   = response.text
    CONTEXT  = [str(d) for d in response.retrieved_documents]

    print(f"Agent output: {OUTPUT}\n")

    print(Hallucination(name="factuality").score(input=INPUT, output=OUTPUT, context=CONTEXT))
    print(ContextPrecision(name="groundedness").score(input=INPUT, output=OUTPUT, expected_output=EXPECTED, context=CONTEXT))
    print(AnswerRelevance(name="relevance").score(input=INPUT, output=OUTPUT, context=CONTEXT))
    print(SequenceFidelity().score(input=INPUT, output=OUTPUT))

    retrieved = response.retrieved_documents
    relevant  = ["doc-001", "doc-003", "doc-005"]

    print(PrecisionAtK(k=K).score(retrieved_ids=retrieved, relevant_ids=relevant))
    print(RecallAtK(k=K).score(retrieved_ids=retrieved, relevant_ids=relevant))
    print(F1AtK(k=K).score(retrieved_ids=retrieved, relevant_ids=relevant))

    print("\nSee 03_metrics.md for the checklist. Proceed to 04_experiments.py")


if __name__ == "__main__":
    main()
