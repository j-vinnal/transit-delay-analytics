"""Central project constants."""

from transit_delay_analytics import PROJECT_ROOT

# Default configuration paths
DEFAULT_PIPELINE_CONFIG = PROJECT_ROOT / "config" / "pipeline.toml"
DEFAULT_LOG_CONFIG = PROJECT_ROOT / "config" / "logging.toml"

# Logs dir
LOGS_DIR = PROJECT_ROOT / "logs"

# ==========================================
# MODULE 1: INGESTION
# ==========================================

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

# ==========================================
# MODULE 2: DATA PIPELINE
# ==========================================

# Standardized data base dir
STANDARDIZED_DATA_DIR = PROJECT_ROOT / "data" / "standardized"
