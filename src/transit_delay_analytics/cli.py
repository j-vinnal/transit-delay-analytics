"""Command-line interface for the data pipeline."""

import argparse


def parse_args(valid_sources: list[str]) -> argparse.Namespace:
    """Parse command-line arguments with subparsers.

    Args:
        valid_sources (list[str]): List of source names from configuration for validation.

    Returns:
        argparse.Namespace: Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        prog="data-pipeline",
        description="Modular data pipeline framework.",
    )

    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser("ingest", help="Run data ingestion")
    run_parser.add_argument(
        "--source",
        type=str,
        default=None,
        choices=valid_sources,
        help="Specific source to run. If omitted, runs all sources.",
    )

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

    return parser.parse_args()
