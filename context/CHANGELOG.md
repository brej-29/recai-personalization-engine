# Changelog

All notable changes to this project will be documented in this file.

This file follows a simplified Keep a Changelog style.

---

## [0.1.0] – Initial MVP

### Added

- FastAPI application with health, stats, items, recommendations, tracking, and admin endpoints.
- SQLAlchemy 2.0 models and Alembic migrations for:
  - `users`
  - `items`
  - `interactions`
  - `model_versions`
- Structured logging with per-request `request_id`.
- Centralised exception handling with consistent JSON error schema.
- MovieLens 1M ingestion pipeline:
  - Dataset downloader script.
  - DB seeding script.
- Recommenders:
  - Popular baseline.
  - Content-based TF‑IDF.
  - Matrix factorisation using `implicit` ALS.
- Model registry and artifact storage under `artifacts/`.
- Redis caching for per-user recommendation results.
- EDA + evaluation notebook scaffold.
- Context documentation (`context/*.md`).
- Dockerfile and `docker-compose.yml` for local dev.
- CI workflow with linting (ruff) and tests (pytest).

### Changed

- n/a – initial version.

### Removed

- n/a – initial version.

---

For future work:

- Add A/B testing framework and experiment tracking.
- Extend to multi-domain and multi-tenant scenarios.
- Improve observability (metrics, tracing, dashboards).