"""Smoke-test for the standardized layer output.

Checks that all five models have been written correctly after a backfill run.
Run this after `tra transform --all-dates` or whenever you modify a transformer.

Usage:
    uv run python scripts/verify_standardized.py

What is checked:
    gps_positions   — schema (types, identifiers as String), coordinate bounds
                      within Estonia, partition count
    gtfs_stops      — schema, row count, sample rows
    gtfs_trips      — schema, row count, sample rows
    all models      — number of date= partitions in data/standardized/

Exit code 0 = all assertions passed.
Exit code 1 = an assertion failed (printed to stderr).
"""

import sys
from pathlib import Path

import polars as pl

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(".")

# ── GPS ───────────────────────────────────────────────────────────────────────
gps = pl.scan_parquet("data/standardized/gps_positions/**/*.parquet").collect()
print("=== GPS gps_positions ===")
print(dict(gps.schema))

total = len(gps)
dates = gps["snapshot_ts"].dt.date().n_unique()
spd_nulls = gps["speed_kmh"].null_count()
head_nulls = gps["heading_deg"].null_count()

assert str(gps.schema["vehicle_id"]) == "String", "vehicle_id should be String"
assert str(gps.schema["fleet_number"]) == "String", "fleet_number should be String"
assert str(gps.schema["lon"]) == "Float64", "lon should be Float64"

lon_min, lon_max = gps["lon"].min(), gps["lon"].max()
lat_min, lat_max = gps["lat"].min(), gps["lat"].max()
lon_ok = 20 < lon_min and lon_max < 30
lat_ok = 57 < lat_min and lat_max < 62

print(
    f"Rows: {total:,}  Dates: {dates}"
    f"  speed nulls: {spd_nulls:,}  heading nulls: {head_nulls:,}"
)
print(f"lon {lon_min:.4f}..{lon_max:.4f}  {'OK' if lon_ok else 'FAIL'}")
print(f"lat {lat_min:.4f}..{lat_max:.4f}  {'OK' if lat_ok else 'FAIL'}")

# ── GTFS stops ────────────────────────────────────────────────────────────────
stops = pl.read_parquet("data/standardized/gtfs_stops/date=2026-05-19/part.parquet")
print("\n=== GTFS gtfs_stops ===")
print(dict(stops.schema))
print(f"Rows: {len(stops)}")
print(stops.head(3))

# ── GTFS trips ────────────────────────────────────────────────────────────────
trips = pl.read_parquet("data/standardized/gtfs_trips/date=2026-05-19/part.parquet")
print("\n=== GTFS gtfs_trips ===")
print(dict(trips.schema))
print(f"Rows: {len(trips)}")
print(trips.head(3))

# ── Partition counts ──────────────────────────────────────────────────────────
print("\n=== Partition counts ===")
for model in [
    "gps_positions",
    "gtfs_stops",
    "gtfs_routes",
    "gtfs_trips",
    "gtfs_stop_times",
]:
    parts = sorted(Path(f"data/standardized/{model}").glob("date=*/part.parquet"))
    print(f"  {model}: {len(parts)} partitions")
