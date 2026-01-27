PYTHON := python3
COMPOSE ?= docker compose

.PHONY: help install install-dev lint fmt format test run up down logs migrate seed train-content train-mf alembic-upgrade

help:
	@echo "Available targets:"
	@echo "  make install         - Install runtime dependencies"
	@echo "  make install-dev     - Install runtime + dev dependencies"
	@echo "  make up              - Start Postgres + Redis via docker compose"
	@echo "  make down            - Stop all docker-compose services"
	@echo "  make logs            - Tail logs for api + db + redis"
	@echo "  make migrate         - Run Alembic migrations (alembic upgrade head)"
	@echo "  make seed            - Seed the database with MovieLens 1M"
	@echo "  make train-content   - Train content-based TF-IDF model"
	@echo "  make train-mf        - Train MF ALS model"
	@echo "  make run             - Run FastAPI app with uvicorn (reload)"
	@echo "  make test            - Run pytest test suite"
	@echo "  make lint            - Run ruff lint checks"
	@echo "  make fmt             - Run ruff formatter"

install:
	$(PYTHON) -m pip install -r requirements.txt

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	ruff check .

fmt:
	ruff format .

# Backwards-compatible alias
format: fmt

test:
	pytest

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port ${PORT:-8000}

up:
	$(COMPOSE) up -d postgres redis

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f api postgres redis

migrate:
	alembic upgrade head

seed:
	$(PYTHON) scripts/seed_db.py

train-content:
	$(PYTHON) -m app.training.train --model content

train-mf:
	$(PYTHON) -m app.training.train --model mf

# Backwards-compatible alias
alembic-upgrade: migrate