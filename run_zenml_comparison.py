"""CLI runner for static comparison of completed Opik evaluation runs.

Examples:
    python run_zenml_comparison.py --run run_a --run run_b
    python run_zenml_comparison.py --result-json a.json --result-json b.json --output-html reports/comparison.html
"""

from __future__ import annotations

import argparse
from typing import List, Optional

from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a ZenML artifact that compares completed Opik evaluation results."
    )
    parser.add_argument(
        "--run",
        action="append",
        dest="runs",
        default=[],
        help="ZenML pipeline run name or ID containing an opik_evaluation_results artifact. Repeat for each run to compare. The first run is the baseline.",
    )
    parser.add_argument(
        "--result-json",
        action="append",
        dest="result_json_paths",
        default=[],
        help="Downloaded opik_evaluation_results data.json file. Repeat for each file to compare. Useful if you do not want to load from ZenML by run name.",
    )
    parser.add_argument(
        "--label",
        action="append",
        dest="labels",
        default=None,
        help="Optional display label. Repeat in the same order as --run / --result-json.",
    )
    parser.add_argument(
        "--output-html",
        default=None,
        help="Optional local path for a copy of the comparison HTML report. The ZenML artifact is always created.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    _validate_args(args.runs, args.result_json_paths, args.labels)

    from zenml_orchestration.pipelines.opik_comparison import (
        opik_evaluation_comparison_pipeline,
    )

    opik_evaluation_comparison_pipeline(
        run_names_or_ids=args.runs or None,
        result_json_paths=args.result_json_paths or None,
        labels=args.labels,
        output_html_path=args.output_html,
    )
    print(
        ">> ZenML comparison pipeline submitted/completed. Check the "
        "opik_evaluation_comparison artifact for the HTML report."
    )


def _validate_args(
    runs: List[str],
    result_json_paths: List[str],
    labels: Optional[List[str]],
) -> None:
    source_count = len(runs) + len(result_json_paths)
    if source_count < 2:
        raise SystemExit("Provide at least two --run / --result-json values to compare.")
    if labels and len(labels) != source_count:
        raise SystemExit(
            f"Received {len(labels)} labels for {source_count} comparison sources. "
            "Either omit --label or provide exactly one per source."
        )


if __name__ == "__main__":
    main()
