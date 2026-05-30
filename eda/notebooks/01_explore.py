# %%
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GPS_DATE = "2026-05-23"
GPS_DATE_FILE = GPS_DATE.replace("-", "")
GPS_PATH = PROJECT_ROOT / "data/raw/source=gps" / f"date={GPS_DATE}" / "gps_*.csv"


# %%
# Defineerime veerunimed
headers = [
    "transport_type",  # 1=trolleybus, 2=bus, 3=tram, 7=night bus
    "line_number",  # string: e.g. `"8"`, `"18A"`
    "longitude_raw",  # Longitude × 1,000,000 (WGS84)
    "latitude_raw",  # Latitude × 1,000,000 (WGS84)
    "speed_kmh",  # Empty string when unavailable
    "heading_deg",  # `999` when unavailable
    "vehicle_id",  # Internal vehicle identifier
    "floor_type",  # Z = low-floor, false = unknown
    "fleet_number",  # Physical vehicle serial number
    "destination",  # Destination stop name
]

# %%
# Loeme kõik failid sisse, kasutades wildcardi (*) ja lisades failitee veeru
df = pl.scan_csv(
    GPS_PATH,
    separator=",",
    has_header=False,
    new_columns=headers,
    include_file_paths="file_path",
)

# %%
df.collect().head()

# %%
# Eralda timestamp failinimest + teisenda koordinaadid kraadideks
df = df.with_columns(
    pl.col("file_path").str.extract(r"(\d{8}_\d{6})")
    .str.strptime(pl.Datetime("us", "UTC"), format="%Y%m%d_%H%M%S")
    .alias("snapshot_ts"),
    (pl.col("longitude_raw") / 1_000_000).alias("lon"),
    (pl.col("latitude_raw") / 1_000_000).alias("lat"),
    pl.when(pl.col("heading_deg") == 999)
    .then(None)
    .otherwise(pl.col("heading_deg"))
    .alias("heading_deg"),
)

# Eemaldame abiveeru file_path, kui seda enam vaja pole
# df = df.drop("file_path")

# %%
# EDA algus: ülevaade
print(df.collect().shape)
df.collect().describe()

# %%
df.head().collect()


# %%
# =======================================================
# STANDARDIZED
# =======================================================

# Concatenate all snapshots for a date into one table.
# Parse columns, assign correct types, divide coordinates by 1,000,000,
# replace sentinel values (empty speed → `None`, heading 999 → `None`).
# Add `snapshot_ts` from filename. No filtering

standard_dir = PROJECT_ROOT / "data/standardized/gps_positions" / f"date={GPS_DATE}"
standard_dir.mkdir(parents=True, exist_ok=True)

df_std = df.with_columns(
    pl.col("file_path").str.extract(r"(data/.*)$")
)

df_std.collect().glimpse(max_items_per_column=3)
df_std.head().collect()

# %%
# Write standardized CSV
df_std.collect().write_csv(standard_dir / f"gps_positions_{GPS_DATE_FILE}.csv")


# %%
# =======================================================
# INTERMEDIATE
# =======================================================

# Filter `transport_type == 2` and `line_number == "8"`. Drop all other vehicles.

interim_dir = PROJECT_ROOT / "data/intermediate" / f"date={GPS_DATE}"
interim_dir.mkdir(parents=True, exist_ok=True)

df_int_8 = df_std.drop("file_path", "longitude_raw", "latitude_raw").filter(
    (pl.col("transport_type") == 2) & (pl.col("line_number") == "8")
)

df_int_8.collect().glimpse(max_items_per_column=3)
df_int_8.head().collect()

# %%
# Write intermediate CSV

df_int_8.collect().write_csv(interim_dir / f"route8_positions_{GPS_DATE_FILE}.csv")

# %%