#!/usr/bin/env bash
set -e

# Apply database migrations
echo "Running Alembic migrations..."
alembic upgrade head || echo "Alembic migrations failed or not configured; continuing."

# Start the API
echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"