"""Ingestor implementation for Real-Time GPS data."""

from datetime import datetime, timezone
from pathlib import Path

import requests

from transit_delay_analytics.ingestion.base import BaseIngestor


class GPSIngestor(BaseIngestor, source_name="gps"):
    """Ingestor for fetching real-time bus GPS locations."""

    def fetch(self) -> bytes:
        """Fetch GPS text data via HTTP GET."""
        response = requests.get(self.config.url, timeout=10)
        response.raise_for_status()
        return response.content

    def get_target_path(self) -> Path:
        # Use UTC timestamp for filename to ensure consistency across systems
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config.name}_{timestamp}.{self.config.format}"
        return self.get_save_dir() / filename
