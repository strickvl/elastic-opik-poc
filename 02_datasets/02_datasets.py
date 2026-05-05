"""
Step 02 — Dataset Creation and Versioning

Opik datasets are the ground-truth store for evaluation. Every insert, update,
or delete creates an immutable new version, and each experiment run is pinned to
the dataset version that was active when it ran — so results are always
reproducible even as the dataset evolves.

This script:
  1. Creates the golden Q&A dataset (or retrieves it if it already exists)
  2. Inserts 5 seed items covering core Elasticsearch / Kibana topics
  3. Updates one item's expected output (simulates a ground-truth correction)
  4. Inserts a 6th item (simulates adding a new test case)

Each mutation pauses so you can verify the new version appears in the UI before
continuing. A deletion example is included but commented out.

Docs: https://www.comet.com/docs/opik/evaluation/manage_datasets/

Usage:
    python 02_datasets/02_datasets.py
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import opik

DATASET_NAME = os.environ["DATASET_NAME"]
PROJECT_NAME = os.environ["OPIK_PROJECT_NAME"]

client = opik.Opik()

dataset = client.get_or_create_dataset(
    name=DATASET_NAME,
    description="Golden Q&A pairs for evaluating the Elastic AI Search / Kibana agent",
    project_name=PROJECT_NAME,
)
print(f"Dataset ready: {dataset.name!r}\n")

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SEED_ITEMS = [
    {
        "input": "How do I create a new index in Elasticsearch?",
        "expected_output": (
            "Use the PUT /<index-name> API to create a new index. "
            "Specify settings such as number_of_shards and number_of_replicas in the request body."
        ),
        "relevant_doc_ids": ["doc-001", "doc-003"],
    },
    {
        "input": "What is ELSER and how does it enable semantic search?",
        "expected_output": (
            "ELSER is a sparse embedding model trained by Elastic. It converts text into "
            "sparse token-weight vectors that enable semantic search without a separate embedding service."
        ),
        "relevant_doc_ids": ["doc-004", "doc-006"],
    },
    {
        "input": "How do I use KQL to filter documents in Kibana Discover?",
        "expected_output": (
            "In Kibana Discover, type a KQL expression in the search bar. "
            "KQL supports field:value, wildcards, ranges, and boolean operators."
        ),
        "relevant_doc_ids": ["doc-002", "doc-005"],
    },
    {
        "input": "What index lifecycle management phases are available in ILM?",
        "expected_output": (
            "ILM supports hot, warm, cold, and delete phases. Each phase can trigger "
            "actions like rollover, shrink, force merge, and searchable snapshot."
        ),
        "relevant_doc_ids": ["doc-003", "doc-007"],
    },
    {
        "input": "How do I configure the Kibana AI Search connector?",
        "expected_output": (
            "In Kibana, go to Search > AI Search and create a new connector. "
            "Select your index, choose an embedding model, and configure the inference endpoint."
        ),
        "relevant_doc_ids": ["doc-001", "doc-008"],
    },
]

dataset.insert(SEED_ITEMS)
print(f"Inserted {len(SEED_ITEMS)} seed items.")
input(">>> UI: Datasets > elastic-agent-qa-v1 — confirm 5 items and version 1. Press Enter to continue.\n")

# ---------------------------------------------------------------------------
# Mutation 1: update
# ---------------------------------------------------------------------------

items = list(dataset.get_items())
first = items[0]
dataset.update([{
    "id": first["id"],
    "input": first["input"],
    "expected_output": first["expected_output"] + " You can also specify mappings in the same request.",
    "relevant_doc_ids": first["relevant_doc_ids"],
}])
print("Mutation 1 complete: updated expected_output for the first item.")
input(">>> UI: confirm a new version appears in the version history. Press Enter to continue.\n")

# ---------------------------------------------------------------------------
# Mutation 2: insert
# ---------------------------------------------------------------------------

dataset.insert([{
    "input": "How do I use the Elasticsearch knn query for vector search?",
    "expected_output": (
        "Use the knn top-level parameter in your search request. Specify the field, "
        "query_vector, k, and num_candidates."
    ),
    "relevant_doc_ids": ["doc-004", "doc-010"],
}])
print("Mutation 2 complete: inserted one new item (6 items total).")


# ---------------------------------------------------------------------------
# Mutation 3: Delete
# ---------------------------------------------------------------------------

# Deletion example (commented out — uncomment to see delete versioning):
# items = list(dataset.get_items())
# to_delete = next((i for i in items if "knn query" in i.get("input", "")), None)
# if to_delete:
#     dataset.delete(items_ids=[to_delete["id"]])

# ---------------------------------------------------------------------------
# Pass criteria
# ---------------------------------------------------------------------------

print("Done. See 02_datasets.md for the UI checklist.")
