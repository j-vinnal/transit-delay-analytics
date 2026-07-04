# Transit delay analytics

**Status: Experimental / Work in Progress**
This project is an ongoing architectural experiment. It is being used to test and evaluate different data processing strategies and is not a finalized or production-ready pipeline. Expect frequent breaking changes.

Configuration-driven data pipeline and stochastic modelling framework for analyzing public transport delays using GTFS and near real-time vehicle GPS data.

## Getting Started

### Prerequisites

### Installation

```sh
# Install uv if you don't have it yet
# https://docs.astral.sh/uv/getting-started/installation/

# Install the project and all dependencies
uv sync
```

### Docker Deployment

For long-running ingestion, deploying with Docker Compose is recommended. The container mounts local `data`, `logs`, and `config` directories - all downloaded files will appeare in host file system.

```bash
# Build the image and start the daemon in the background
docker-compose up -d --build

# View real-time logs
docker-compose logs -f

# Stop the container
docker-compose down

```

## Usage

The pipeline exposes three CLI commands: `ingest`, `daemon`, and `transform`.

> Alternatively to `uv run`, activate the virtual environment first (`source .venv/bin/activate` on Mac/Linux or `.venv\Scripts\activate` on Windows) and omit the `uv run` prefix.

### `ingest` — one-off data collection

Downloads the latest raw data from configured sources and saves it to `data/raw/`.

```sh
# Run all configured sources
uv run tra ingest

# Run a specific source
uv run tra ingest --source gps
uv run tra ingest --source gtfs
```

### `daemon` — continuous scheduled collection

Runs ingestors continuously on the schedules defined in `config/pipeline.toml`
(GPS every 30 s within a time window, GTFS once a day).

```sh
# Start daemon for all sources (also the default in Docker)
uv run tra daemon

# Daemon for a specific source
uv run tra daemon --source gps
```

### `transform` — standardize raw data

Reads raw files from `data/raw/`, parses and type-casts them, and writes
clean Parquet partitions to `data/standardized/`.

Each model produces one partition per date (`date=YYYY-MM-DD/part.parquet`).
Re-running is safe — existing partitions are skipped unless `--overwrite` is passed.

```sh
# Standardize today's GPS data
uv run tra transform --model gps_positions

# Standardize a specific date
uv run tra transform --model gps_positions --date 2026-05-19

# Backfill all available dates
uv run tra transform --model gps_positions --all-dates

# Backfill a date range
uv run tra transform --model gps_positions --date-from 2026-05-12 --date-to 2026-05-19

# Run all models for today
uv run tra transform

# Force overwrite existing partitions
uv run tra transform --model gtfs_stops --all-dates --overwrite
```

Available models: `gps_positions`, `gtfs_stops`, `gtfs_routes`, `gtfs_trips`, `gtfs_stop_times`

## Development Utilities

### `scripts/verify_standardized.py`

Validates the output of the standardized layer — checks schemas, coordinate
bounds, and partition counts across all five models. Run after a backfill
or when adding a new transformer.

```sh
uv run python scripts/verify_standardized.py
```

## Repository Structure

## Execution Flow

## Data Documentation

## Methodology & Thought Process

## Dependencies & Tech Stack

## Limitations & Future Work

## License

This project is licensed under the MIT License.
