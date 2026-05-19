"""Utility for locating the GTFS ZIP file for a given date partition."""

from datetime import date
from pathlib import Path

from transit_delay_analytics.constants import RAW_DATA_DIR


def find_gtfs_zip(target_date: date) -> Path:
    """Return the GTFS ZIP file for the given date partition.

    If multiple ZIPs exist for the same date (e.g. a re-download), returns
    the lexicographically latest one (highest timestamp in filename).

    Args:
        target_date: The date partition to look in.

    Returns:
        Path to the ZIP file.

    Raises:
        FileNotFoundError: If no ZIP is found for the given date.
    """
    raw_dir = RAW_DATA_DIR / "source=gtfs" / f"date={target_date}"
    zips = sorted(raw_dir.glob("*.zip"))
    if not zips:
        raise FileNotFoundError(
            f"No GTFS ZIP found for date {target_date} in {raw_dir}"
        )
    return zips[-1]
