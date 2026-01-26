# RecAI – Multi-Domain Personalization Engine (MVP)

RecAI is a **free-first, production-grade recommendation API** designed for deployment on
**Hugging Face Docker Spaces**. The MVP targets the MovieLens 1M dataset, but the architecture
is general enough to support other domains (products, articles, etc.).

---

## Features

- **FastAPI** + **Uvicorn** API
- **Postgres** (Supabase in prod) + **SQLAlchemy 2.0** + **Alembic**
- **Redis** (Upstash in prod) for caching per-user recommendations
- Recommenders:
  - Popular / Trending baseline
  - Content-based TF‑IDF similarity
  - Matrix factorization using `implicit` ALS
- Model artifacts stored under `artifacts/` (gitignored) with metadata in Postgres
- Structured logging, global error handling, type hints
- Docker + docker-compose for local dev
- GitHub Actions CI:
  - `ruff` lint
  - `pytest` tests
- EDA + evaluation notebook for MovieLens 1M

---

## Quickstart (Local Development)

### 1. Clone and install

```bash
git clone <this-repo>
cd recai-personalization-engine

cp .env.example .env   # adjust if needed
make install-dev
```

### 2. Start services with docker-compose

```bash
docker-compose up --build
```

This will start:

- `api` (FastAPI + Uvicorn)
- `postgres`
- `redis`

The API should be available at `http://localhost:8000`.

### 3. Download MovieLens 1M

In another terminal:

```bash
python scripts/download_movielens_1m.py
```

If the download fails (e.g. firewall restrictions), the script will print instructions
for manually placing `ml-1m.zip` into `data/raw/`.

### 4. Seed the database

```bash
python scripts/seed_db.py
```

This will:

- Create tables (if not already present).
- Insert users, items, and interactions from MovieLens 1M.

### 5. Train models (MVP)

Content-based TF‑IDF:

```bash
python -m app.training.train --model content
```

Matrix factorization (ALS):

```bash
python -m app.training.train --model mf
```

Alternatively, you can use the admin API:

```bash
curl -X POST "http://localhost:8000/v1/admin/train?model=content"
curl -X POST "http://localhost:8000/v1/admin/train?model=mf"
```

---

## API Overview

### Health

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "ok",
  "env": "local",
  "version": "0.1.0",
  "request_id": "..."
}
```

### Stats

```bash
curl http://localhost:8000/v1/stats
```

### Get Item

```bash
curl http://localhost:8000/v1/items/1
```

### Similar Items (content-based)

```bash
curl "http://localhost:8000/v1/items/1/similar?limit=20"
```

### Recommendations

```bash
# Popular baseline
curl "http://localhost:8000/v1/recommendations?user_id=1&strategy=popular"

# Content-based
curl "http://localhost:8000/v1/recommendations?user_id=1&strategy=content"

# Matrix factorization (ALS)
curl "http://localhost:8000/v1/recommendations?user_id=1&strategy=mf"
```

Responses follow this general shape:

```json
{
  "user_id": 1,
  "strategy": "popular",
  "items": [
    {
      "id": 50,
      "title": "Star Wars (1977)",
      "score": 1234.0,
      "strategy": "popular",
      "reason": "Popular item with 1234 interactions"
    }
  ],
  "request_id": "..."
}
```

### Track Interactions

For now, `POST /v1/track` simply records interactions:

```bash
curl -X POST "http://localhost:8000/v1/track" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "item_id": 50, "event_type": "view"}'
```

---

## Configuration

Configuration is handled by `pydantic-settings` in `app/core/config.py`.

Key environment variables:

- `ENV` – `local` | `test` | `dev` | `prod`
- `LOG_LEVEL` – e.g. `INFO`, `DEBUG`
- `PORT` – API port (default: `8000`)
- `DATABASE_URL` – SQLAlchemy Postgres URL
- `REDIS_URL` – Redis URL
- `DATA_DIR` – base data directory (default: `data`)
- `ARTIFACT_DIR` – model artifacts directory (default: `artifacts`)

See `.env.example` for a template.

---

## Repo Structure

```text
.
├─ app/
│  ├─ main.py
│  ├─ core/
│  ├─ db/
│  ├─ routers/
│  ├─ recommenders/
│  ├─ services/
│  ├─ training/
│  └─ utils/
├─ notebooks/
│  └─ 01_movielens_eda_and_eval.ipynb
├─ scripts/
├─ tests/
├─ context/
├─ docker/
├─ docker-compose.yml
├─ .env.example
├─ requirements*.txt
├─ pyproject.toml
└─ .github/workflows/ci.yml
```

---

## Hugging Face Spaces (Docker) – High-Level Deployment

The target deployment is a **Hugging Face Space** using the **Docker** runtime:

1. Build a Docker image using `docker/Dockerfile`.
2. Ensure environment variables are set in the Space:
   - `DATABASE_URL` (Supabase)
   - `REDIS_URL` (Upstash)
   - `DATA_DIR` (if using attached storage)
   - `ARTIFACT_DIR`
3. Point the Space to run `docker/entrypoint.sh` as its entrypoint.
4. Pre-train models and upload artifacts (or train in the Space on startup, if feasible).

Further details (e.g. initialization strategies, health checks, experiments) will be covered in
a follow-up prompt.

---

## Roadmap (Coming Next)

- A/B testing and experiment tracking.
- Improved cold-start handling.
- More advanced models and hybrid recommenders.
- Better observability: metrics and tracing.

For architectural details and decisions, see the `context/` folder:
- `context/GOAL.md`
- `context/ARCHITECTURE.md`
- `context/DECISIONS.md`
- `context/METRICS.md`