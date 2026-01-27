# Components

This document describes each major component of the RecAI MVP and how they fit together.

---

## 1. API Layer

### `app/main.py`

- Creates the FastAPI application.
- Configures:
  - Logging (JSON-ish with `request_id` correlation).
  - Error handling (consistent error envelopes).
  - Routers under `/` and `/v1/*`.

### Routers (`app/routers/`)

- `health.py`
  - `GET /health` – simple liveness + version + env.
- `stats.py`
  - `GET /v1/stats` – counts for users, items, interactions, active model versions.
- `items.py`
  - `GET /v1/items/{item_id}` – fetch item details.
  - `GET /v1/items/{item_id}/similar` – content-based item similarity.
- `recommend.py`
  - `GET /v1/recommendations` – main entrypoint for user recommendations.
- `admin.py`
  - `GET /v1/admin/models` – list model versions.
  - `POST /v1/admin/train?model=content|mf` – synchronous training trigger.
- Tracking (part of admin module for now, but exposed under `/v1/track`):
  - `POST /v1/track` – track interactions.

Routers depend on:

- `app/db/session.get_db` for DB access.
- `app/recommenders/*` for recommendation logic.
- `app/services/*` for orchestration and side effects.

---

## 2. Core Infrastructure

### Config – `app/core/config.py`

- Uses `pydantic-settings`.
- Main fields:
  - `DATABASE_URL`
  - `REDIS_URL`
  - `ENV`
  - `LOG_LEVEL`
  - `DATA_DIR`
  - `ARTIFACT_DIR`
  - `PORT`
- Single `Settings` instance via `lru_cache`.

### Logging – `app/core/logging.py`

- Configures `logging` with:
  - Single JSON formatter that emits:
    - `time`
    - `level`
    - `logger`
    - `message`
    - optional `request_id`
  - Middleware:
    - Extracts `X-Request-ID` or generates UUID.
    - Sets contextvar so downstream logs include `request_id`.
    - Logs request start and end with latency.

### Error Handling – `app/core/error_handler.py`

- Converts exceptions into structured responses:

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "details": {...}
  },
  "request_id": "..."
}
```

- Handles:
  - `AppError` (domain errors).
  - FastAPI/Pydantic validation errors.
  - Unhandled exceptions (500).

---

## 3. Persistence Layer

### ORM Models – `app/db/models.py`

- `User`
  - `id`
  - `created_at`
  - `attributes` (JSONB / JSON variant)
- `Item`
  - `id`
  - `title`
  - `genres` (pipe-separated string e.g. `Action|Sci-Fi`)
  - `text` (text blob for content-based)
  - `metadata` (JSONB / JSON variant)
- `Interaction`
  - `id`
  - `user_id` → `users.id`
  - `item_id` → `items.id`
  - `event_type` (`view|click|rate`)
  - `rating` (optional float)
  - `ts` (timestamp)
  - Indexes:
    - (`user_id`, `ts`)
    - (`item_id`, `ts`)
    - (`user_id`, `item_id`)
- `ModelVersion`
  - `id`
  - `name` (e.g. `content_tfidf`, `mf_als`)
  - `version` (timestamp string)
  - `trained_at`
  - `metrics` (JSONB)
  - `path` (artifact path)
  - `is_active`
  - Unique on (`name`, `version`)

### Sessions – `app/db/session.py`

- SQLAlchemy engine from `DATABASE_URL`.
- `SessionLocal` factory.
- `get_db` dependency yields per-request session.

### Migrations – `app/db/migrations/` + `alembic.ini`

- Alembic environment configured against `DATABASE_URL`.
- Initial migration:
  - Creates all four core tables + indexes + constraints.

---

## 4. Recommenders

### Popular – `app/recommenders/popular.py`

- Aggregates `interactions` table:
  - Count per `item_id`.
  - Optional average rating (for later weighting).
- Returns globally popular items.
- Used as:
  - A baseline strategy.
  - Fallback when other models are not ready.

### Content-based TF‑IDF – `app/recommenders/content_tfidf.py`

- Trained from `items.text_blob` (title + genres + text).
- Artifact structure:
  - `vectorizer` (scikit-learn `TfidfVectorizer`)
  - `item_ids`
  - `item_titles`
  - `item_matrix` (dense TF-IDF vectors)
- Capabilities:
  - Recommend items for a user based on their past items.
  - Find similar items for a given `item_id`.
  - Simple explanation:
    - `"Because similar to 'Some Movie'"`.

### Matrix Factorization (ALS) – `app/recommenders/mf_implicit.py`

- Trained with `implicit.als.AlternatingLeastSquares`.
- Artifact structure:
  - `user_factors`
  - `item_factors`
  - `user_id_mapping`
  - `item_id_mapping`
- Online scoring:
  - Dot product between user and item vectors.
  - Filters out items already seen by the user.

### Hybrid – `app/recommenders/hybrid.py`

- Placeholder only; implemented in later work.

---

## 5. Services

### Interaction Service – `app/services/interaction_service.py`

- Ensures users and items exist (lightweight upsert) when tracking events.
- Inserts `Interaction` rows.
- Used by API endpoint `POST /v1/track`.

### Model Registry – `app/services/model_registry.py`

- Handles `model_versions` table:
  - Register new versions.
  - Deactivate previous active versions per model name.
  - Retrieve active version by name.
- Encapsulates logic for consistent model metadata.

### Cache Service – `app/services/cache_service.py`

- Thin wrapper around `redis.Redis`.
- Functions for:
  - Creating / reusing Redis client.
  - Building cache keys for per-user recommendations.
  - Getting/setting JSON-serialised cached recommendations.

---

## 6. Training & Evaluation

### Data Prep – `app/training/data_prep.py`

- Loads `interactions` and `items` into pandas DataFrames.
- Builds implicit feedback matrix:
  - Aggregated weights per `(user_id, item_id)` based on `event_type`.

### Evaluation – `app/training/eval.py`

- Implements:
  - `recall_at_k`
  - `ndcg_at_k`
  - `evaluate_recommender` (averages per-user metrics).

### Training – `app/training/train.py`

- `train_content_model(db)`:
  - Builds text blobs.
  - Trains TF‑IDF.
  - Saves artifact and registers model version.
- `train_mf_model(db)`:
  - Builds sparse implicit matrix.
  - Trains ALS model.
  - Saves factors and registers model version.
- CLI entry point:
  - `python -m app.training.train --model content|mf`.

---

## 7. Scripts & Notebooks

- `scripts/download_movielens_1m.py` – downloads dataset (or prints manual instructions).
- `scripts/seed_db.py` – populates Postgres from MovieLens 1M.
- `scripts/smoke_test_api.py` – quick ping to `/health` and `/v1/recommendations`.
- `notebooks/01_movielens_eda_and_eval.ipynb` – narrative EDA + evaluation.

---

## 8. CI/CD & Ops

- `.github/workflows/ci.yml`:
  - Install dependencies.
  - Run `ruff` and `pytest`.
- `docker/`:
  - `Dockerfile` & `entrypoint.sh` for app container.
- `docker-compose.yml`:
  - API + Postgres + Redis for local dev.

Use this document to understand **what** lives where and how components are intended to interact. For any architectural changes, update this file and `context/DECISIONS.md`.