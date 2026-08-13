"""Ingestor implementation for GTFS Schedule data."""
import zipfile
from pathlib import Path

from transit_delay_analytics.constants import relative_to_project
from transit_delay_analytics.ingestion.base import BaseIngestor


class GTFSIngestor(BaseIngestor, source_name="gtfs"):
    """Ingestor for fetching daily GTFS zip archives."""

    def post_process(self, path: Path) -> None:
        """Extract the GTFS archive into a run-specific directory.

        The extraction directory is derived from the ZIP filename, which already
        contains a timestamp.

        Example:
            gtfs_20260813_101500.zip
            gtfs_20260813_101500/
                agency.txt
                routes.txt
        """
        extract_dir = path.with_suffix("")

        if extract_dir.exists():
            self.logger.info(
                "Extraction skipped: directory already exists",
                extra={
                    "source": self.config.name,
                    "path": str(relative_to_project(extract_dir)),
                },
            )
            return

        with zipfile.ZipFile(path) as zf:
            zf.extractall(extract_dir)

        self.logger.info(
            "Extraction completed",
            extra={
                "saved_to": str(relative_to_project(extract_dir)),
            },
        )
