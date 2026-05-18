# Transit delay analytics

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

The pipeline is operated via a CLI with execution mode: `ingest` (one-off).

```sh
# Run all configured sources at once
uv run tra ingest

# Run a specific source
uv run tra ingest --source gps
uv run tra ingest --source gtfs
```

> Alternatively, activate the virtual environment first (`source .venv/bin/activate` on Mac/Linux or `.venv\Scripts\activate` on Windows) and omit the `uv run` prefix.

## Repository Structure

## Execution Flow

## Data Documentation

## Methodology & Thought Process

## Dependencies & Tech Stack

## Limitations & Future Work

## License

This project is licensed under the MIT License.
