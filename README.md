# Elastic Agent Builder PoC — Opik Validation Scripts

Validation scripts for the Elastic AI Search / Kibana agent PoC. Work through them in order, then consolidate into a single notebook.

## Prerequisites

- Opik workspace and API key — [comet.com/opik](https://www.comet.com/opik)
- OpenAI API key (used by LLM-as-judge metrics)
- Labeled golden dataset of Q&A pairs with ground truth answers and relevant document IDs
- CI reference values for Precision@K, Recall@K, F1@K from your TypeScript pipeline
- OTel traces flowing from the Kibana agent into Opik (see Step 01)

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in your values in .env
```

## Running

| Step | Script | Checklist |
|------|--------|-----------|
| 01  | `01_otel_example/01_otel_example.py` — OTel ingestion, no SDK | `01_otel_example/01_otel_example.md` |
| 02  | `02_datasets/02_datasets.py` — dataset creation, versioning, CRUD | `02_datasets/02_datasets.md` |
| 03  | `03_metrics/03_metrics.py` — metrics standalone validation | `03_metrics/03_metrics.md` |
| 04  | `04_experiments/04_experiments.py` — full eval loop with all metrics | `04_experiments/04_experiments.md` |
| 05  | `05_trace_linking/05_trace_linking.py` — OTel trace to experiment linking | `05_trace_linking/05_trace_linking.md` |

## Before running at scale

Replace `call_kibana_agent()` in `kibana_agent.py` with your real Kibana conversation API call. The mock returns random answers and doc IDs — retrieval metric parity with CI is only verifiable against the real agent.
