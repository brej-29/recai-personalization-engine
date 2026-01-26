PYTHON := python3

.PHONY: install install-dev lint format test run alembic-upgrade

install:
	$(PYTHON) -m pip install -r requirements.txt

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

lint:
	ruff check .

format:
	black app tests scripts

test:
	pytest

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port $${PORT:-8000}

alembic-upgrade:
	alembic upgrade head