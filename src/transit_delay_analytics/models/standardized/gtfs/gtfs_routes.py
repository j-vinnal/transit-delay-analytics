"""Standardized transformer for GTFS routes."""

import io
import zipfile
from datetime import date

import polars as pl

from transit_delay_analytics.models.standardized.base import BaseTransformer
from transit_delay_analytics.models.standardized.gtfs._zip_loader import find_gtfs_zip


class GTFSRoutesTransformer(BaseTransformer, model_name="gtfs_routes"):
    """Parses routes.txt from the GTFS ZIP into a typed DataFrame.

    Input:  data/raw/source=gtfs/date={date}/gtfs_*.zip → routes.txt
    Output: data/standardized/gtfs_routes/date={date}/part.parquet
    """

    _raw_source = "gtfs"

    def transform(self, target_date: date) -> pl.DataFrame:
        zip_path = find_gtfs_zip(target_date)
        with zipfile.ZipFile(zip_path) as z:
            df = pl.read_csv(io.BytesIO(z.read("routes.txt")), infer_schema_length=0)

        return df.select(
            [
                pl.col("route_id").cast(pl.Utf8),
                pl.col("route_short_name").cast(pl.Utf8),
                pl.col("route_long_name").cast(pl.Utf8),
                pl.col("route_type").cast(pl.Int32),
            ]
        )
