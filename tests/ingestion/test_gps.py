"""Tests for the GPS ingestion module."""

from transit_delay_analytics.ingestion.base import BaseIngestor
from transit_delay_analytics.ingestion.ingest_gps import GPSIngestor


def test_gps_ingestor_is_registered():
    """GPSIngestor must be registered under source_name='gps'."""

    assert "gps" in BaseIngestor._registry
    assert BaseIngestor._registry["gps"] is GPSIngestor


def test_gps_factory_returns_correct_instance(make_source_config):
    """The factory method must return a GPSIngestor instance."""
    config = make_source_config(name="gps")

    ingestor = BaseIngestor.get_ingestor(config)
    assert isinstance(ingestor, GPSIngestor)
    assert ingestor.config is config
