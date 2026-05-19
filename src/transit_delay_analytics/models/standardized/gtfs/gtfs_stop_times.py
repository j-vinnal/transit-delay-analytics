"""Standardized transformer for GTFS stop times."""

import io
import zipfile
from datetime import date

import polars as pl

from transit_delay_analytics.models.standardized.base import BaseTransformer
from transit_delay_analytics.models.standardized.gtfs._zip_loader import find_gtfs_zip


class GTFSStopTimesTransformer(BaseTransformer, model_name="gtfs_stop_times"):
    """Parses stop_times.txt from the GTFS ZIP into a typed DataFrame.

    Input:  data/raw/source=gtfs/date={date}/gtfs_*.zip → stop_times.txt
    Output: data/standardized/gtfs_stop_times/date={date}/part.parquet

    Note on arrival_time / departure_time:
        GTFS allows times beyond 23:59:59 (e.g. "25:30:00") for trips that run
        past midnight. Polars `Time` cannot represent these values. The columns
        are intentionally kept as Utf8 strings and will be converted in the
        intermediate layer where the context (service date) is available.
    """

    _raw_source = "gtfs"

    def transform(self, target_date: date) -> pl.DataFrame:
        zip_path = find_gtfs_zip(target_date)
        with zipfile.ZipFile(zip_path) as z:
            df = pl.read_csv(
                io.BytesIO(z.read("stop_times.txt")), infer_schema_length=0
            )

        return df.select(
            [
                pl.col("trip_id").cast(pl.Utf8),
                pl.col("arrival_time").cast(pl.Utf8),  # "25:30:00" possible
                pl.col("departure_time").cast(pl.Utf8),  # "25:30:00" possible
                pl.col("stop_id").cast(pl.Utf8),
                pl.col("stop_sequence").cast(pl.Int32),
            ]
        )
