"""Main entry point for the data pipeline application."""

import argparse
import logging
import sys
import time
import tomllib
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from transit_delay_analytics import ingestion
from transit_delay_analytics.cli import parse_args
from transit_delay_analytics.core.config import (
    SourceConfig,
    is_now_within_window,
    load_pipeline_config,
)
from transit_delay_analytics.core.logger import setup_logging
from transit_delay_analytics.models.standardized.base import BaseTransformer

logger = logging.getLogger(__name__)


def run_pipeline(
    sources_dict: dict[str, SourceConfig], source_name: str | None
) -> bool:
    """Executes the ingestion process for specified sources.

    Args:
        sources_dict (dict[str, SourceConfig]): The loaded pipeline sources
            configuration.
        source_name (str | None): The specific source to run, or None to run all.

    Returns:
        bool: True if all sources were successfully ingested, False otherwise.
    """
    sources_to_run = (
        [sources_dict[source_name]] if source_name else list(sources_dict.values())
    )

    source_names = [source.name for source in sources_to_run]
    sources_str = ", ".join(source_names)

    logger.info("Pipeline started", extra={"source": sources_str})

    overall_success = True

    for source in sources_to_run:
        try:
            ingestor = ingestion.BaseIngestor.get_ingestor(source)
            ingestor.run()
        except (OSError, RuntimeError, ValueError):
            logger.exception("Ingestion failed", extra={"source": source.name})
            overall_success = False

    logger.info(
        "Pipeline finished", extra={"source": sources_str, "success": overall_success}
    )
    return overall_success


def run_daemon(sources_dict: dict[str, SourceConfig], source_name: str | None) -> None:
    """Runs continuously, triggering ingestors based on their schedule."""
    sources_to_run = (
        [sources_dict[source_name]] if source_name else list(sources_dict.values())
    )

    # Remember when each source was last launched
    last_run: dict[str, datetime | None] = {s.name: None for s in sources_to_run}

    logger.info("Daemon started. Press Ctrl+C to stop.")

    try:
        while True:
            now = datetime.now(UTC)

            for source in sources_to_run:
                # 1. Check if we are within the allowed time window (if defined)
                if source.window_start and source.window_end:
                    if not is_now_within_window(source, now_utc=now):
                        continue

                # 2. Check the interval
                last_run_time = last_run[source.name]
                if last_run_time is not None:
                    elapsed_seconds = (now - last_run_time).total_seconds()
                    if elapsed_seconds < source.interval_seconds:
                        continue

                # 3. It's time! Fetch the data.
                logger.info("Scheduled trigger", extra={"source": source.name})
                try:
                    ingestor = ingestion.BaseIngestor.get_ingestor(source)
                    ingestor.run()
                except Exception:
                    # The error is already logged, let the daemon continue running
                    pass
                finally:
                    # Update the last run time regardless of success/failure,
                    # to avoid creating an endless error loop that would spam the logs.
                    last_run[source.name] = datetime.now(UTC)

            # Sleep for a second and repeat the loop
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("Daemon stopped by user.")


def run_transform(
    model_names: list[str],
    dates: list[date] | None,
    overwrite: bool,
) -> bool:
    """Executes the standardized transformation for given models and dates.

    Args:
        model_names: Transformer model names to run.
        dates: Explicit list of dates to process. If None, each transformer
               discovers its own available dates from raw data.
        overwrite: If True, overwrite existing partitions.

    Returns:
        bool: True if all transformations succeeded, False otherwise.
    """
    models_str = ", ".join(model_names)
    logger.info("Transform started", extra={"models": models_str})

    overall_success = True

    for model_name in model_names:
        transformer = BaseTransformer.get_transformer(model_name)
        run_dates = dates if dates is not None else transformer.discover_dates()

        if not run_dates:
            logger.warning("No dates to process", extra={"model": model_name})
            continue

        for target_date in run_dates:
            try:
                transformer.run(target_date, overwrite=overwrite)
            except Exception:
                logger.exception(
                    "Transform failed",
                    extra={"model": model_name, "date": str(target_date)},
                )
                overall_success = False

    logger.info(
        "Transform finished",
        extra={"models": models_str, "success": overall_success},
    )
    return overall_success


def main() -> int:
    """Executes the main application flow.

    Returns:
        int: 0 for successful execution, non-zero exit code for failure.
    """
    # Pre-parse to allow overriding config and log config paths
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", dest="config", default=None)
    pre_parser.add_argument("--log-config", dest="log_config", default=None)
    pre_args, _ = pre_parser.parse_known_args()

    # Resolve config paths (fall back to defaults inside loader/setup)
    pipeline_config_path = Path(pre_args.config) if pre_args.config else None
    log_config_path = Path(pre_args.log_config) if pre_args.log_config else None

    # Initialize logging (uses default if log_config_path is None)
    setup_logging(config_path=log_config_path) if log_config_path else setup_logging()

    try:
        sources_config = (
            load_pipeline_config(pipeline_config_path)
            if pipeline_config_path
            else load_pipeline_config()
        )
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        logger.critical("Pipeline config error")
        return 1

    valid_sources = list(sources_config.keys())
    # standardized import above registers all transformers in BaseTransformer._registry
    # TODO: Peaks kontrollima neid vastavalt argumendile, ingest puhul etc seda vaja pole, ehk kontroll on vales kohas.
    valid_models = list(BaseTransformer._registry.keys())

    args = parse_args(valid_sources=valid_sources, valid_models=valid_models)

    if args.command == "ingest":
        success = run_pipeline(sources_config, args.source)
        return 0 if success else 1

    elif args.command == "daemon":
        run_daemon(sources_config, args.source)
        return 0

    elif args.command == "transform":
        # Resolve date range from CLI flags
        if args.all_dates:
            dates = None  # each transformer discovers its own dates
        elif args.date_from is not None:
            if args.date_to is None:
                logger.critical("--date-from requires --date-to")
                return 1
            delta = (args.date_to - args.date_from).days
            if delta < 0:
                logger.critical("--date-to must be >= --date-from")
                return 1
            dates = [args.date_from + timedelta(days=i) for i in range(delta + 1)]
        elif args.date is not None:
            dates = [args.date]
        else:
            dates = [date.today()]

        model_names = (
            [args.model] if args.model else list(BaseTransformer._registry.keys())
        )
        success = run_transform(
            model_names=model_names,
            dates=dates,
            overwrite=args.overwrite,
        )
        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
