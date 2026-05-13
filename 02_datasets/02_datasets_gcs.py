"""
Step 02 — Dataset Creation and Versioning from GCS

This is the GCS/CSV variant of the Step 02 playbook. It keeps the original
interactive behaviour when run directly, but it is now safe to import without
creating an Opik client, reading GCS, inserting rows, or blocking on input().

Docs: https://www.comet.com/docs/opik/evaluation/manage_datasets/

Usage:
    python 02_datasets/02_datasets_gcs.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from zenml_orchestration.dataset_registration import DATASET_DESCRIPTION, load_gcs_items


def main() -> None:
    """Run the original GCS-backed dataset insertion playbook."""
    load_dotenv()

    import pandas as pd
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

    items = load_gcs_items()
    df = pd.DataFrame(items)
    dataset.insert_from_pandas(df)
    print(f"Inserted {len(df)} seed items.")
    input(
        ">>> UI: Datasets > elastic-agent-qa-v1 — confirm items and version 1. "
        "Press Enter to continue.\n"
    )

    # ---------------------------------------------------------------------------
    # Mutation examples retained for playbook experimentation
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

    # dataset.insert([{
    #     "input": "How do I use the Elasticsearch knn query for vector search?",
    #     "expected_output": (
    #         "Use the knn top-level parameter in your search request. Specify the field, "
    #         "query_vector, k, and num_candidates."
    #     ),
    #     "relevant_doc_ids": ["doc-004", "doc-010"],
    # }])
    # print("Mutation 2 complete: inserted one new item (6 items total).")

    # Deletion example (commented out — uncomment to see delete versioning):
    # items = list(dataset.get_items())
    # to_delete = next((i for i in items if "knn query" in i.get("input", "")), None)
    # if to_delete:
    #     dataset.delete(items_ids=[to_delete["id"]])

    print("Done. See 02_datasets.md for the UI checklist.")


if __name__ == "__main__":
    main()
