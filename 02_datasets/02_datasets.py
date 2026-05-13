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

from zenml_orchestration.dataset_registration import (
    DATASET_DESCRIPTION,
    MOCK_ADDITIONAL_ITEM,
    MOCK_BASE_ITEMS,
    UPDATED_FIRST_EXPECTED_SUFFIX,
)


def main() -> None:
    """Run the original interactive dataset-versioning playbook."""
    load_dotenv()

    import opik

    dataset_name = os.environ["DATASET_NAME"]
    project_name = os.environ["OPIK_PROJECT_NAME"]

    client = opik.Opik()
    dataset = client.get_or_create_dataset(
        name=dataset_name,
        description=DATASET_DESCRIPTION,
        project_name=project_name,
    )
    print(f"Dataset ready: {dataset.name!r}\n")

    # ---------------------------------------------------------------------------
    # Seed data
    # ---------------------------------------------------------------------------

    dataset.insert(MOCK_BASE_ITEMS)
    print(f"Inserted {len(MOCK_BASE_ITEMS)} seed items.")
    input(
        ">>> UI: Datasets > elastic-agent-qa-v1 — confirm 5 items and version 1. "
        "Press Enter to continue.\n"
    )

    # ---------------------------------------------------------------------------
    # Mutation 1: update
    # ---------------------------------------------------------------------------

    items = list(dataset.get_items())
    first = items[0]
    dataset.update([
        {
            "id": first["id"],
            "input": first["input"],
            "expected_output": first["expected_output"] + UPDATED_FIRST_EXPECTED_SUFFIX,
            "relevant_doc_ids": first["relevant_doc_ids"],
        }
    ])
    print("Mutation 1 complete: updated expected_output for the first item.")
    input(
        ">>> UI: confirm a new version appears in the version history. "
        "Press Enter to continue.\n"
    )

    # ---------------------------------------------------------------------------
    # Mutation 2: insert
    # ---------------------------------------------------------------------------

    dataset.insert([MOCK_ADDITIONAL_ITEM])
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


if __name__ == "__main__":
    main()
