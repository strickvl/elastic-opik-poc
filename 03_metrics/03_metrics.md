# Step 03 — Metrics: UI Checklist

**Docs:** [Metrics overview](https://www.comet.com/docs/opik/evaluation/metrics/overview/) · [Hallucination](https://www.comet.com/docs/opik/evaluation/metrics/hallucination/) · [Answer relevance](https://www.comet.com/docs/opik/evaluation/metrics/answer_relevance/) · [Context precision](https://www.comet.com/docs/opik/evaluation/metrics/context_precision/)

Run `python 03_metrics.py`. All output is printed to the terminal — no Opik UI needed for this step.

**LLM judges**
- [ ] Hallucination: correct answer scores low (~0.0), hallucinated answer scores high (~1.0)
- [ ] AnswerRelevance: relevant answer scores high, off-topic answer scores low
- [ ] ContextPrecision: relevant context first scores high, irrelevant context first scores low
- [ ] GEval: correct answer scores ~1.0, hallucinated answer scores ~0.0
- [ ] Each LLM judge prints a `reason` string explaining the score

**Retrieval metrics (no LLM)**
- [ ] Perfect retrieval: precision=1.00, recall=1.00, f1=1.00
- [ ] Partial retrieval: precision≈0.67, recall≈0.67, f1≈0.67
- [ ] Complete miss: precision=0.00, recall=0.00, f1=0.00

Proceed to `04_experiments.py`.
