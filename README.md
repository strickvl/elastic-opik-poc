# Elastic Agent Builder PoC — Opik Validation Playbook

A small, hands-on playbook for validating the Elastic AI Search / Kibana agent with [Opik](https://www.comet.com/opik). Work through the numbered scripts in order to confirm that traces, datasets, metrics, experiments, and trace-linked evaluations all behave as expected against your agent. An optional ZenML pipeline at the end ties the dataset and trace-linked evaluation steps into a single repeatable run.

## What this repo does

Two complementary surfaces, each with a clear job:

- **Opik** owns the trace store, the golden dataset (with versioning), the built-in and custom metrics, the experiments, and the per-item scores. This is where your team will spend the most time inspecting agent behaviour.
- **ZenML** (optional) wraps the last two steps of the playbook into a single two-step pipeline. It does not replace Opik. It adds repeatable runs, captured config, run history, lineage between runs, and customer-friendly handoff artifacts — a typed evaluation summary with JSON + HTML views, plus a clickable Opik experiment link — so the "register dataset → run trace-linked eval" flow can be triggered consistently from CI or locally.

| Concern | Owned by |
|---|---|
| OTel trace ingestion | Opik |
| Golden dataset + versioning | Opik |
| Built-in & custom metrics | Opik |
| Experiment rows + per-item scores | Opik |
| Trace ↔ experiment-item linking (W3C `traceparent`) | Opik |
| Orchestrating "register dataset → run trace-linked eval" | ZenML |
| Run config capture, run history, run lineage | ZenML |

## Prerequisites

- An Opik workspace and API key — [comet.com/opik](https://www.comet.com/opik).
- An LLM-judge provider key. The default judge is `openrouter/anthropic/claude-sonnet-4.5`, so `OPENROUTER_API_KEY` is the standard choice. You can override the model with `--judge-model`.
- A labeled golden Q&A dataset with ground-truth answers and relevant document IDs. A mock seed is provided so you can smoke-test without one; for real evaluation, see [Adapting to real data and a real agent](#adapting-to-real-data-and-a-real-agent).
- Reference Precision@K, Recall@K, and F1@K values from your existing TypeScript pipeline. These let you sanity-check retrieval parity once you're on the real agent.
- OTel traces flowing from the Kibana agent into Opik — Step 01 walks through this.

## Setup

```bash
cd /path/to/elastic-opik-poc
pip install -r requirements.txt        # or: uv pip install -r requirements.txt
cp .env.example .env
# Fill in the values in .env — see the next section
zenml init                             # run once from the repo root
```

Run commands from the repo root. `zenml init` gives ZenML a source root for this project, so local runs and remote Docker builds know which files belong with the pipeline.

### Environment variables

The full list lives in `.env.example`. Grouped by what they're for:

- **Opik (always required):** `OPIK_API_KEY`, `OPIK_WORKSPACE`, `OPIK_PROJECT_NAME`, `DATASET_NAME`.
- **LLM judge (always required):** `OPENROUTER_API_KEY`, or `OPENROUTER_API_BASE` if you're routing through an enterprise endpoint.
- **GCS dataset source (real path only):** `GCS_BUCKET`, `GCS_OBJECT`.
- **Kibana agent (real path only):** `KIBANA_URL`, `KIBANA_API_KEY` (or `KIBANA_USERNAME` / `KIBANA_PASSWORD`), `KIBANA_API_KEY_ID`, `KIBANA_AGENT_ID`, `KIBANA_SPACE`, `KIBANA_CONNECTOR_ID`.

You only need the Opik + judge variables to run the mock smoke path. GCS and Kibana variables are required exclusively for the real run.

## The Opik playbook (numbered steps)

Work through these in order. Each script has a short Markdown checklist alongside it that tells you what to verify in the Opik UI before moving on.

| Step | Script | UI checklist |
|------|--------|--------------|
| 01 | `01_otel_example/01_otel_example.py` — raw OTel ingestion, no Opik SDK | `01_otel_example/01_otel_example.md` |
| 02 | `02_datasets/02_datasets.py` — dataset creation, versioning, CRUD | `02_datasets/02_datasets.md` |
| 03 | `03_metrics/03_metrics.py` — metrics validated in isolation | `03_metrics/03_metrics.md` |
| 04 | `04_experiments/04_experiments.py` — full eval loop with all metrics | `04_experiments/04_experiments.md` |
| 05 | `05_trace_linking/05_trace_linking.py` — OTel traces linked to experiment items | `05_trace_linking/05_trace_linking.md` |

These scripts are deliberately readable and side-effect-heavy: Step 02 mutates the dataset version a few times so you can see Opik's versioning work, and Step 05 talks to the Kibana agent. Run them with `python` or `uv run python`.

## Run via ZenML (the two-step pipeline)

Once you have the numbered playbook understood, the ZenML pipeline lets you run Steps 02 + 05 as a single repeatable job.

The ZenML code lives in a conventional small layout under `zenml_orchestration/`: step wrappers in `steps/`, the pipeline in `pipelines/`, a custom materializer in `materializers/`, and dashboard HTML helpers in `visualizations/`. The old `zenml_orchestration.pipeline` import path still works as a compatibility re-export.

### What the pipeline does

Two steps, in order:

1. **`register_dataset_step`** — reads the desired Opik dataset rows (from the mock seed or from GCS), compares them against what's already in Opik by `input`, and inserts / updates / skips so the run is idempotent. Note that the original Step 02 *script* intentionally mutates dataset versions to demonstrate Opik's versioning; this pipeline *step* deliberately does not, because reruns shouldn't churn versions. Returns a small summary: `inserted`, `updated`, `skipped`, `total_items_after`.
2. **`run_trace_linked_evaluation_step`** — calls `opik.evaluate(...)` with the same metric stack as Step 05, builds an OTel `traceparent` for each dataset item, and invokes either the mock or the real Kibana agent. Returns a typed `opik_evaluation_summary` artifact with both raw JSON and a clean HTML report, plus a small `HTMLString` artifact with a one-click link to the Opik experiment.

The second step consumes the first step's `dataset_info` artifact, so the DAG correctly reflects the real dependency: evaluation only runs after the dataset is registered. Caching is disabled on both steps — these are real remote calls, and a cached "success" would be misleading.

### Mock smoke run

This proves the wiring works end-to-end without needing GCS or a live Kibana service. The mock agent returns random answers and random doc IDs, so the scores will not be meaningful — that's expected. What you're checking is that the pipeline shape is correct.

```bash
python run_zenml_pipeline.py --config configs/zenml_mock_smoke.yaml
```

If you prefer flags instead of YAML, this is equivalent:

```bash
python run_zenml_pipeline.py \
  --dataset-source mock \
  --agent-mode mock \
  --experiment-name elastic-agent-trace-linked-zenml-smoke
```

### Real run

After Opik, OpenRouter, GCS, and Kibana variables are configured, switch to the real dataset and the real agent:

```bash
python run_zenml_pipeline.py --config configs/zenml_real.yaml
```

You can still override one config value from the CLI, for example:

```bash
python run_zenml_pipeline.py \
  --config configs/zenml_real.yaml \
  --experiment-name elastic-agent-real-trace-linked-zenml-2026-05-13
```

### CLI flags

| Flag | Default | What it does |
|---|---|---|
| `--dataset-source` | `mock` | `mock` uses the seed rows; `gcs` loads from `gs://$GCS_BUCKET/$GCS_OBJECT`. |
| `--agent-mode` | `mock` | `mock` uses the canned agent; `real` calls the Kibana API. |
| `--experiment-name` | `elastic-agent-trace-linked-zenml` | Name shown in Opik's Experiments tab. |
| `--task-threads` | `1` | Keep at 1 while validating trace links; raise later for speed. |
| `--judge-model` | `openrouter/anthropic/claude-sonnet-4.5` | LLM judge passed to factuality / groundedness / relevance. |
| `--update-existing` / `--no-update-existing` | off | If set, the dataset step updates changed rows instead of skipping them. The negative form is handy when overriding a YAML config. |
| `--config` | — | Optional ZenML YAML config applied via `pipeline.with_options(config_path=...)`. |

### Config files

Two lightweight configs are included:

- `configs/zenml_mock_smoke.yaml` — mock dataset + mock agent; useful for checking the orchestration shape without GCS or Kibana.
- `configs/zenml_real.yaml` — GCS dataset + real Kibana agent; use this when real credentials and services are available.

Credentials still come from environment variables / `.env`. The configs intentionally do not contain secrets, and you do not need to create ZenML secrets for this PoC. For remote real runs, `configs/zenml_real.yaml` adds only the basic GCS + Kibana runtime variables. If your environment needs optional values like `OPENROUTER_API_BASE`, `RETRIEVAL_K`, basic auth, or Kibana space/connector IDs, add those to `settings.docker.runtime_environment` in your local config.

### Lightweight local validation

Before making remote Opik/OpenRouter/Kibana calls, you can check that the Python modules, config files, and imports are structurally sound:

```bash
python -m compileall zenml_orchestration run_zenml_pipeline.py
python -c "from zenml_orchestration.pipelines.elastic_opik import elastic_opik_zenml_pipeline; print(elastic_opik_zenml_pipeline.name)"
python run_zenml_pipeline.py --help
```

A real pipeline run still needs Opik + judge credentials, even in mock mode, because `opik.evaluate(...)` and the LLM judge metrics make external calls.

### How to validate a run

**In the ZenML dashboard:**

- [ ] The run has exactly two steps: `register_dataset_step` and `run_trace_linked_evaluation_step`.
- [ ] The `opik_dataset_registration` metadata shows the expected `inserted` / `updated` / `skipped` counts. On a second run with no changes, every row should be reported as unchanged.
- [ ] The `opik_evaluation_summary` artifact / evaluation metadata records dataset name, project name, agent mode, judge model, task threads, and the Opik experiment URL.
- [ ] The `opik_evaluation_summary` **Visualization** tab includes the clean HTML report. Use the JSON visualization on the same artifact when you want the raw handoff payload.
- [ ] The `opik_experiment_link` HTML artifact opens the experiment in Opik.

**In Opik:**

- [ ] An experiment with the configured name exists under the project.
- [ ] Scores are populated for `factuality`, `groundedness`, `relevance`, `sequence_fidelity`, `precision_at_3`, `recall_at_3`, and `f1_at_3`.
- [ ] The `otel_traceparent` column is present on each experiment item and (in real mode) starts with `00-`.
- [ ] In real mode only: each item has a working **Trace** link that opens the full Kibana span tree. With the mock agent this link will not appear — the Step 05 doc explains why.

## Adapting to real data and a real agent

Two switches turn the smoke run into a real evaluation.

**1. Real dataset (`--dataset-source gcs`).** The GCS loader in `zenml_orchestration/dataset_registration.py` expects a CSV at `gs://$GCS_BUCKET/$GCS_OBJECT` with these columns:

- `input_question` — mapped to Opik's `input`
- `output_expected` — mapped to Opik's `expected_output`
- `gt_elastic_knowledge_base` — a Python-literal list or dict of relevant doc IDs, parsed into Opik's `relevant_doc_ids`

If your dataset has a different shape, edit `load_gcs_items` in that file — that's the only place the column mapping lives.

**2. Real agent (`--agent-mode real`).** `kibana_agent.py` exposes both `call_kibana_agent` (mock) and `call_real_kibana_agent` (the real HTTP path). For trace linking to actually work end-to-end, two things have to be true:

- The real call must forward the `headers` dict it receives in the outbound HTTP request.
- Your Kibana / TypeScript service must configure its OTel SDK with a W3C TraceContext propagator, so it picks up the `traceparent` header from the incoming request and starts its root span as a child of the Opik evaluation span.

Without both, traces will still be created but they will not link to Opik experiment items. The Step 05 checklist (`05_trace_linking/05_trace_linking.md`) covers the troubleshooting steps in more detail.

## Limitations and out of scope

This is a focused PoC, not a productionised system. Intentionally not included:

- A generic Opik → ZenML migration tool. The orchestration helpers here are tailored to this Elastic flow.
- Post-experiment comparison reports or significance testing across runs.
- Replacing Opik datasets, traces, or experiment tracking with ZenML equivalents. Opik stays the source of truth for evaluation data.
- TypeScript / Kibana service changes. The Kibana side must already forward and accept W3C trace context for trace linking to work; this repo only documents that requirement.

Other things worth knowing:

- **Mock trace linking does not actually link.** With the mock agent, `inject()` writes a `traceparent` but there is no remote service to consume it, so experiment items will not have **Trace** links in the Opik UI. This is expected and is the reason for the real-agent path. See the warning at the top of `05_trace_linking/05_trace_linking.py`.
- **Default `task_threads=1`.** Parallel evaluation makes trace debugging harder. Raise it only after you have confirmed trace linking works end-to-end.
- **Dataset registration is deliberately conservative.** Existing rows are matched by `input`. Changed rows are skipped unless you pass `--update-existing`, and extra rows already in Opik are never deleted.

## Repo layout

```
elastic-opik-poc/
├── 01_otel_example/        # Step 01 — raw OTel ingestion
├── 02_datasets/            # Step 02 — dataset CRUD + versioning
├── 03_metrics/             # Step 03 — metric validation (incl. custom metrics)
├── 04_experiments/         # Step 04 — full eval loop
├── 05_trace_linking/       # Step 05 — OTel → experiment trace linking
├── kibana_agent.py         # mock + real Kibana agent calls
├── configs/                # lightweight ZenML run configs
│   ├── zenml_mock_smoke.yaml
│   └── zenml_real.yaml
├── zenml_orchestration/    # optional ZenML orchestration layer
│   ├── dataset_registration.py  # runtime helper: Opik dataset registration
│   ├── artifacts.py             # typed ZenML artifacts
│   ├── evaluation.py            # runtime helper: Opik trace-linked eval
│   ├── pipeline.py              # backwards-compatible re-export
│   ├── materializers/           # custom artifact materializers + visualizations
│   ├── pipelines/               # ZenML @pipeline definitions
│   ├── steps/                   # ZenML @step wrappers
│   └── visualizations/          # small dashboard HTML helper/templates
├── run_zenml_pipeline.py   # CLI entrypoint for the ZenML pipeline
└── docs/plans/             # background design notes
```
