"""Central project constants."""

from transit_delay_analytics import PROJECT_ROOT


# Default configuration paths
DEFAULT_PIPELINE_CONFIG = PROJECT_ROOT / "config" / "pipeline.toml"
DEFAULT_LOG_CONFIG = PROJECT_ROOT / "config" / "logging.toml"

# Raw data base dir
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Logs dir
LOGS_DIR = PROJECT_ROOT / "logs"
