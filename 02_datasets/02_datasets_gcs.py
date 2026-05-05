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

import ast
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from dotenv import load_dotenv
load_dotenv()

import opik

DATASET_NAME = os.environ["DATASET_NAME"]
PROJECT_NAME = os.environ["OPIK_PROJECT_NAME"]

GCS_BUCKET = os.environ["GCS_BUCKET"]
GCS_OBJECT = os.environ["GCS_OBJECT"]

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

df = pd.read_csv(f"gs://{GCS_BUCKET}/{GCS_OBJECT}")

df["relevant_doc_ids"] = df["gt_elastic_knowledge_base"].apply(
    lambda x: list(ast.literal_eval(x).keys()) if pd.notna(x) else []
)

dataset.insert_from_pandas(
    df,
    keys_mapping={"input_question": "input", "output_expected": "expected_output"},
    ignore_keys=["gt_elastic_knowledge_base"]
)
print(f"Inserted {len(df)} seed items.")
input(">>> UI: Datasets > elastic-agent-qa-v1 — confirm 5 items and version 1. Press Enter to continue.\n")

# ---------------------------------------------------------------------------
# Mutation 1: update
# ---------------------------------------------------------------------------

# items = list(dataset.get_items())
# first = items[0]
# dataset.update([{
#     "id": first["id"],
#     "input": first["input"],
#     "expected_output": first["expected_output"] + " You can also specify mappings in the same request.",
#     "relevant_doc_ids": first["relevant_doc_ids"],
# }])
# print("Mutation 1 complete: updated expected_output for the first item.")
# input(">>> UI: confirm a new version appears in the version history. Press Enter to continue.\n")

# ---------------------------------------------------------------------------
# Mutation 2: insert
# ---------------------------------------------------------------------------

# dataset.insert([{
#     "input": "How do I use the Elasticsearch knn query for vector search?",
#     "expected_output": (
#         "Use the knn top-level parameter in your search request. Specify the field, "
#         "query_vector, k, and num_candidates."
#     ),
#     "relevant_doc_ids": ["doc-004", "doc-010"],
# }])
# print("Mutation 2 complete: inserted one new item (6 items total).")


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
