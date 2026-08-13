"""Abstract base class for data ingestors."""

import logging
from abc import ABC
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from transit_delay_analytics.core.config import SourceConfig
from transit_delay_analytics.constants import (
    HIVE_DATE_PARTITION_KEY,
    HIVE_SOURCE_PARTITION_KEY,
    RAW_DATA_DIR,
    relative_to_project,
)


class BaseIngestor(ABC):
    """Base implementation for data ingestion workflows."""

    _registry: dict[str, type["BaseIngestor"]] = {}

    def __init_subclass__(cls, source_name: str, **kwargs: Any) -> None:
        """Registers subclasses when they are defined."""
        super().__init_subclass__(**kwargs)
        if source_name in cls._registry:
            raise ValueError(f"Source is already registered: {source_name!r}")
        cls._registry[source_name] = cls

    @classmethod
    def get_ingestor(cls, source_config: SourceConfig) -> "BaseIngestor":
        """Factory method to get the correct ingestor instance."""
        ingestor_class = cls._registry.get(source_config.name)
        if ingestor_class is None:
            raise ValueError(
                f"No ingestor registered for source: '{source_config.name}'"
            )
        return ingestor_class(source_config)

    def __init__(self, source_config: SourceConfig) -> None:
        self.config = source_config
        self.logger = logging.getLogger(self.__class__.__name__)

    # ---------------------------------------------------------------------------
    # Template Method: fixed workflow, subclasses should not override
    # ---------------------------------------------------------------------------
    def run(self) -> None:
        """Orchestrate the ingestion process with idempotency check."""
        target_path = self.get_target_path()

        if target_path.exists() and not self.config.overwrite_existing:
            self.logger.info(
                "Ingestion skipped: File already exists",
                extra={
                    "source": self.config.name,
                    "path": str(relative_to_project(target_path)),
                },
            )
            return

        self.logger.info("Ingestion started", extra={"url": self.config.url})
        try:
            raw_data = self.fetch()
            saved_path = self.save(raw_data, target_path)
            size_mb = round(len(raw_data) / (1024 * 1024), 2)
            self.post_process(saved_path)

            self.logger.info(
                "Ingestion completed",
                extra={
                    "saved_to": str(relative_to_project(saved_path)),
                    "size_mb": size_mb,
                },
            )
        except Exception:
            self.logger.exception(
                "Ingestion failed", extra={"source": self.config.name}
            )
            raise

    # ---------------------------------------------------------------------------
    # Workflow steps, override when needed
    # ---------------------------------------------------------------------------
    def get_target_path(self) -> Path:
        """Determines the target path using a Hive-style partitioned directory and UTC timestamp filename."""
        now = datetime.now(UTC)
        today = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f"{self.config.name}_{timestamp}.{self.config.format}"

        return (
                RAW_DATA_DIR
                / f"{HIVE_SOURCE_PARTITION_KEY}={self.config.name}"
                / f"{HIVE_DATE_PARTITION_KEY}={today}"
                / filename
        )

    def fetch(self) -> bytes:
        """Fetch raw data via HTTP GET using the configured timeout."""
        response = requests.get(self.config.url, timeout=self.config.timeout_seconds)
        response.raise_for_status()
        return response.content

    @staticmethod
    def save(data: bytes, path: Path) -> Path:
        """Write raw bytes to the given path, creating parent directories."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def post_process(self, path: Path) -> None:
        """Post-process the saved artifact. No-op by default."""
        pass
