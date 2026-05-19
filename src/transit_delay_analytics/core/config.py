"""Pipeline configuration loader.

Includes helpers to interpret local-time windows and convert them to UTC.
"""

import tomllib
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from transit_delay_analytics.constants import DEFAULT_PIPELINE_CONFIG


@dataclass(frozen=True)
class SourceConfig:
    """Configuration for a single data source.

    Attributes:
        name (str): The source identifier key (e.g. 'gps', 'gtfs').
        url (str): The URL to fetch data from.
        format (str): The file format of the source data (e.g. 'csv', 'zip').
        description (str): Human-readable description of the source.
    """

    name: str
    url: str
    format: str
    description: str
    interval_seconds: int = 0
    timeout_seconds: int = 30
    window_start: str | None = None
    window_end: str | None = None
    timezone: str | None = None
    overwrite_existing: bool = False


def load_pipeline_config(
    config_path: Path = DEFAULT_PIPELINE_CONFIG,
) -> dict[str, SourceConfig]:
    """Load and parse the pipeline configuration from a TOML file.

    Args:
        config_path (Path): Path to the pipeline TOML configuration file.
    Returns:
        dict[str, SourceConfig]: A dictionary mapping source names to their configurations.
    Raises:
        FileNotFoundError: If the configuration file does not exist.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Pipeline config not found: {config_path}")

    with config_path.open("rb") as f:
        raw: dict[str, Any] = tomllib.load(f)

    return {
        name: SourceConfig(name=name, **{**values, "timezone": values.get("timezone")})
        for name, values in raw.get("sources", {}).items()
    }


def is_now_within_window(source: SourceConfig, now_utc: datetime | None = None) -> bool:
    """Return True if current UTC time is within the configured local window.

    This function keeps the configuration human-friendly (local wall-clock times)
    while comparing against system UTC time used by the pipeline.

    - If `window_start` or `window_end` is missing, the window is considered open.
    - `timezone` should be an IANA name like "Europe/Tallinn"; falls back to UTC.
    - Handles windows that span midnight (e.g., 23:00-02:00).
    """
    if not source.window_start or not source.window_end:
        return True

    tz_name = source.timezone or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")

    def _parse_hm(s: str) -> time:
        h, m = map(int, s.split(":"))
        return time(h, m)

    # Use today's date in the source timezone as the reference.
    today_local: date = datetime.now(tz).date()
    start_local = datetime.combine(
        today_local, _parse_hm(source.window_start), tzinfo=tz
    )
    end_local = datetime.combine(today_local, _parse_hm(source.window_end), tzinfo=tz)

    # If end is earlier-or-equal than start, assume the window crosses midnight.
    if end_local <= start_local:
        end_local = end_local + timedelta(days=1)

    start_utc = start_local.astimezone(ZoneInfo("UTC"))
    end_utc = end_local.astimezone(ZoneInfo("UTC"))

    now_utc = now_utc or datetime.now(timezone.utc)
    return start_utc <= now_utc <= end_utc
