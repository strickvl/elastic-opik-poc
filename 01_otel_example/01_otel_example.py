"""
Step 01 — OTel Native Ingestion

Runs the mock Kibana agent (kibana_agent.py) and verifies that OTel traces
appear in Opik without the Opik SDK in the app code. This is the pattern for
teams who already have an OTel pipeline (e.g. a TypeScript Kibana agent) and
want Opik to receive those traces.

HOW OPIK MAPS OTEL ATTRIBUTES
==============================
Opik runs a rule-based mapper on every incoming OTLP span. Key mappings:

  ATTRIBUTE                          → OPIK FIELD
  ─────────────────────────────────────────────────────────────────────────────
  input / input.*                    → input
  output / output.*                  → output
  thread_id                          → thread_id       (groups traces in UI)
  gen_ai.conversation.id             → thread_id       (same effect)
  opik.tags                          → tags
  opik.metadata.*                    → metadata

  gen_ai.system                      → provider        (sets span type = llm)
  gen_ai.request.model               → model           (sets span type = llm)
  gen_ai.response.model              → model           (sets span type = llm)
  gen_ai.usage.input_tokens          → usage.prompt_tokens
  gen_ai.usage.output_tokens         → usage.completion_tokens

  llm.model_name                     → model           (OpenInference alt.)
  llm.token_count.prompt             → usage.prompt_tokens
  llm.token_count.completion         → usage.completion_tokens

Docs: https://www.comet.com/docs/opik/tracing/integrations/opentelemetry/

Usage:
    python 01_otel_example/01_otel_example.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kibana_agent import PROJECT_NAME, SAMPLE_QUERIES, call_kibana_agent

if __name__ == "__main__":
    print(f"Sending OTel traces to Opik project '{PROJECT_NAME}' ...\n")

    for i, query in enumerate(SAMPLE_QUERIES, 1):
        print(f"[{i}/{len(SAMPLE_QUERIES)}] {query}")
        response = call_kibana_agent(query)
        print(f"    -> {response.text[:80]}\n")

    print("Done. See 01_otel_example.md for the UI checklist.")
