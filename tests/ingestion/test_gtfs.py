"""Tests for the GTFS ingestion module."""

from transit_delay_analytics.ingestion.base import BaseIngestor
from transit_delay_analytics.ingestion.ingest_gtfs import GTFSIngestor


def test_gtfs_ingestor_is_registered():
    """GTFSIngestor must be registered under source_name='gtfs'."""

    assert "gtfs" in BaseIngestor._registry
    assert BaseIngestor._registry["gtfs"] is GTFSIngestor


def test_gtfs_factory_returns_correct_instance(make_source_config):
    """The factory method must return a GTFSIngestor instance."""
    config = make_source_config(name="gtfs")

    ingestor = BaseIngestor.get_ingestor(config)
    assert isinstance(ingestor, GTFSIngestor)
    assert ingestor.config is config
