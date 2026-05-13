"""CLI runner for the Elastic Opik ZenML pipeline.

Examples:
    uv run python run_zenml_pipeline.py --dataset-source mock --agent-mode mock
    uv run python run_zenml_pipeline.py --dataset-source gcs --agent-mode real
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from zenml_orchestration.evaluation import DEFAULT_EXPERIMENT_NAME, DEFAULT_JUDGE_MODEL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the two-step ZenML orchestration for the Elastic Opik PoC."
    )
    parser.add_argument(
        "--dataset-source",
        choices=["mock", "gcs"],
        default="mock",
        help="Dataset source to register in Opik before evaluation.",
    )
    parser.add_argument(
        "--agent-mode",
        choices=["mock", "real"],
        default="mock",
        help="Agent implementation to call during Opik evaluation.",
    )
    parser.add_argument(
        "--experiment-name",
        default=DEFAULT_EXPERIMENT_NAME,
        help="Opik experiment name for the evaluation step.",
    )
    parser.add_argument(
        "--task-threads",
        type=int,
        default=1,
        help="Number of Opik evaluation task threads. Defaults to 1 for trace validation.",
    )
    parser.add_argument(
        "--judge-model",
        default=DEFAULT_JUDGE_MODEL,
        help="LLM judge model passed to Opik built-in and custom metrics.",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update changed Opik dataset rows instead of skipping them.",
    )
    parser.add_argument(
        "--config",
        help="Optional ZenML YAML config path, applied with pipeline.with_options(config_path=...).",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()

    from zenml_orchestration.pipeline import elastic_opik_zenml_pipeline

    pipe = elastic_opik_zenml_pipeline
    if args.config:
        pipe = pipe.with_options(config_path=args.config)

    pipe(
        dataset_source=args.dataset_source,
        agent_mode=args.agent_mode,
        experiment_name=args.experiment_name,
        task_threads=args.task_threads,
        judge_model=args.judge_model,
        update_existing=args.update_existing,
    )

    print(
        ">> ZenML pipeline submitted/completed. Check the ZenML dashboard for "
        "the dataset summary, evaluation summary, and Opik experiment URL artifact."
    )


if __name__ == "__main__":
    main()
