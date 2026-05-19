"""Abstract base class for standardized-layer transformers."""

import logging
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Any, ClassVar

import polars as pl

from transit_delay_analytics import PROJECT_ROOT
from transit_delay_analytics.constants import RAW_DATA_DIR, STANDARDIZED_DATA_DIR


class BaseTransformer(ABC):
    """Abstract base class defining the interface for all standardized transformers.

    Each concrete subclass must define:
        - `model_name` (via class keyword argument): registry key and
          output directory name
        - `_raw_source` (class attribute): the source name used in raw data path
          (e.g. "gps" → data/raw/source=gps/)
    """

    _registry: ClassVar[dict[str, type["BaseTransformer"]]] = {}
    _model_name: ClassVar[str]  # set automatically by __init_subclass__
    _raw_source: ClassVar[str]  # must be defined by each concrete subclass

    def __init_subclass__(cls, model_name: str, **kwargs: Any) -> None:
        """Automatically registers subclasses and stores their model name."""
        super().__init_subclass__(**kwargs)
        cls._model_name = model_name
        cls._registry[model_name] = cls

    @classmethod
    def get_transformer(cls, model_name: str) -> "BaseTransformer":
        """Factory method to get the correct transformer instance."""
        klass = cls._registry.get(model_name)
        if not klass:
            raise ValueError(f"No transformer registered for: '{model_name}'")
        return klass()

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_output_path(self, target_date: date) -> Path:
        """Returns the output parquet path for the given date.

        Pattern: data/standardized/{model_name}/date=YYYY-MM-DD/part.parquet
        Does not create directories (no side effects).
        """
        return (
            STANDARDIZED_DATA_DIR
            / self._model_name
            / f"date={target_date}"
            / "part.parquet"
        )

    def discover_dates(self) -> list[date]:
        """Find all dates for which raw data is available.

        Scans data/raw/source={_raw_source}/date=*/ directories.
        """
        raw_dir = RAW_DATA_DIR / f"source={self._raw_source}"
        return sorted(
            date.fromisoformat(d.name.removeprefix("date="))
            for d in raw_dir.glob("date=*/")
            if d.is_dir()
        )

    @abstractmethod
    def transform(self, target_date: date) -> pl.DataFrame:
        """Pure transformation: read raw data for the given date,
        return clean DataFrame.

        Must not write to disk, log, or produce side effects.
        """
        ...

    def run(self, target_date: date, overwrite: bool = False) -> Path | None:
        """Orchestrate: idempotency check → transform → write parquet.

        Args:
            target_date: The date partition to process.
            overwrite: If True, overwrite an existing partition.

        Returns:
            Path to the written parquet file, or None if skipped.
        """
        output = self.get_output_path(target_date)

        if output.exists() and not overwrite:
            self.logger.info(
                "Transform skipped: partition already exists",
                extra={
                    "model": self._model_name,
                    "path": str(output.relative_to(PROJECT_ROOT)),
                },
            )
            return None

        self.logger.info(
            "Transform started",
            extra={"model": self._model_name, "date": str(target_date)},
        )

        try:
            df = self.transform(target_date)
        except Exception:
            self.logger.exception(
                "Transform failed",
                extra={"model": self._model_name, "date": str(target_date)},
            )
            raise

        if df.is_empty():
            self.logger.warning(
                "No data found, partition not written",
                extra={"model": self._model_name, "date": str(target_date)},
            )
            return None

        output.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(output)

        self.logger.info(
            "Transform completed",
            extra={
                "model": self._model_name,
                "date": str(target_date),
                "rows": len(df),
                "saved_to": str(output.relative_to(PROJECT_ROOT)),
            },
        )
        return output
