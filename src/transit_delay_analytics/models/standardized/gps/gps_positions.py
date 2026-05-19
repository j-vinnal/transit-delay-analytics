"""Standardized transformer for GPS vehicle position snapshots."""

import io
from datetime import UTC, date, datetime
from pathlib import Path

import polars as pl

from transit_delay_analytics.constants import RAW_DATA_DIR
from transit_delay_analytics.models.standardized.base import BaseTransformer

# Column names matching the verified GPS API schema (headerless CSV, 10 columns).
# See: doc_project_structure_flow.md §3.1
_GPS_RAW_COLUMNS = [
    "transport_type",
    "line_number",
    "longitude_raw",
    "latitude_raw",
    "speed_kmh",
    "heading_deg",
    "vehicle_id",
    "floor_type",
    "fleet_number",
    "destination",
]

# Sentinel value used by the API to signal "heading unavailable"
_HEADING_UNAVAILABLE = 999


def _parse_snapshot_ts(path: Path) -> datetime:
    """Parse UTC timestamp from GPS filename: gps_YYYYMMDD_HHMMSS.csv"""
    ts_str = path.stem[4:]  # strip leading "gps_"
    return datetime.strptime(ts_str, "%Y%m%d_%H%M%S").replace(tzinfo=UTC)


def _read_snapshot(path: Path) -> pl.DataFrame:
    """Read one GPS snapshot CSV and return a typed DataFrame with snapshot_ts."""
    ts = _parse_snapshot_ts(path)
    return pl.read_csv(
        io.BytesIO(path.read_bytes()),
        has_header=False,
        new_columns=_GPS_RAW_COLUMNS,
        # Empty string → null (handles missing speed_kmh)
        null_values="",
        schema_overrides={
            "transport_type": pl.Int32,
            "longitude_raw": pl.Int64,
            "latitude_raw": pl.Int64,
            "speed_kmh": pl.Int32,
            "heading_deg": pl.Int32,
            # Identifiers — force Utf8 even if values happen to be numeric
            "vehicle_id": pl.Utf8,
            "fleet_number": pl.Utf8,
        },
    ).with_columns(pl.lit(ts).cast(pl.Datetime("us", "UTC")).alias("snapshot_ts"))


class GPSPositionsTransformer(BaseTransformer, model_name="gps_positions"):
    """Standardizes all GPS snapshots for a single date into one typed DataFrame.

    Input:  data/raw/source=gps/date={date}/gps_YYYYMMDD_HHMMSS.csv  (N files)
    Output: data/standardized/gps_positions/date={date}/part.parquet
    """

    _raw_source = "gps"

    def transform(self, target_date: date) -> pl.DataFrame:
        """Concatenate all GPS snapshots for the date, cast types, clean sentinels."""
        raw_dir = RAW_DATA_DIR / "source=gps" / f"date={target_date}"
        files = sorted(raw_dir.glob("*.csv"))

        if not files:
            return pl.DataFrame()

        df = pl.concat([_read_snapshot(f) for f in files])

        return (
            df.with_columns(
                [
                    # Divide raw integer coordinates to WGS84 degrees
                    (pl.col("longitude_raw") / 1_000_000).alias("lon"),
                    (pl.col("latitude_raw") / 1_000_000).alias("lat"),
                    # Replace heading sentinel 999 with null
                    pl.when(pl.col("heading_deg") == _HEADING_UNAVAILABLE)
                    .then(None)
                    .otherwise(pl.col("heading_deg"))
                    .alias("heading_deg"),
                ]
            )
            .drop(["longitude_raw", "latitude_raw"])
            .select(
                [
                    "snapshot_ts",
                    "transport_type",
                    "line_number",
                    "lon",
                    "lat",
                    "speed_kmh",
                    "heading_deg",
                    "vehicle_id",
                    "floor_type",
                    "fleet_number",
                    "destination",
                ]
            )
            .sort("snapshot_ts")
        )
