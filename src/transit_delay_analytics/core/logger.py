"""Logging configuration and setup."""

import logging
import logging.config
import time
import tomllib
from pathlib import Path
from typing import Any, Literal

from transit_delay_analytics import PROJECT_ROOT
from transit_delay_analytics.constants import DEFAULT_LOG_CONFIG, LOGS_DIR


class ConditionalFormatter(logging.Formatter):
    """Custom formatter that appends dynamically specified extra fields to the log.

    It checks the LogRecord for specified extra fields and appends them to the
    formatted message if they exist.

    Attributes:
        extra_fields (List[str]): A list of attribute names to monitor in the LogRecord.
    """

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%", "{", "$"] = "%",
        extra_fields: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the ConditionalFormatter.

        Args:
            fmt (str | None): The format string for the log message.
            datefmt (str | None): The format string for the date/time.
            style (Literal["%", "{", "$"]): The formatting style. Defaults to "%".
            extra_fields (list[str] | None): A list of extra field names to append.
            **kwargs (Any): Additional keyword arguments passed to the base Formatter.
        """
        super().__init__(fmt=fmt, datefmt=datefmt, style=style, **kwargs)
        # Store the fields we want to monitor dynamically
        self.extra_fields = extra_fields or []

    def format(self, record: logging.LogRecord) -> str:
        """Format the specified record as text and append extra fields.

        Args:
            record (logging.LogRecord): The log record to be formatted.

        Returns:
            str: The fully formatted log message including dynamic extra fields.
        """
        # Capture the original exception info
        original_exc_info = record.exc_info
        original_exc_text = record.exc_text

        # Temporarily clear the exception info to prevent automatic
        # multi-line traceback printing
        record.exc_info = None
        record.exc_text = None

        # Format the base message using standard logic
        formatted_message = super().format(record)

        # Collect dynamic extra fields
        extra_parts: list[str] = []
        for field in self.extra_fields:
            if hasattr(record, field):
                value = getattr(record, field)
                if value is not None:  # Only add if the value is not None/empty
                    extra_parts.append(f"[{field}: {value}]")

        # Append error info in a single-line format
        if original_exc_info and original_exc_info[0] is not None:
            exc_type, exc_value, _ = original_exc_info
            extra_parts.append(f"[Exception: {exc_type.__name__} - {exc_value}]")

        if extra_parts:
            formatted_message += " | " + " | ".join(extra_parts)

        # Restore the original exception info to its initial state
        record.exc_info = original_exc_info
        record.exc_text = original_exc_text

        return formatted_message


def _resolve_log_file_paths(config: dict[str, Any], base_dir: Path) -> None:
    """Make all relative filename paths in logging handlers absolute.

    Args:
        config (dict[str, Any]): The parsed logging configuration dictionary.
        base_dir (Path): The base directory to resolve relative paths against.
    """
    for handler_cfg in config.get("handlers", {}).values():
        if "filename" in handler_cfg:
            filename = Path(handler_cfg["filename"])
            if not filename.is_absolute():
                handler_cfg["filename"] = str(base_dir / filename)


def setup_logging(
    config_path: Path = DEFAULT_LOG_CONFIG, log_dir: Path = LOGS_DIR
) -> None:
    """Load logging configuration from a TOML file and apply it.

    Args:
        config_path (Path): The path to the TOML configuration file. Defaults
            to the project's config/logging.toml.
        log_dir (Path): The directory where log files will be stored. Defaults
            to the project's logs/ directory.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
    """
    log_dir.mkdir(parents=True, exist_ok=True)

    # Ensure logging times are in UTC
    logging.Formatter.converter = time.gmtime

    if not config_path.exists():
        raise FileNotFoundError(f"Logging configuration file not found: {config_path}")

    with config_path.open("rb") as f:
        config = tomllib.load(f)

    _resolve_log_file_paths(config, PROJECT_ROOT)
    logging.config.dictConfig(config)

    # Handlers (including timed rotating file handler) are configured via dictConfig
    # If additional programmatic handlers are desired they can be added here.
