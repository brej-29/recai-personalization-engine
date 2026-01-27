# Architecture

At a high level RecAI is a **stateless FastAPI web service** that talks to:

- **Postgres** (SQLAlchemy 2.0 + Alembic)
- **Redis** (redis-py)
- **Local disk** for model artifacts (`artifacts/`)

Supabase and Upstash are used in production by simply changing `DATABASE_URL`
and `REDIS_URL` environment variables.

---

## ASCII Diagram

```text
                 +-------------------------+
                 |  Client / Integrations  |
                 |  (web, mobile, batch)   |
                 +------------+------------+
                              |
                              v
                   HTTP (FastAPI / Uvicorn)
                              |
                              v
                    +---------+---------+
                    |   RecAI API       |
                    |  app.main:app     |
                    +---------+---------+
                              |
        +---------------------+----------------------+
        |                    |                      |
        v                    v                      v
  +-----+------+      +------+-------+       +------+------+
  | Routers    |      | Services     |       | Recommenders|
  | (health,   |      | (DB, cache,  |       | popular,    |
  | stats,     |      | model reg,   |       | content, mf)|
  | items,     |      | interactions)|       +------+------+
  | recommend, |      +------+-------+              |
  | admin)     |             |                      |
  +-----+------+             |                      |
        |                    |                      |
        v                    v                      v
  +-----+------+     +-------+--------+     +-------+--------+
  | Core       |     | Postgres       |     | Redis          |
  | (config,   |<--> | users, items,  |<--> | per-user rec    |
  | logging,   |     | interactions,  |     | cache           |
  | errors)    |     | model_versions |     +-----------------+
  +------------+     +----------------+
                           |
                           v
                     +-----+------+
                     | Artifacts  |
                     |  (local/   |
                     |  HF Spaces)|
                     +------------+
```

---

## Key Components

- **FastAPI Application (`app/main.py`)**
  - Creates the app, wires middleware, logging, and routers.
  - Exposes:
    - `/health`
    - `/v1/stats`
    - `/v1/items/{id}`, `/v1/items/{id}/similar`
    - `/v1/recommendations`
    - `/v1/track`
    - `/v1/admin/models`
    - `/v1/admin/train`

- **Core**
  - `app/core/config.py` – pydantic-settings based configuration.
  - `app/core/logging.py` – JSON-ish logging with per-request `request_id`.
  - `app/core/exceptions.py` – structured application exceptions.
  - `app/core/error_handler.py` – global FastAPI exception handlers.

- **Database (`app/db/`)**
  - `models.py` – SQLAlchemy 2.0 ORM models:
    - `User`
    - `Item`
    - `Interaction`
    - `ModelVersion`
  - `session.py` – session factory and request-scoped DB dependency.
  - `migrations/` – Alembic migrations with `alembic.ini` at repo root.

- **Recommenders (`app/recommenders/`)**
  - `popular.py` – computes globally popular items from interactions.
  - `content_tfidf.py` – TF‑IDF item representations, user- and item-based recs.
  - `mf_implicit.py` – matrix factorization via `implicit` ALS.
  - `hybrid.py` – placeholder for Prompt 2.

- **Services (`app/services/`)**
  - `interaction_service.py` – tracking interactions and upserting users/items.
  - `model_registry.py` – model version registration + lookup.
  - `cache_service.py` – Redis access and recommendation caching.

- **Training (`app/training/`)**
  - `data_prep.py` – utilities for building matrices / DataFrames.
  - `eval.py` – implementations of Recall@K, NDCG@K.
  - `train.py` – CLI + functions to train content and MF models.

- **Scripts (`scripts/`)**
  - `download_movielens_1m.py` – dataset downloader with manual fallback.
  - `seed_db.py` – parse MovieLens 1M and insert into Postgres.
  - `smoke_test_api.py` – quick health/recommendation smoke test.

---

## Runtime Flows

### 1. Request / Response

1. Client sends HTTP request (e.g. `GET /v1/recommendations?user_id=123&strategy=content`).
2. `logging_middleware`:
   - generates or propagates `request_id`
   - logs `request_start`
3. Router handler:
   - Obtains a DB session via dependency injection.
   - Selects recommender (popular/content/mf).
   - Recommender may:
     - query the DB (items/interactions)
     - fetch or store results in Redis
     - load model artifacts from disk
4. Response is returned with consistent schema and `request_id`.
5. Middleware logs `request_end` with latency.

### 2. Training Flow

1. Data is downloaded by `scripts/download_movielens_1m.py`.
2. `scripts/seed_db.py` loads MovieLens data into Postgres.
3. Admin triggers training via:
   - `POST /v1/admin/train?model=content`
   - `POST /v1/admin/train?model=mf`
4. `app.training.train`:
   - Reads data from Postgres.
   - Trains the model.
   - Writes artifacts under `artifacts/`.
   - Registers a row in `model_versions`.
5. Online recommenders read **only active** `model_versions` + artifacts.

---

## Deployment Model

- **Local dev**
  - `docker-compose up` runs:
    - API (FastAPI + Uvicorn)
    - Postgres
    - Redis
  - Environment configured via `.env`.

- **Production (HF Spaces + Supabase + Upstash)**
  - Same Docker image as local.
  - Environment variables:
    - `DATABASE_URL` – Supabase Postgres URL.
    - `REDIS_URL` – Upstash Redis URL.
  - No code differences; only configuration changes.

---

## Extension Points

- New recommenders can be added in `app/recommenders/` and wired via:
  - `app/routers/recommend.py`
  - `model_versions` registry.
- Additional domains (e.g. products) can:
  - Reuse `users` and `interactions`.
  - Add domain-specific fields on `items.metadata`.
- Future A/B testing:
  - New tables / models (e.g. `experiments`, `assignments`).
  - Request routing based on experiment assignment before calling recommenders.