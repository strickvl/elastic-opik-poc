# Step 05 — Trace Linking: UI Checklist

> **Important:** the standalone script's mock path can show that `traceparent` injection works, but it cannot validate actual Opik **Trace** links. Real trace-link validation requires the real remote agent path, where Kibana receives the injected header and emits child spans back to Opik.

**Docs:** [Distributed traces with OpenTelemetry](https://www.comet.com/docs/opik/tracing/advanced/log_distributed_traces#distributed-traces-with-a-remote-service-using-opentelemetry) · [Evaluate your LLM](https://www.comet.com/docs/opik/evaluation/evaluate_your_llm/)

Run `python 05_trace_linking.py`, then verify in Opik UI > Experiments > elastic-agent-trace-linked.

- [ ] Each experiment item has a **Trace** link in the Opik UI
- [ ] Clicking the link opens the Kibana agent trace with the full span tree
- [ ] LLM span inside the trace shows `prompt_tokens` and `completion_tokens`
- [ ] The `otel_traceparent` column starts with `00-` (confirms `inject()` is working)
- [ ] `answer_relevance` scores are populated for all items

**If items do not link to traces:**
1. Confirm `call_kibana_agent()` forwards the `headers` dict in the outbound HTTP request
2. Confirm the Kibana OTel SDK is configured with a W3C TraceContext propagator
3. Re-check Step 01 — traces must be flowing into Opik before linking works

---

**Running via the ZenML pipeline?** The same trace-linked evaluation runs as the second step of the ZenML pipeline (`run_trace_linked_evaluation_step`), with the experiment name and agent mode controlled by CLI flags. Use `--agent-mode real` for actual trace linking — the mock agent cannot produce **Trace** links because there is no remote service to receive the injected `traceparent`. See the **Run via ZenML** and **Adapting to real data and a real agent** sections in the top-level `README.md`.
