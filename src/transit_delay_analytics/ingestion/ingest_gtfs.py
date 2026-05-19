"""Ingestor implementation for GTFS Schedule data."""

from transit_delay_analytics.ingestion.base import BaseIngestor


class GTFSIngestor(BaseIngestor, source_name="gtfs"):
    """Ingestor for fetching daily GTFS zip archives."""
