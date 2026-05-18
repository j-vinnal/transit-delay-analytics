"""Abstract base class for data ingestors."""

from datetime import datetime, timezone
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from transit_delay_analytics import PROJECT_ROOT
from transit_delay_analytics.core.config import SourceConfig

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)


class BaseIngestor(ABC):
    """Abstract base class defining the interface for all data ingestors."""

    # All created subclasses are collected here
    _registry: dict[str, type["BaseIngestor"]] = {}

    def __init_subclass__(cls, source_name: str, **kwargs: Any) -> None:
        """Automatically registers subclasses when they are defined."""
        super().__init_subclass__(**kwargs)
        cls._registry[source_name] = cls

    @classmethod
    def get_ingestor(cls, source_config: SourceConfig) -> "BaseIngestor":
        """Factory method to get the correct ingestor instance."""
        ingestor_class = cls._registry.get(source_config.name)
        if not ingestor_class:
            raise ValueError(
                f"No ingestor registered for source: '{source_config.name}'"
            )
        return ingestor_class(source_config)

    def __init__(self, source_config: SourceConfig) -> None:
        self.config = source_config
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_save_dir(self) -> Path:
        """Generates a Hive-style partitioned directory for the current UTC date.

        The `date=` partition is derived from UTC to avoid DST/timezone issues.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        # Create directory: data/raw/source=gps/date=2026-05-12/
        dir_path = (
            PROJECT_ROOT
            / "data"
            / "raw"
            / f"source={self.config.name}"
            / f"date={today}"
        )
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @abstractmethod
    def fetch(self) -> bytes:
        pass

    def save(self, data: bytes) -> Path:
        """Default save implementation writing raw bytes to the target path.

        Subclasses may override if special handling is required.
        """
        target = self.get_target_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as f:
            f.write(data)
        return target

    @abstractmethod
    def get_target_path(self) -> Path:
        """Determines the target path for the data without saving it yet."""
        pass

    def run(self) -> None:
        """Orchestrate the ingestion process with idempotency check."""
        target_path = self.get_target_path()

        if target_path.exists() and not self.config.overwrite_existing:
            self.logger.info(
                "Ingestion skipped: File already exists",
                extra={
                    "source": self.config.name,
                    "path": str(target_path.relative_to(PROJECT_ROOT)),
                },
            )
            return

        self.logger.info("Ingestion started", extra={"url": self.config.url})
        try:
            raw_data = self.fetch()
            saved_path = self.save(raw_data)

            size_mb = round(len(raw_data) / (1024 * 1024), 2)
            self.logger.info(
                "Ingestion completed",
                extra={"saved_to": str(saved_path), "size_mb": size_mb},
            )
        except Exception:
            self.logger.exception(
                "Ingestion failed", extra={"source": self.config.name}
            )
            raise
