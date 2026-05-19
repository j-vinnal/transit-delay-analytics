"""Standardized transformer for GTFS stops."""

import io
import zipfile
from datetime import date

import polars as pl

from transit_delay_analytics.models.standardized.base import BaseTransformer
from transit_delay_analytics.models.standardized.gtfs._zip_loader import find_gtfs_zip


class GTFSStopsTransformer(BaseTransformer, model_name="gtfs_stops"):
    """Parses stops.txt from the GTFS ZIP into a typed DataFrame.

    Input:  data/raw/source=gtfs/date={date}/gtfs_*.zip → stops.txt
    Output: data/standardized/gtfs_stops/date={date}/part.parquet
    """

    _raw_source = "gtfs"

    def transform(self, target_date: date) -> pl.DataFrame:
        zip_path = find_gtfs_zip(target_date)
        with zipfile.ZipFile(zip_path) as z:
            df = pl.read_csv(io.BytesIO(z.read("stops.txt")), infer_schema_length=0)

        return df.select(
            [
                pl.col("stop_id").cast(pl.Utf8),
                pl.col("stop_name").cast(pl.Utf8),
                pl.col("stop_lat").cast(pl.Float64),
                pl.col("stop_lon").cast(pl.Float64),
            ]
        )
