# Changelog

All notable changes to this project will be documented in this file.

This file follows a simplified Keep a Changelog style.

---

## [0.2.0] – Production-Style MVP

### Added

- **Hybrid recommender** (`strategy=hybrid`) combining MF ALS, content TF‑IDF, and popularity with configurable weights and a fallback ladder.
- **Cold-start onboarding**:
  - `POST /v1/users/onboard` to store `preferred_genres` and `preferred_keywords` in `users.attributes`.
  - Popular recommender prioritises items in preferred genres.
- **Admin item creation**: `POST /v1/admin/items` to register new items that content-based models can use immediately.
- **Real-time feedback loop**:
  - Enhanced `POST /v1/track` with typed `event_type` (`view|click|rate`).
  - Best-effort Redis updates for global popularity, per-genre popularity, and hourly trending buckets.
- **A/B testing framework**:
  - New tables: `experiments`, `assignments`, `events_agg`.
  - Deterministic assignment (`hybrid_vs_popular` experiment with variants `["hybrid", "popular"]`).
  - Impression logging on `/v1/recommendations` and click logging on `/v1/track`.
  - Admin APIs: create, list, and report on experiments.
- **Monitoring & dashboard**:
  - `/metrics` Prometheus-style endpoint with request counts, error counts, cache hit/miss, and latency buckets.
  - `/dashboard` HTML page showing entity counts, active models, and A/B CTR snapshot.
- **Deployment guide**:
  - `context/DEPLOYMENT.md` detailing Supabase + Upstash + HF Spaces setup.
- **Optional rate limiting**:
  - Simple per-IP, per-minute limiter controlled via `RATE_LIMIT_ENABLED` and `RATE_LIMIT_REQUESTS_PER_MIN`.

### Changed

- Dockerfile now exposes port `7860` and entrypoint defaults to `PORT=7860` for Hugging Face Spaces compatibility.
- Recommendation response schema extended with a `reasons: List[str]` field for richer explainability.
- `/v1/items/{id}/similar` now validates `limit` with sane bounds to prevent abuse.

### Removed

- n/a.

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