"""
Step 05 — OTel Trace to Experiment Linking

⚠  Highest technical risk step. Complete Steps 01 and 03 before running this.

When an experiment runs, Opik creates one item per dataset row. Normally those
items show scores but have no link back to the live agent's trace. This step
closes that gap: by injecting a W3C traceparent header into the Kibana API call,
the agent's OTel trace is started as a child of the Opik-created evaluation
span, so clicking an experiment item opens the full Kibana trace — including
every retrieval, reranking, and LLM span — directly in the Opik UI.

How it works:
  1. opik.evaluate() creates a span for each dataset item
  2. opentelemetry.propagate.inject() writes the active traceparent into a
     headers dict
  3. call_kibana_agent() forwards those headers in the outbound HTTP request
  4. The Kibana agent's OTel SDK picks up the traceparent and starts its root
     span as a child, linking the two traces together

⚠  With the mock agent, trace linking is not verifiable in the UI — inject()
   writes from OTel's global context, but Opik's evaluation engine manages its
   span context internally and does not propagate it there. With the real
   TypeScript Kibana agent, the OTel SDK picks up the traceparent header
   automatically from the incoming HTTP request and links the spans.

Docs: https://www.comet.com/docs/opik/tracing/advanced/log_distributed_traces#distributed-traces-with-a-remote-service-using-opentelemetry

Usage:
    python 05_trace_linking/05_trace_linking.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from zenml_orchestration.evaluation import run_trace_linked_evaluation


def main() -> None:
    """Run the original standalone trace-linked Opik evaluation."""
    print("Running trace-linked evaluation ...\n")
    summary = run_trace_linked_evaluation(
        experiment_name="elastic-agent-trace-linked",
        agent_mode="mock",
        task_threads=1,
    )
    print(f"\nDone. View results: {summary['experiment_url']}")
    print("See 05_trace_linking.md for the UI checklist.")


if __name__ == "__main__":
    main()
