"""Central project constants."""

import os
from pathlib import Path

# Project root resolution:
#   1. TRA_PROJECT_ROOT env var (Docker, CI, installed package)
#   2. Fallback: derived from src-layout (src/transit_delay_analytics/constants.py)
_DEFAULT_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(os.environ.get("TRA_PROJECT_ROOT", _DEFAULT_ROOT))


def relative_to_project(path: Path) -> Path:
    """Return path relative to PROJECT_ROOT for logging; fall back to absolute."""
    try:
        return path.relative_to(PROJECT_ROOT)
    except ValueError:
        return path


# Default configuration paths
DEFAULT_PIPELINE_CONFIG = PROJECT_ROOT / "config" / "pipeline.toml"
DEFAULT_LOG_CONFIG = PROJECT_ROOT / "config" / "logging.toml"

# Logs dir
LOGS_DIR = PROJECT_ROOT / "logs"

# ==========================================
# MODULE 1: INGESTION
# ==========================================

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Hive-style partition keys
HIVE_SOURCE_PARTITION_KEY = "extract_source"
HIVE_DATE_PARTITION_KEY = "extract_date"

# ==========================================
# MODULE 2: DATA PIPELINE
# ==========================================

# Standardized data base dir
STANDARDIZED_DATA_DIR = PROJECT_ROOT / "data" / "standardized"
