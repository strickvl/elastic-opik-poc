# Step 03 — Experiments: UI Checklist

**Docs:** [Evaluate your LLM](https://www.comet.com/docs/opik/evaluation/evaluate_your_llm/) · [Python SDK reference](https://www.comet.com/docs/opik/python-sdk-reference/)

Run `python 04_experiments.py`, then verify in Opik UI > Experiments.

- [ ] Experiment `elastic-agent-baseline` is listed
- [ ] Each item shows `hallucination` and `answer_relevance` scores
- [ ] Each item shows `input_tokens`, `output_tokens`, `cost_usd`, `latency_ms`
- [ ] Experiment config shows `git_sha`, `git_branch`, `model`, `agent_version`
- [ ] Dataset version is pinned in the experiment detail

Proceed to `05_metrics_eval.py`.
