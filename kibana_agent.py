"""
Mock Kibana agent with OpenTelemetry instrumentation.

This module is the "app" called by all evaluation scripts. It simulates the
Kibana conversation API and instruments every call with OTel spans that flow
to Opik automatically — no Opik SDK in the app code.

Replace the mock implementation with your real Kibana API call when ready.
The return type must expose:
    response.text                   str
    response.retrieved_documents    List[str]  — document IDs from the retriever

Token counts, cost, and latency are emitted as OTel span attributes and
surfaced in Opik automatically once trace linking is active (05_trace_linking.py).

Docs: https://www.comet.com/docs/opik/tracing/integrations/opentelemetry/
"""

import os
import random
import time
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import extract
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.trace import Status, StatusCode

PROJECT_NAME = os.environ["OPIK_PROJECT_NAME"]
DATASET_NAME = os.environ["DATASET_NAME"]
K = int(os.environ.get("RETRIEVAL_K", "3"))


# ---------------------------------------------------------------------------
# OTel setup — runs once on import
# ---------------------------------------------------------------------------

def _setup_otel(service: str = "elastic-kibana-agent") -> trace.Tracer:
    api_key = os.environ["OPIK_API_KEY"]
    workspace = os.environ.get("OPIK_WORKSPACE", "default")

    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://www.comet.com/opik/api/v1/private/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = (
        f"Authorization={api_key},"
        f"projectName={PROJECT_NAME},"
        f"Comet-Workspace={workspace}"
    )

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service}))
    provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
    # Do NOT call trace.set_tracer_provider() — that would override the global
    # provider that Opik uses, breaking inject() in the trace-linking step.
    # We get our tracer directly from this local provider instead.
    return provider.get_tracer(__name__)


tracer = _setup_otel()


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

_DOCS = {
    "doc-001": "ELSER is a sparse embedding model trained by Elastic for semantic search.",
    "doc-002": "The knn query in Elasticsearch finds approximate nearest neighbours.",
    "doc-003": "ILM manages index lifecycle across hot, warm, cold, and delete phases.",
    "doc-004": "In Kibana Discover, type a KQL expression in the search bar.",
    "doc-005": "Use the PUT /<index-name> API to create a new index with settings.",
    "doc-006": "ELSER converts text into sparse token-weight vectors without a separate embedding service.",
    "doc-007": "ILM supports hot, warm, cold, and delete phases with actions like rollover and shrink.",
    "doc-008": "In Kibana, go to Search > AI Search and create a new connector.",
}

_QUERY_RESULTS = [
    (["doc-001", "doc-003"], "doc-006"),
    (["doc-004", "doc-002"], "doc-001"),
    (["doc-002", "doc-005"], "doc-006"),
    (["doc-003", "doc-007"], "doc-004"),
    (["doc-001", "doc-008"], "doc-005"),
]

SAMPLE_QUERIES = [
    "What is ELSER and how does it enable semantic search?",
    "How do I configure ILM phases in Elasticsearch?",
    "What is the knn query and when should I use it?",
]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class _AgentResponse:
    def __init__(self, text: str, retrieved_documents: List[str]):
        self.text = text
        self.retrieved_documents = retrieved_documents


def call_kibana_agent(
    input_text: str,
    headers: Optional[Dict[str, str]] = None,
) -> _AgentResponse:
    """
    Call the Kibana conversation API.

    The optional `headers` dict is used by 05_trace_linking.py to propagate
    the W3C traceparent so agent spans appear as children of the eval span.

    Real implementation example:
        import httpx
        r = httpx.post(
            "https://<kibana-host>/api/chat/conversation",
            json={"message": input_text},
            headers={**(headers or {})},
        )
        body = r.json()
        return _AgentResponse(
            text=body["message"],
            retrieved_documents=body["references"],
        )
    """
    ctx = extract(headers or {})

    with tracer.start_as_current_span("kibana.agent", context=ctx) as root:
        root.set_attribute("input", input_text)
        root.set_attribute("opik.tags", "elastic,kibana,demo")
        root.set_attribute("opik.metadata.agent_version", "8.14.0")

        try:
            retrieved_ids, answer_doc_id = random.choice(_QUERY_RESULTS)

            with tracer.start_as_current_span("elasticsearch.search") as search:
                search.set_attribute("db.system", "elasticsearch")
                search.set_attribute("db.operation", "search")
                search.set_attribute("elasticsearch.query", input_text)
                time.sleep(random.uniform(0.03, 0.08))
                search.set_attribute("elasticsearch.hits", len(retrieved_ids))
                search.set_status(Status(StatusCode.OK))

            context_text = "\n".join(_DOCS[d] for d in retrieved_ids if d in _DOCS)
            prompt = f"Context:\n{context_text}\n\nQuestion: {input_text}"
            answer = f"Based on the retrieved documents: {_DOCS.get(answer_doc_id, '')}"

            with tracer.start_as_current_span("llm.chat") as llm:
                llm.set_attribute("gen_ai.system", "openai")
                llm.set_attribute("gen_ai.request.model", "gpt-4o")
                llm.set_attribute("gen_ai.response.model", "gpt-4o")
                llm.set_attribute("gen_ai.request.input", prompt[:500])
                time.sleep(random.uniform(0.1, 0.3))
                in_tok = len(prompt.split())
                out_tok = len(answer.split())
                llm.set_attribute("gen_ai.response.output", answer)
                llm.set_attribute("gen_ai.usage.input_tokens", in_tok)
                llm.set_attribute("gen_ai.usage.output_tokens", out_tok)
                llm.set_status(Status(StatusCode.OK))

            root.set_attribute("output", answer)
            root.set_attribute("gen_ai.usage.input_tokens", in_tok)
            root.set_attribute("gen_ai.usage.output_tokens", out_tok)
            root.set_status(Status(StatusCode.OK))

            return _AgentResponse(text=answer, retrieved_documents=retrieved_ids)

        except Exception as exc:
            root.set_status(Status(StatusCode.ERROR, str(exc)))
            root.record_exception(exc)
            raise


def task_fn(dataset_item: Dict) -> Dict:
    """
    Task function for opik.evaluate(). Calls the Kibana agent and returns scored outputs.

    Token counts, cost, and latency are omitted here — once the real Kibana agent
    is wired up with OTel trace linking (05_trace_linking.py), Opik surfaces those
    automatically from the linked trace spans.
    """
    response = call_kibana_agent(dataset_item["input"])
    return {
        "output": response.text,
        "context": [_DOCS.get(d, d) for d in response.retrieved_documents],
        "retrieved_ids": response.retrieved_documents,
        "relevant_ids": dataset_item.get("relevant_doc_ids", []),
    }

def _extract_doc_ids(steps: List[Any]) -> List[str]:
    """Pull Elasticsearch document _id values out of agent step results."""
    ids: List[str] = []
    for step in steps:
        if step.get("type") != "tool_call":
            continue
        for result in step.get("results") or []:
            ref = result.get("data", {}).get("reference", {})
            doc_id = ref.get("id")
            if doc_id:
                ids.append(doc_id)
    return ids


def call_real_kibana_agent(
    input_text: str,
    headers: Optional[Dict[str, str]] = None,
) -> _AgentResponse:
    """
    Call the Kibana Agent Builder converse endpoint.

    Required env vars:
        KIBANA_URL        e.g. https://my-kibana.example.com
        KIBANA_API_KEY    Elastic API key  (preferred)
          — or —
        KIBANA_USERNAME / KIBANA_PASSWORD  for basic auth

    Optional env vars:
        KIBANA_AGENT_ID   defaults to "elastic-ai-agent"
        KIBANA_SPACE      Kibana space name (omit for the default space)
    """
    kibana_url = os.environ["KIBANA_URL"].rstrip("/")
    agent_id = os.environ.get("KIBANA_AGENT_ID", "elastic-ai-agent")
    space = os.environ.get("KIBANA_SPACE", "")

    path_prefix = f"/s/{space}" if space else ""
    endpoint = f"{kibana_url}{path_prefix}/api/agent_builder/converse"

    import base64

    api_key = os.environ.get("KIBANA_API_KEY")
    api_key_id = os.environ.get("KIBANA_API_KEY_ID")
    if api_key and api_key_id:
        # id + api_key provided separately — encode as base64(id:api_key)
        encoded = base64.b64encode(f"{api_key_id}:{api_key}".encode()).decode()
        auth_header = f"ApiKey {encoded}"
    elif api_key:
        # assume KIBANA_API_KEY is already the base64-encoded id:api_key value
        auth_header = f"ApiKey {api_key}"
    else:
        username = os.environ["KIBANA_USERNAME"]
        password = os.environ["KIBANA_PASSWORD"]
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        auth_header = f"Basic {token}"

    request_headers = {
        "Authorization": auth_header,
        "kbn-xsrf": "true",
        "Content-Type": "application/json",
        **(headers or {}),
    }

    ctx = extract(headers or {})

    with tracer.start_as_current_span("kibana.agent", context=ctx) as root:
        root.set_attribute("input", input_text)
        root.set_attribute("opik.tags", "elastic,kibana,real")
        root.set_attribute("opik.metadata.agent_id", agent_id)

        try:
            with tracer.start_as_current_span("kibana.converse") as span:
                span.set_attribute("http.method", "POST")
                span.set_attribute("http.url", endpoint)

                resp = httpx.post(
                    endpoint,
                    json={"input": input_text, "agent_id": agent_id},
                    headers=request_headers,
                    timeout=300.0,
                )
                resp.raise_for_status()

                span.set_attribute("http.status_code", resp.status_code)
                span.set_status(Status(StatusCode.OK))

            body = resp.json()
            answer = body.get("response", {}).get("message", "")
            steps = body.get("steps", [])
            retrieved_ids = _extract_doc_ids(steps)

            root.set_attribute("output", answer)
            root.set_attribute("opik.metadata.elasticsearch.retrieved_docs", len(retrieved_ids))
            root.set_status(Status(StatusCode.OK))

            return _AgentResponse(text=answer, retrieved_documents=retrieved_ids)

        except Exception as exc:
            root.set_status(Status(StatusCode.ERROR, str(exc)))
            root.record_exception(exc)
            raise