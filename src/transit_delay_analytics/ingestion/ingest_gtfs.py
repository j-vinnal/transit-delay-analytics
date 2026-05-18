"""Ingestor implementation for GTFS Schedule data."""

from datetime import datetime, timezone
from pathlib import Path

import requests

from transit_delay_analytics.ingestion.base import BaseIngestor


class GTFSIngestor(BaseIngestor, source_name="gtfs"):
    """Ingestor for fetching daily GTFS zip archives."""

    def fetch(self) -> bytes:
        """Fetch GTFS zip file via HTTP GET."""
        response = requests.get(self.config.url, timeout=30)
        response.raise_for_status()
        return response.content

    def get_target_path(self) -> Path:
        # Use UTC timestamp and include time to match GPS naming convention
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config.name}_{timestamp}.{self.config.format}"
        return self.get_save_dir() / filename
