#!/usr/bin/env bash
set -euo pipefail

echo "[RUN_LOCAL] Starting local RecAI stack (Postgres + Redis + API)..."

# Detect docker compose vs docker-compose
if command -v docker &>/dev/null && docker compose version &>/dev/null; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose &>/dev/null; then
  COMPOSE_CMD="docker-compose"
else
  echo "[RUN_LOCAL] ERROR: Neither 'docker compose' nor 'docker-compose' is available."
  echo "[RUN_LOCAL] Install Docker Desktop (with Docker Compose) and try again."
  exit 1
fi

echo "[RUN_LOCAL] Using '${COMPOSE_CMD}'"

# Ensure .env exists
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    echo "[RUN_LOCAL] .env not found, copying from .env.example"
    cp .env.example .env
  else
    echo "[RUN_LOCAL] ERROR: .env and .env.example are missing. Create a .env first."
    exit 1
  fi
fi

echo "[RUN_LOCAL] Bringing up Postgres + Redis..."
${COMPOSE_CMD} up -d postgres redis

echo "[RUN_LOCAL] Applying database migrations (alembic upgrade head)..."
if ! alembic upgrade head; then
  echo "[RUN_LOCAL] WARNING: Alembic migrations failed. Check DATABASE_URL and Postgres status."
fi

echo "[RUN_LOCAL] Downloading MovieLens 1M dataset (if needed)..."
python scripts/download_movielens_1m.py

echo "[RUN_LOCAL] Seeding database (idempotent via marker file)..."
mkdir -p data
SEED_MARKER="data/.seeded"
if [ ! -f "${SEED_MARKER}" ]; then
  python scripts/seed_db.py
  touch "${SEED_MARKER}"
  echo "[RUN_LOCAL] Database seeded. Marker created at ${SEED_MARKER}."
else
  echo "[RUN_LOCAL] ${SEED_MARKER} exists; skipping seed_db.py."
  echo "[RUN_LOCAL] To re-seed, delete the marker and reset DB volumes (see context/RUN_LOCAL.md)."
fi

echo "[RUN_LOCAL] Training content-based model (if needed)..."
mkdir -p artifacts
if [ ! -f "artifacts/content_tfidf.pkl" ]; then
  if python -m app.training.train --model content; then
    echo "[RUN_LOCAL] Content-based model trained."
  else
    echo "[RUN_LOCAL] WARNING: Content model training failed; API will still work with popular strategy."
  fi
else
  echo "[RUN_LOCAL] artifacts/content_tfidf.pkl exists; skipping content training."
fi

echo "[RUN_LOCAL] Training MF model (if needed)..."
if [ ! -f "artifacts/mf_als.pkl" ]; then
  if python -m app.training.train --model mf; then
    echo "[RUN_LOCAL] MF model trained."
  else
    echo "[RUN_LOCAL] WARNING: MF model training failed; API will still work with popular strategy."
  fi
else
  echo "[RUN_LOCAL] artifacts/mf_als.pkl exists; skipping MF training."
fi

PORT="${PORT:-8000}"
echo "[RUN_LOCAL] Starting API with Uvicorn on http://127.0.0.1:${PORT} ..."
exec uvicorn app.main:app --reload --host 0.0.0.0 --port "${PORT}"