"""CLI runner for the Elastic Opik ZenML pipeline.

Examples:
    python run_zenml_pipeline.py --config configs/zenml_mock_smoke.yaml
    python run_zenml_pipeline.py --config configs/zenml_real.yaml
    python run_zenml_pipeline.py --dataset-source mock --agent-mode mock
"""

from __future__ import annotations

import argparse
from typing import Any, Dict

from dotenv import load_dotenv

from zenml_orchestration.evaluation import DEFAULT_EXPERIMENT_NAME, DEFAULT_JUDGE_MODEL

_DEFAULT_PIPELINE_ARGS: Dict[str, Any] = {
    "dataset_source": "mock",
    "agent_mode": "mock",
    "experiment_name": DEFAULT_EXPERIMENT_NAME,
    "task_threads": 1,
    "judge_model": DEFAULT_JUDGE_MODEL,
    "update_existing": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the two-step ZenML orchestration for the Elastic Opik PoC."
    )
    parser.add_argument(
        "--dataset-source",
        choices=["mock", "gcs"],
        default=None,
        help="Dataset source to register in Opik before evaluation. Default without --config: mock.",
    )
    parser.add_argument(
        "--agent-mode",
        choices=["mock", "real"],
        default=None,
        help="Agent implementation to call during Opik evaluation. Default without --config: mock.",
    )
    parser.add_argument(
        "--experiment-name",
        default=None,
        help=f"Opik experiment name. Default without --config: {DEFAULT_EXPERIMENT_NAME}.",
    )
    parser.add_argument(
        "--task-threads",
        type=int,
        default=None,
        help="Number of Opik evaluation task threads. Default without --config: 1.",
    )
    parser.add_argument(
        "--judge-model",
        default=None,
        help=f"LLM judge model passed to Opik metrics. Default without --config: {DEFAULT_JUDGE_MODEL}.",
    )
    parser.add_argument(
        "--update-existing",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Update changed Opik dataset rows instead of skipping them. Default without --config: false.",
    )
    parser.add_argument(
        "--config",
        help="Optional ZenML YAML config path, applied with pipeline.with_options(config_path=...).",
    )
    return parser.parse_args()


def pipeline_kwargs(args: argparse.Namespace) -> Dict[str, Any]:
    """Build pipeline kwargs without accidentally overriding YAML config values."""
    explicit_args = {
        "dataset_source": args.dataset_source,
        "agent_mode": args.agent_mode,
        "experiment_name": args.experiment_name,
        "task_threads": args.task_threads,
        "judge_model": args.judge_model,
        "update_existing": args.update_existing,
    }
    if args.config:
        return {key: value for key, value in explicit_args.items() if value is not None}

    return {
        key: _DEFAULT_PIPELINE_ARGS[key] if value is None else value
        for key, value in explicit_args.items()
    }


def main() -> None:
    load_dotenv()
    args = parse_args()

    from zenml_orchestration.pipelines.elastic_opik import elastic_opik_zenml_pipeline

    pipe = elastic_opik_zenml_pipeline
    if args.config:
        pipe = pipe.with_options(config_path=args.config)

    pipe(**pipeline_kwargs(args))

    print(
        ">> ZenML pipeline submitted/completed. Check the ZenML dashboard for "
        "the dataset summary, evaluation summary, and Opik experiment URL artifact."
    )


if __name__ == "__main__":
    main()
