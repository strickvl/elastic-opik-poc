"""Import-safe dataset registration helpers for the ZenML pipeline.

This module intentionally does not create an Opik client at import time. Remote
Opik and GCS work only happens when ``register_opik_dataset`` is called.
"""

from __future__ import annotations

import ast
import os
from typing import Any, Dict, Iterable, List, Literal, Optional

from dotenv import load_dotenv

DatasetSource = Literal["mock", "gcs"]

DATASET_DESCRIPTION = (
    "Golden Q&A pairs for evaluating the Elastic AI Search / Kibana agent"
)
UPDATED_FIRST_EXPECTED_SUFFIX = " You can also specify mappings in the same request."

MOCK_BASE_ITEMS: List[Dict[str, Any]] = [
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

MOCK_ADDITIONAL_ITEM: Dict[str, Any] = {
    "input": "How do I use the Elasticsearch knn query for vector search?",
    "expected_output": (
        "Use the knn top-level parameter in your search request. Specify the field, "
        "query_vector, k, and num_candidates."
    ),
    "relevant_doc_ids": ["doc-004", "doc-010"],
}


def final_mock_items() -> List[Dict[str, Any]]:
    """Return the idempotent final state produced by the Step 02 demo."""
    items = [dict(item) for item in MOCK_BASE_ITEMS]
    items[0]["expected_output"] = items[0]["expected_output"] + UPDATED_FIRST_EXPECTED_SUFFIX
    items.append(dict(MOCK_ADDITIONAL_ITEM))
    return items


def load_gcs_items(
    *,
    gcs_bucket: Optional[str] = None,
    gcs_object: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load dataset rows from GCS using the existing Step 02 column mapping."""
    import pandas as pd

    bucket = gcs_bucket or os.environ["GCS_BUCKET"]
    object_name = gcs_object or os.environ["GCS_OBJECT"]
    df = pd.read_csv(f"gs://{bucket}/{object_name}")
    required_columns = {
        "input_question",
        "output_expected",
        "gt_elastic_knowledge_base",
    }
    missing_columns = sorted(required_columns - set(df.columns))
    if missing_columns:
        raise ValueError(
            "GCS dataset is missing required columns: "
            f"{missing_columns}"
        )

    items: List[Dict[str, Any]] = []
    for raw_row in df.to_dict(orient="records"):
        row = {
            key: _clean_pandas_value(value)
            for key, value in raw_row.items()
            if key != "gt_elastic_knowledge_base"
        }
        row["input"] = row.pop("input_question")
        row["expected_output"] = row.pop("output_expected")
        row["relevant_doc_ids"] = _parse_relevant_doc_ids(
            raw_row.get("gt_elastic_knowledge_base")
        )
        items.append(row)

    return items


def register_opik_dataset(
    *,
    source: DatasetSource = "mock",
    dataset_name: Optional[str] = None,
    project_name: Optional[str] = None,
    update_existing: bool = False,
    gcs_bucket: Optional[str] = None,
    gcs_object: Optional[str] = None,
) -> Dict[str, Any]:
    """Create/update an Opik dataset without duplicating unchanged rows.

    Rows are matched by their ``input`` field. Missing rows are inserted. Changed
    rows are updated only when ``update_existing`` is true. Extra rows already in
    Opik are left alone for this MVP.
    """
    load_dotenv()

    import opik

    resolved_dataset_name = dataset_name or os.environ["DATASET_NAME"]
    resolved_project_name = project_name or os.environ["OPIK_PROJECT_NAME"]
    desired_items = _load_desired_items(
        source=source,
        gcs_bucket=gcs_bucket,
        gcs_object=gcs_object,
    )
    desired_duplicates = _find_duplicate_inputs(desired_items)
    if desired_duplicates:
        raise ValueError(
            "Desired dataset rows must have unique 'input' values. "
            f"Duplicates: {desired_duplicates}"
        )

    client = opik.Opik()
    dataset = client.get_or_create_dataset(
        name=resolved_dataset_name,
        description=DATASET_DESCRIPTION,
        project_name=resolved_project_name,
    )

    existing_items = list(dataset.get_items())
    existing_duplicates = _find_duplicate_inputs(existing_items)
    if existing_duplicates:
        raise ValueError(
            "Existing Opik dataset rows have duplicate 'input' values, so "
            "idempotent registration is ambiguous. Duplicates: "
            f"{existing_duplicates}"
        )
    existing_by_input = {
        item.get("input"): item
        for item in existing_items
        if item.get("input") is not None
    }

    to_insert: List[Dict[str, Any]] = []
    to_update: List[Dict[str, Any]] = []
    unchanged = 0
    changed_not_updated = 0

    for desired in desired_items:
        existing = existing_by_input.get(desired["input"])
        if existing is None:
            to_insert.append(desired)
            continue

        if _items_match(existing, desired):
            unchanged += 1
            continue

        if update_existing:
            to_update.append({"id": existing["id"], **desired})
        else:
            changed_not_updated += 1

    if to_insert:
        dataset.insert(to_insert)
    if to_update:
        dataset.update(to_update)

    total_items_after = len(list(dataset.get_items()))
    return {
        "dataset_name": resolved_dataset_name,
        "project_name": resolved_project_name,
        "source": source,
        "inserted": len(to_insert),
        "updated": len(to_update),
        "skipped": unchanged + changed_not_updated,
        "unchanged": unchanged,
        "changed_not_updated": changed_not_updated,
        "total_items_after": total_items_after,
    }


def _load_desired_items(
    *,
    source: DatasetSource,
    gcs_bucket: Optional[str],
    gcs_object: Optional[str],
) -> List[Dict[str, Any]]:
    if source == "mock":
        return final_mock_items()
    if source == "gcs":
        return load_gcs_items(gcs_bucket=gcs_bucket, gcs_object=gcs_object)
    raise ValueError(f"Unsupported dataset source: {source!r}")


def _items_match(existing: Dict[str, Any], desired: Dict[str, Any]) -> bool:
    """Compare only the fields controlled by the desired dataset row."""
    return all(existing.get(key) == value for key, value in desired.items())


def _find_duplicate_inputs(items: List[Dict[str, Any]]) -> List[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        value = item.get("input")
        if value is None:
            continue
        input_value = str(value)
        if input_value in seen:
            duplicates.add(input_value)
        seen.add(input_value)
    return sorted(duplicates)


def _parse_relevant_doc_ids(value: Any) -> List[str]:
    if value is None or _is_nan(value):
        return []
    parsed = ast.literal_eval(value) if isinstance(value, str) else value
    if isinstance(parsed, dict):
        return [str(key) for key in parsed.keys()]
    if isinstance(parsed, Iterable) and not isinstance(parsed, (str, bytes)):
        return [str(item) for item in parsed]
    return []


def _clean_pandas_value(value: Any) -> Any:
    return None if _is_nan(value) else value


def _is_nan(value: Any) -> bool:
    try:
        return bool(value != value)
    except Exception:
        return False
