"""Ingestor implementation for Real-Time GPS data."""

from transit_delay_analytics.ingestion.base import BaseIngestor


class GPSIngestor(BaseIngestor, source_name="gps"):
    """Ingestor for fetching real-time bus GPS locations."""
