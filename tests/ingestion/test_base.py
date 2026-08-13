"""Tests for the ingestion base module."""

from pathlib import Path
import pytest
from transit_delay_analytics.ingestion.base import BaseIngestor


# ---------------------------------------------------------------------------
# Subclass registration
# ---------------------------------------------------------------------------
def test_subclass_is_registered() -> None:
    """Defining a subclass with source_name must auto-register it."""

    class TestIngestor(BaseIngestor, source_name="auto_test"):
        pass

    assert "auto_test" in BaseIngestor._registry
    assert BaseIngestor._registry["auto_test"] is TestIngestor


def test_duplicate_source_name_raises():
    """A duplicate source_name must raise ValueError — this guards against
    configuration mistakes where two different sources share the same key."""

    class FirstIngestor(BaseIngestor, source_name="dup"):
        pass

    with pytest.raises(ValueError, match="already registered"):
        class SecondIngestor(BaseIngestor, source_name="dup"):
            pass


# ---------------------------------------------------------------------------
# Factory method
# ---------------------------------------------------------------------------
def test_get_ingestor_returns_correct_instance(make_source_config):
    """The factory method must return the right class instance bound to
    the supplied SourceConfig."""

    class FactoryIngestor(BaseIngestor, source_name="factory_test"):
        pass

    config = make_source_config(name="factory_test")

    ingestor = BaseIngestor.get_ingestor(config)
    assert isinstance(ingestor, FactoryIngestor)
    assert ingestor.config is config


def test_get_ingestor_raises_for_unknown_source(make_source_config):
    config = make_source_config(name="does_not_exist")

    with pytest.raises(ValueError, match="does_not_exist"):
        BaseIngestor.get_ingestor(config)


# ---------------------------------------------------------------------
# run() template method
# ---------------------------------------------------------------------
def test_run_calls_steps_in_correct_order(make_source_config, monkeypatch):
    """run() is a fixed skeleton: fetch -> save -> post_process"""

    class DummyIngestor(BaseIngestor, source_name="dummy_test_source"):
        pass

    config = make_source_config(name="dummy_test_source")

    ingestor = BaseIngestor.get_ingestor(config)

    call_order: list[str] = []

    def fake_fetch() -> bytes:
        call_order.append("fetch")
        return b"raw-bytes"

    def fake_save(data: bytes, path: Path) -> Path:
        call_order.append("save")
        assert data == b"raw-bytes"
        return path

    def fake_post_process(path: Path) -> None:
        call_order.append("post_process")

    monkeypatch.setattr(ingestor, "fetch", fake_fetch)
    monkeypatch.setattr(ingestor, "save", fake_save)
    monkeypatch.setattr(ingestor, "post_process", fake_post_process)

    ingestor.run()

    assert call_order == ["fetch", "save", "post_process"]
