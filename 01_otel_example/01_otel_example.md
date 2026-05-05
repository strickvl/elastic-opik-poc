# Step 01 — OTel Example: UI Checklist

**Docs:** [OpenTelemetry overview](https://www.comet.com/docs/opik/tracing/opentelemetry/overview) · [Distributed traces](https://www.comet.com/docs/opik/tracing/advanced/log_distributed_traces#distributed-traces-with-a-remote-service-using-opentelemetry)

Run `python 01_otel_example.py`, then verify in Opik UI > Projects > elastic-poc > Traces.

- [ ] 3 traces appear, one per sample query
- [ ] Root span `kibana.agent` shows the question as **input** and the answer as **output**
- [ ] Traces are tagged `elastic`, `kibana`, `demo`
- [ ] Child span `llm.chat` shows **model** (gpt-4o), **provider** (openai), and token counts
- [ ] Child span `elasticsearch.search` is visible in the span tree
- [ ] Metadata panel on the root span shows `agent_version` and `environment`

Proceed to `01_otel_validation.md`.
