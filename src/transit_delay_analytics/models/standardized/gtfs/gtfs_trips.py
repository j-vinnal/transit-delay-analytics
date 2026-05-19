"""Standardized transformer for GTFS trips."""

import io
import zipfile
from datetime import date

import polars as pl

from transit_delay_analytics.models.standardized.base import BaseTransformer
from transit_delay_analytics.models.standardized.gtfs._zip_loader import find_gtfs_zip


class GTFSTripsTransformer(BaseTransformer, model_name="gtfs_trips"):
    """Parses trips.txt from the GTFS ZIP into a typed DataFrame.

    Input:  data/raw/source=gtfs/date={date}/gtfs_*.zip → trips.txt
    Output: data/standardized/gtfs_trips/date={date}/part.parquet
    """

    _raw_source = "gtfs"

    def transform(self, target_date: date) -> pl.DataFrame:
        zip_path = find_gtfs_zip(target_date)
        with zipfile.ZipFile(zip_path) as z:
            # infer_schema_length=0 reads all columns as Utf8, avoiding
            # type inference failures from non-standard GTFS extensions
            df = pl.read_csv(io.BytesIO(z.read("trips.txt")), infer_schema_length=0)

        return df.select(
            [
                pl.col("trip_id").cast(pl.Utf8),
                pl.col("route_id").cast(pl.Utf8),
                pl.col("service_id").cast(pl.Utf8),
            ]
        )
