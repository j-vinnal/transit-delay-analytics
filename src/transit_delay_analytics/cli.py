"""Command-line interface for the data pipeline."""

import argparse
from datetime import date


def parse_args(
        valid_sources: list[str],
        valid_models: list[str],
) -> argparse.Namespace:
    """Parse command-line arguments with subparsers.

    Args:
        valid_sources: Source names from pipeline.toml for validation.
        valid_models: Transformer names from BaseTransformer registry for validation.

    Returns:
        argparse.Namespace: Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="tra",
        description="Modular data pipeline framework.",
    )

    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
    )

    # ── ingest ─────────────────────────────────────────────────────────────
    ingest_parser = subparsers.add_parser("ingest", help="Run data ingestion (one-off)")
    ingest_parser.add_argument(
        "--source",
        type=str,
        default=None,
        choices=valid_sources,
        help="Specific source to run. If omitted, runs all sources.",
    )

    # ── daemon ─────────────────────────────────────────────────────────────
    daemon_parser = subparsers.add_parser(
        "daemon", help="Run data ingestion continuously on a schedule"
    )
    daemon_parser.add_argument(
        "--source",
        type=str,
        default=None,
        choices=valid_sources,
        help="Specific source to schedule. If omitted, schedules all sources.",
    )

    # ── transform ──────────────────────────────────────────────────────────
    transform_parser = subparsers.add_parser(
        "transform",
        help="Standardize raw data into typed Parquet partitions",
    )
    transform_parser.add_argument(
        "--model",
        type=str,
        default=None,
        choices=valid_models,
        metavar="MODEL",
        help=(
            f"Specific model to run. If omitted, runs all models. "
            f"Available: {', '.join(valid_models)}"
        ),
    )
    transform_parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing output partitions (default: skip).",
    )

    # Date selection (mutually exclusive)
    date_group = transform_parser.add_mutually_exclusive_group()
    date_group.add_argument(
        "--date",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="Process a single date (default: today).",
    )
    date_group.add_argument(
        "--all-dates",
        action="store_true",
        default=False,
        help="Process all dates available in raw data.",
    )
    date_group.add_argument(
        "--date-from",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="Start of date range (inclusive). Must be paired with --date-to.",
    )

    transform_parser.add_argument(
        "--date-to",
        type=date.fromisoformat,
        metavar="YYYY-MM-DD",
        help="End of date range (inclusive). Required when --date-from is used.",
    )

    return parser.parse_args()
