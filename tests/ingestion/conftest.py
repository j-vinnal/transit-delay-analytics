"""Shared pytest fixtures for the ingestion test suite."""

from typing import Any

import pytest

from transit_delay_analytics.core.config import SourceConfig


@pytest.fixture
def raw_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("transit_delay_analytics.ingestion.base.RAW_DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def make_source_config():
    def _make(**overrides) -> SourceConfig:
        defaults = dict[str, Any](
            name="test_source",
            url="https://example.invalid/data",
            format="json",
            description="Test source for unit tests",
            interval_seconds=0,
            timeout_seconds=30,
            window_start=None,
            window_end=None,
            timezone=None,
            overwrite_existing=False,
        )
        defaults.update(overrides)
        return SourceConfig(**defaults)

    return _make
