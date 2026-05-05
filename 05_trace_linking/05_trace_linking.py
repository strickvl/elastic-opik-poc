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
sys.path.insert(0, str(Path(__file__).parent.parent))           # root
sys.path.insert(0, str(Path(__file__).parent.parent / "03_metrics"))  # metrics

import opik
from opik.evaluation.metrics import AnswerRelevance, ContextPrecision, Hallucination
from opentelemetry.propagate import inject

from kibana_agent import DATASET_NAME, K, PROJECT_NAME, call_kibana_agent
from metrics import F1AtK, PrecisionAtK, RecallAtK, SequenceFidelity

client = opik.Opik()
dataset = client.get_dataset(name=DATASET_NAME)


def trace_linked_task(dataset_item: dict) -> dict:
    """Task function that propagates OTel trace context into the Kibana API call."""
    headers: dict = {}
    inject(headers)  # writes traceparent header from the active Opik-created span

    # IMPORTANT: your real call_kibana_agent() must forward these headers in
    # the outbound HTTP request, otherwise the Kibana trace starts a new unrelated
    # span and linking will not work.
    response = call_kibana_agent(dataset_item["input"], headers=headers)

    return {
        "output": response.text,
        "context": [str(d) for d in response.retrieved_documents],
        "retrieved_ids": response.retrieved_documents,
        "relevant_ids": dataset_item.get("relevant_doc_ids", []),
    }


print("Running trace-linked evaluation ...\n")

results = opik.evaluate(
    dataset=dataset,
    task=trace_linked_task,
    scoring_metrics=[
        Hallucination(name="factuality"),
        ContextPrecision(name="groundedness"),
        AnswerRelevance(name="relevance"),
        SequenceFidelity(),
        PrecisionAtK(k=K),
        RecallAtK(k=K),
        F1AtK(k=K),
    ],
    experiment_name="elastic-agent-trace-linked",
    project_name=PROJECT_NAME,
    task_threads=1,  # keep at 1 while validating — easier to match items to traces
)

print(f"\nDone. View results: {results.experiment_url}")
print("See 05_trace_linking.md for the UI checklist.")
