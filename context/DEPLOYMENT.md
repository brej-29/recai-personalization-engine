# Deployment Guide – Hugging Face Spaces (Docker) + Free Infra

This document describes how to deploy the RecAI MVP to **Hugging Face Spaces (Docker)**  
using a **free-first** infrastructure stack:

- **Supabase Postgres** for `DATABASE_URL`
- **Upstash Redis** for `REDIS_URL`
- **Hugging Face Space (Docker runtime)** for the API container

---

## 1. Prerequisites

- GitHub account with access to this repository.
- Hugging Face account.
- Supabase account (free tier).
- Upstash account (free tier).

---

## 2. Create a Supabase Project (Postgres)

1. Go to <https://supabase.com> and create a new project.
2. Wait for provisioning to complete.
3. In the Supabase dashboard:
   - Navigate to **Project Settings → Database**.
   - Copy the **connection string** in a form suitable for SQLAlchemy, for example:

     ```text
     postgresql+psycopg2://postgres:<password>@db.<hash>.supabase.co:5432/postgres
     ```

4. This value will be used as `DATABASE_URL` (or `SUPABASE_DATABASE_URL` in `.env`).

> **Note:** Supabase free tier databases are paused after some period of inactivity  
> (around 1 week). When this happens, the first request to the API may time out.  
> To wake it up:
>
> - Open the Supabase dashboard (which wakes the DB), or
> - Hit the `/health` endpoint of your Space and retry after a short delay.

---

## 3. Create an Upstash Redis Database

1. Go to <https://upstash.com> and create a new Redis database (free tier is enough).
2. In the database page, copy the **public Redis URL**, e.g.:

   ```text
   redis://:<password>@eu1-foo-bar.upstash.io:6379/0
   ```

3. This will be used as `REDIS_URL` (or `UPSTASH_REDIS_URL` in `.env`).

Redis is used for:

- Per-user recommendation caching.
- Simple popularity / trending counters.

The system is **best-effort**: if Redis is unreachable, the API continues to serve responses.

---

## 4. Prepare the Repository

Clone the repo locally:

```bash
git clone <this-repo>
cd recai-personalization-engine
```

The key files for deployment:

- `docker/Dockerfile` – Docker image definition.
- `docker/entrypoint.sh` – Runs Alembic migrations and starts Uvicorn.
- `app/main.py` – FastAPI application.
- `context/DEPLOYMENT.md` – this guide.

---

## 5. Environment Variables

The application uses `pydantic-settings` (`app/core/config.py`) and reads from `.env` / environment.

For **local development**, `.env.example` provides sane defaults.

For **Hugging Face Spaces**, you will set variables in the Space settings instead:

Minimum variables:

- `DATABASE_URL` – Supabase Postgres URL.
- `REDIS_URL` – Upstash Redis URL.
- `ENV` – set to `prod`.
- `LOG_LEVEL` – e.g. `INFO`.

Optional:

- `DATA_DIR` – directory for raw data (default: `data`).
- `ARTIFACT_DIR` – directory for model artifacts (default: `artifacts`).
- `RATE_LIMIT_ENABLED` – `true` / `false` (simple per-IP rate limiting).
- `RATE_LIMIT_REQUESTS_PER_MIN` – integer, e.g. `60`.

Example configuration for HF Spaces:

```text
ENV=prod
DATABASE_URL=postgresql+psycopg2://postgres:<password>@db.<hash>.supabase.co:5432/postgres
REDIS_URL=redis://:<password>@eu1-foo-bar.upstash.io:6379/0
LOG_LEVEL=INFO
```

---

## 6. Create a Hugging Face Space (Docker Runtime)

1. Go to <https://huggingface.co/spaces> and click **Create new Space**.
2. Choose:
   - **SDK**: Docker
   - **Space name**: e.g. `your-username/recai-movielens`
   - **Visibility**: Public (or Private if you prefer)
3. After creation, in the Space settings:
   - Under **Variables and secrets**, add the environment variables from the previous step.
   - Ensure no credentials are committed to the repo.

The Docker runtime automatically sets a `PORT` environment variable, defaulting to `7860`.  
The provided Dockerfile and entrypoint respect this:

- `docker/Dockerfile` exposes port `7860`.
- `docker/entrypoint.sh` starts:

  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-7860}"
  ```

No additional configuration is needed.

---

## 7. Connect the Repo to the Space

You have two options:

### Option A – Push from Local

1. Add the Hugging Face Space as a git remote:

   ```bash
   git remote add space https://huggingface.co/spaces/<user>/recai-movielens
   ```

2. Push the branch containing the MVP:

   ```bash
   git push space HEAD:main
   ```

The Space will build the Docker image using `docker/Dockerfile` and start the container.

### Option B – Use GitHub Integration

Hugging Face Spaces can also mirror a GitHub repo.  
Follow the HF docs to connect your GitHub repository to the Space.  
Ensure the Docker runtime is selected so `docker/Dockerfile` is used.

---

## 8. Database Migrations and Startup

On container startup, the entrypoint runs:

```bash
alembic upgrade head || echo "Alembic migrations failed or not configured; continuing."
uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-7860}"
```

That means:

- All Alembic migrations in `app/db/migrations/` are applied to your Supabase database.
- If migrations fail (e.g. first-time misconfiguration), the API still attempts to start,
  but you may see errors when hitting endpoints that rely on DB tables.

If you change models/migrations, the next deployment will run `alembic upgrade head` again.

---

## 9. Seeding Data and Training Models

For the MovieLens 1M MVP, you can either:

### Option A – Precompute Locally and Upload Artifacts

1. Run the scripts locally against a local Postgres:

   ```bash
   python scripts/download_movielens_1m.py
   python scripts/seed_db.py
   python -m app.training.train --model content
   python -m app.training.train --model mf
   ```

2. Copy the `artifacts/` directory that was produced into the repo or into an attached volume for the Space.
3. Ensure the `model_versions` table is populated (via local training) and that `path` fields
   point to locations available in the container (e.g. `/app/artifacts/...`).

### Option B – Seed and Train Inside the Space

This is feasible for MovieLens 1M but costs some startup time:

1. Open a Space **shell** or build an admin-only script/notebook in the Space.
2. Run:

   ```bash
   python scripts/download_movielens_1m.py
   python scripts/seed_db.py
   python -m app.training.train --model content
   python -m app.training.train --model mf
   ```

3. After training, the active model versions will be stored in Postgres and artifacts under `ARTIFACT_DIR`.

---

## 10. Verifying the Deployment

Once the Space is built and running:

1. Hit the health endpoint:

   ```bash
   curl https://<space-URL>/health
   ```

   You should see a JSON response like:

   ```json
   {
     "status": "ok",
     "env": "prod",
     "version": "0.1.0",
     "request_id": "..."
   }
   ```

2. Check basic stats:

   ```bash
   curl https://<space-URL>/v1/stats
   ```

3. Request recommendations (after seeding/training):

   ```bash
   curl "https://<space-URL>/v1/recommendations?user_id=1&strategy=hybrid"
   ```

4. Inspect monitoring:

   - Prometheus-style metrics: `https://<space-URL>/metrics`
   - Basic dashboard: `https://<space-URL>/dashboard`

---

## 11. Free-Tier Caveats

- **Supabase**: database may sleep after ~1 week of inactivity.  
  First request after wake-up can be slow or fail; retry after a short delay.
- **Upstash Redis**: has request and memory limits on free tier.  
  The RecAI MVP is designed to fail gracefully if Redis is unavailable.
- **HF Spaces**: free hardware has limited CPU/RAM.  
  Avoid very large models; the provided MF + TF-IDF setup is tuned for MovieLens 1M.

---

## 12. Operational Tips

- Set `LOG_LEVEL=INFO` in production; use `DEBUG` only transiently.
- Consider enabling simple rate limiting:

  ```text
  RATE_LIMIT_ENABLED=true
  RATE_LIMIT_REQUESTS_PER_MIN=120
  ```

- Use the `/v1/admin/models` endpoint to inspect active model versions.
- Use the A/B testing endpoints:

  - `POST /v1/admin/experiments/create`
  - `GET /v1/admin/experiments`
  - `GET /v1/admin/experiments/hybrid_vs_popular/report`

These give you a thin but real **production-style** story for deploying RecAI to free infrastructure.