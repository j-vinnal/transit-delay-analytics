# Use the official lightweight Python 3.11 base image
FROM python:3.11-slim

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory inside the container
WORKDIR /app

# Copy the project configuration, lockfile, and source code
COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY config/ config/

# Install the project and dependencies using uv
RUN uv sync --frozen

# Create empty data and logs directories to mount local volumes later
RUN mkdir -p data logs

# Set the timezone to UTC for consistent system time inside the container
ENV TZ="UTC"

# Tell Python where the source directory is
ENV PYTHONPATH="/app/src"

# Run the daemon process using the correct module name via uv run
CMD ["uv", "run", "transit_delay_analytics", "daemon"]