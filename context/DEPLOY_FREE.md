# Deploying RecAI for Free

This guide describes how to deploy the RecAI MVP on **100% free-tier
infrastructure**:

- **Hugging Face Space (Docker runtime)** – runs the FastAPI API container.
- **Supabase Postgres** – persistent database for users, items, interactions, and model metadata.
- **Upstash Redis** – managed Redis for caching and popularity signals.

It focuses on **step-by-step, click-by-click** instructions, including environment variables,
verification, and common issues.

For more general deployment notes, also see:

- `context/DEPLOYMENT.md` (original deployment guide)


---

## 1. Architecture recap

High-level view of the free deployment:

```text
                 +----------------------------+
                 |      Client / Integrator   |
                 | (web app, backend, mobile) |
                 +--------------+-------------+
                                |
                                v   HTTPS (Space URL)
                      +---------+----------+
                      | Hugging Face Space |
                      |   (Docker runtime) |
                      +---------+----------+
                                |
                                | DATABASE_URL
                                v
                       +--------+--------+
                       |   Supabase      |
                       |   Postgres DB   |
                       +-----------------+

                                ^
                                |
                                | REDIS_URL
                                v
                      +---------+---------+
                      |    Upstash       |
                      |     Redis        |
                      +------------------+
```

- The **Space** runs the API container built from `docker/Dockerfile`.
- The container connects to:
  - **Supabase Postgres** via `DATABASE_URL`
  - **Upstash Redis** via `REDIS_URL`
- All three are on **free tiers**.


---

## 2. Supabase setup (free Postgres)

### 2.1 Create a Supabase project

1. Go to <https://supabase.com/> and sign in (GitHub login is common).
2. Click **New project**.
3. Choose:
   - A **project name**
   - A **strong database password**
   - A **region** close to your expected users
4. Click **Create new project** and wait for provisioning to finish.

---

### 2.2 Get the connection string

1. In your Supabase project, go to:

   - **Project Settings → Database → Connection string**

2. Supabase offers several connection string formats and “pooler” modes.  
   For best compatibility from cloud runtimes like Hugging Face Spaces:

   - Prefer the **“Pooler (Session)”** or **“Pooler (Transaction)”** connection strings.
   - These typically provide **IPv4-compatible** endpoints.

3. Choose the **Python** or **SQLAlchemy**-style URL, for example:

   ```text
   postgresql+psycopg2://postgres:<password>@db.<hash>.supabase.co:5432/postgres
   ```

   or (using the pooler):

   ```text
   postgresql+psycopg2://postgres.<project-id>:<password>@aws-0-<pooler>.supabase.co:6543/postgres
   ```

4. Copy this URL; you will paste it as `DATABASE_URL` in Hugging Face Space settings.

> **IPv6 note**
>
> Some *direct* database endpoints may be **IPv6-only**. If your runtime cannot
> reach IPv6, you might see connection errors.
>
> - Using a **Supavisor pooler** connection string (Session/Transaction) generally
>   provides **IPv4-compatible** endpoints.
> - If you hit unexplained connection issues, switch to a pooler connection string.

---

### 2.3 Free-tier pause behaviour

On the free tier, Supabase will **pause your database** after a period of inactivity
(typically around a week).

- When paused, the first API calls from your Space may:
  - Time out
  - Return connection errors

To wake the DB:

- Open the Supabase dashboard – this usually resumes the database.
- Or hit the `/health` endpoint of your Space and then **retry after a short delay**.

> Optional idea (not built into this repo):  
> You can schedule a lightweight weekly `curl` to your Space `/health` endpoint
> (e.g. from GitHub Actions or a cronjob) to reduce the chance of cold starts.
> This is **not required** and should be done outside this repository if desired.


---

## 3. Upstash Redis setup (free Redis)

### 3.1 Create an Upstash Redis database

1. Go to <https://upstash.com/> and log in.
2. Click **Redis → Create database**.
3. Choose:
   - **Region** (ideally close to your Supabase region)
   - Free-tier plan
4. Create the database.

---

### 3.2 Get the Redis URL

1. In your Upstash Redis database page, find the **“Connect”** section.
2. Copy the **public Redis URL**, which usually looks like:

   ```text
   rediss://:<password>@<host>:<port>/0
   ```

   or:

   ```text
   redis://:<password>@<host>:<port>/0
   ```

3. Use this value as `REDIS_URL` in your Space.

Notes:

- Upstash often defaults to **TLS-enabled (`rediss://`)** URLs – these are supported.
- Always use the URL shown in the **“Connect”** section, not a private/internal address.


---

## 4. Hugging Face Space setup (Docker, free CPU)

### 4.1 Create the Space

1. Go to <https://huggingface.co/spaces>.
2. Click **New Space**.
3. Fill in:
   - **Owner**: your username or org
   - **Space name**: e.g. `recai-movielens`
   - **Visibility**: Public (or Private, if desired)
   - **Hardware**: `cpu-basic` (free tier)
4. For **SDK**, choose **Docker**.
5. Click **Create Space**.

You now have an empty Docker-based Space.

---

### 4.2 Connect the repo to the Space

You have two main options:

#### Option A – Push from local

1. Add the Space as a remote:

   ```bash
   git remote add space https://huggingface.co/spaces/<user>/recai-movielens
   ```

2. Push your current branch (the one containing this code):

   ```bash
   git push space HEAD:main
   ```

Hugging Face will:

- Build the Docker image using `docker/Dockerfile`.
- Run the container with `docker/entrypoint.sh`.

#### Option B – Use GitHub integration

1. In the Space page, open the **Settings** tab.
2. Under **Repository**, connect your GitHub repo.
3. Ensure:
   - The **Docker runtime** is selected.
   - The repo contains `docker/Dockerfile`.

Each push to the linked branch will trigger a new build.

---

### 4.3 Ensure Space metadata is correct (YAML)

The Space will have a README with a small YAML front matter block.  
Make sure it includes:

```yaml
---
sdk: docker
app_port: 7860
---
```

- `sdk: docker` – tells Hugging Face to use the Docker runtime.
- `app_port: 7860` – indicates the Space listens on port **7860**.

Our Docker entrypoint respects the `PORT` environment variable and defaults
to `7860` when it is not set.

---

### 4.4 Configure environment variables (Variables vs Secrets)

In your Space:

1. Go to the **Settings** tab.
2. Open **Variables and secrets**.

You will see two sections:

- **Environment variables** (non-secret)
- **Secrets** (hidden values)

Recommended usage:

- **Secrets**:
  - `DATABASE_URL` – Supabase Postgres URL
  - `REDIS_URL` – Upstash Redis URL
- **Environment variables** (non-secret):
  - `ENV=prod`
  - `LOG_LEVEL=INFO`
  - `PORT=7860` (optional; defaults to 7860 if omitted)
  - `AUTO_TRAIN_ON_BOOT=true` (recommended – see below)

Add the following entries:

**Secrets**

- `DATABASE_URL` = `postgresql+psycopg2://postgres:<password>@.../postgres`
- `REDIS_URL`    = `rediss://:<password>@.../0` (or `redis://...` as given by Upstash)

**Environment variables**

- `ENV`                  = `prod`
- `LOG_LEVEL`            = `INFO`
- `PORT`                 = `7860`  (ensures Uvicorn listens on the expected port)
- `AUTO_TRAIN_ON_BOOT`   = `true`  (see section 5)

You can also optionally set:

- `RATE_LIMIT_ENABLED`          = `true` or `false`
- `RATE_LIMIT_REQUESTS_PER_MIN` = e.g. `120`

After saving changes, the Space will usually **restart automatically**.
You can also trigger a manual restart from the Space UI.


---

## 5. Ephemeral storage and model artifacts

### 5.1 The problem

Hugging Face Spaces’ filesystem is **ephemeral**:

- Docker containers can be **recreated** on redeploys or hardware changes.
- Files under `artifacts/` (model files) and any cached data can be lost.
- Your **database** (Supabase) and **Redis** (Upstash) remain persistent.

We therefore need a strategy to ensure models are available after a restart.

---

### 5.2 This repo’s approach: AUTO_TRAIN_ON_BOOT

This repo implements a lightweight **auto-training on startup** mechanism,
controlled by the `AUTO_TRAIN_ON_BOOT` environment variable.

**How it works**

1. On application startup (`app/main.py`), a startup hook calls:

   ```python
   ensure_models_trained_if_missing()
   ```

   from `app.services.auto_train`.

2. That function:

   - Checks for an **active model version** in the `model_versions` table for:
     - `content_tfidf`
     - `mf_als`
   - For each active model:
     - Verifies that the model artifact file exists (e.g. `artifacts/content_tfidf.pkl`).
   - If **no active version** or **artifact file is missing**, it:
     - Calls the corresponding training function from `app.training.train`:
       - `train_content_model(db)`
       - `train_mf_model(db)`

3. Training behaviour:

   - Reads interactions from **Supabase Postgres**.
   - Trains the model.
   - Writes a new artifact file under `ARTIFACT_DIR` (default: `artifacts/`).
   - Registers a new row in `model_versions`.

4. Errors during training are **logged but do not crash startup**:
   - If training fails, the app still starts and continues to serve:
     - `strategy=popular` normally.
     - `strategy=content`, `strategy=mf`, and `strategy=hybrid` will gracefully **fall back**
       to popularity when models are unavailable.

> Set `AUTO_TRAIN_ON_BOOT=true` in the Space to enable this behaviour.

---

### 5.3 Requirements for auto-training to succeed

Auto-training assumes:

1. The **database schema exists** (Alembic migrations ran successfully).
   - `docker/entrypoint.sh` already runs:
     ```bash
     alembic upgrade head || echo "Alembic migrations failed or not configured; continuing."
     ```

2. The database is **seeded with interactions** (e.g. MovieLens 1M):
   - You must **seed once** (locally or inside the Space), so that:
     - `users`, `items`, and `interactions` contain data.
   - After that, auto-training can run on each restart when artifacts are missing.

If there is no data in `interactions`, auto-training will log a warning and
return without providing MF/content models. The API still works with `popular`.

---

### 5.4 Alternative: External artifact storage (optional, not implemented)

Another common pattern is to:

- Upload `artifacts/` files to an **HF Dataset repo** or similar,
- Then download them in `docker/entrypoint.sh` if missing.

This repo does **not** implement that to keep the setup simple and 100% free
without adding extra services. If you need this, you can:

- Extend the entrypoint to `wget` artifacts from a public URL.
- Ensure the `model_versions.path` fields point to valid paths inside the container.


---

## 6. Seeding data and training models (once)

You have two main workflows: **local precomputation** or **in-Space seeding**.
The existing `context/DEPLOYMENT.md` explains both; here is a concise version.

### 6.1 Option A – Precompute locally and reuse DB only

In this option, you run seed + train **against Supabase** from your local machine:

1. On your local dev environment, set:

   ```bash
   export DATABASE_URL="postgresql+psycopg2://postgres:<password>@db.<hash>.supabase.co:5432/postgres"
   ```

2. Run migrations:

   ```bash
   alembic upgrade head
   ```

3. Download MovieLens data locally:

   ```bash
   python scripts/download_movielens_1m.py
   ```

4. Seed Supabase:

   ```bash
   python scripts/seed_db.py
   ```

5. Train models **against Supabase**:

   ```bash
   python -m app.training.train --model content
   python -m app.training.train --model mf
   ```

Now Supabase contains:

- Users, items, interactions
- Model metadata in `model_versions`

On the Space:

- Set `DATABASE_URL` to the **same Supabase URL**.
- Set `AUTO_TRAIN_ON_BOOT=true` so that if artifacts are missing on a restart,
  the Space can retrain from Supabase data.

---

### 6.2 Option B – Seed and train inside the Space

Alternatively, you can run everything **inside the Space container**:

1. In your Space page, open the **“Logs”** panel.
2. Click **“Open in HF Spaces shell”** or similar (terminal access).
3. From the shell:

   ```bash
   python scripts/download_movielens_1m.py
   python scripts/seed_db.py
   python -m app.training.train --model content
   python -m app.training.train --model mf
   ```

This uses:

- `DATABASE_URL` from the Space environment (Supabase)
- Local `ARTIFACT_DIR` inside the Space container (`artifacts/`)

On subsequent restarts, if artifacts vanish, `AUTO_TRAIN_ON_BOOT=true` will
retrain them from Supabase as needed.


---

## 7. Verification checklist

Once the Space build succeeds and the container is running:

Let’s assume your Space URL is:

```text
https://<your-space-subdomain>.hf.space
```

The actual **API URL** will be the same subdomain:

```text
https://<your-space-subdomain>.hf.space
```

(adjust to match your Space’s public URL, which Hugging Face shows in the UI).

### 7.1 Health endpoint

```bash
curl https://<your-space-subdomain>.hf.space/health
```

Expected JSON:

```json
{
  "status": "ok",
  "env": "prod",
  "version": "0.1.0",
  "request_id": "..."
}
```

---

### 7.2 Stats endpoint

```bash
curl https://<your-space-subdomain>.hf.space/v1/stats
```

You should see counts for users/items/interactions. If they are zero,
you likely haven’t seeded Supabase yet.

---

### 7.3 Recommendations

Once data and models are in place:

```bash
curl "https://<your-space-subdomain>.hf.space/v1/recommendations?user_id=1&strategy=hybrid"
```

You should see:

- `"user_id": 1`
- `"strategy": "hybrid"`
- `"items": [...]` – non-empty list of recommended items
- Each item with:
  - `id`, `title`, `score`, `strategy`, `reasons`

If models are missing or training failed, `hybrid` will fall back to `popular`,
but you should still see reasonable items.

---

### 7.4 Metrics and dashboard

Metrics:

```bash
curl https://<your-space-subdomain>.hf.space/metrics
```

You should see Prometheus-like text including:

- `recai_request_count`
- `recai_error_count`
- `recai_cache_hit_count`
- `recai_latency_ms_bucket{...}`

Dashboard:

- Open in a browser:

  ```text
  https://<your-space-subdomain>.hf.space/dashboard
  ```

You should see a basic HTML dashboard summarizing entity counts and experiment info.


---

## 8. Common deployment issues & fixes

### 8.1 Wrong port (must be 7860)

Symptoms:

- Space appears to build but returns connection errors.
- Logs show Uvicorn listening on a different port.

Checklist:

1. Ensure Space README YAML specifies:

   ```yaml
   sdk: docker
   app_port: 7860
   ```

2. In **Variables and secrets**, set:

   ```text
   PORT=7860
   ```

3. Confirm logs show something like:

   ```text
   Uvicorn running on http://0.0.0.0:7860
   ```

---

### 8.2 Missing or incorrect env vars

Symptoms:

- Startup errors about missing `DATABASE_URL` or `REDIS_URL`.
- Runtime errors on DB or Redis connection.

Checklist:

1. In the Space’s **Settings → Variables and secrets**:

   - Confirm `DATABASE_URL` (Secret) exists and matches Supabase.
   - Confirm `REDIS_URL` (Secret) exists and matches Upstash.
   - Confirm `ENV=prod` and `LOG_LEVEL=INFO` in Variables.

2. Save changes and restart the Space.

---

### 8.3 Supabase paused or unreachable

Symptoms:

- Connection timeouts on first requests.
- Logs mention connection failures to the Postgres host.

Fix:

1. Open Supabase dashboard for your project.
2. Wait until the DB shows as **Running**.
3. Retry `/health` and `/v1/stats` on your Space.
4. If issues persist, confirm that:
   - You are using a **pooler** connection string (Session/Transaction).
   - `DATABASE_URL` matches the string from **Project Settings → Database → Connection string**.

---

### 8.4 Redis TLS / URL mismatch

Symptoms:

- Errors like `Error connecting to Redis` in logs.
- Space runs, but caching fails.

Checklist:

1. In Upstash, confirm the **Connect** URL (e.g. `rediss://...`).
2. In your Space:
   - Set `REDIS_URL` **exactly** to that value.
3. Restart the Space and check logs.

Note:

- If you change the Redis URL, existing caches are discarded; this is fine for the MVP.

---

### 8.5 Space build failures

If the Space fails to build:

1. Open your Space page.
2. Click the **“Build”** tab (or **“Logs”** / **“Runtime”** depending on UI).
3. Look for:
   - Docker build errors (e.g. missing dependencies in `requirements.txt`).
   - Network issues during `pip install`.

Typical checks:

- Ensure `docker/Dockerfile` and `requirements*.txt` are committed.
- If the error refers to a missing file, verify the file path in the repo.

Re-push your branch or click **“Restart”** in the Space UI after fixing issues.

---

### 8.6 Database migrations not applied

Symptoms:

- Runtime errors like `relation "users" does not exist`.
- `/v1/stats` fails due to missing tables.

By default, `docker/entrypoint.sh` runs:

```bash
alembic upgrade head || echo "Alembic migrations failed or not configured; continuing."
```

If migrations fail:

1. Open the Space logs and search for `Alembic`.
2. Common causes:
   - `DATABASE_URL` is wrong or empty.
   - Supabase is not reachable.
3. Fix `DATABASE_URL` and any network issues.
4. Restart the Space so `alembic upgrade head` runs again.

If needed, you can also run migrations manually from the Space shell:

```bash
alembic upgrade head
```

---

### 8.7 Auto-training issues

If you’ve set `AUTO_TRAIN_ON_BOOT=true` but models are still missing:

1. Check the Space logs around startup:
   - Look for messages like `Auto-train: training content_tfidf model on startup...`.
   - Look for warnings about no interactions or failed training.

2. Verify Supabase has data:
   - Locally or via a SQL editor:
     ```sql
     SELECT COUNT(*) FROM interactions;
     ```
   - If zero, you need to seed the DB (`scripts/seed_db.py`).

3. If training fails, the app will still start and serve `popular` recommendations.  
   Fix the underlying issue (e.g. connectivity, data) and restart the Space.

---

With Supabase, Upstash, and a Docker Space configured as above, you get a
**fully free**, production-style deployment of RecAI with:

- Persistent data in Supabase,
- Caching and popularity metrics in Upstash Redis,
- Automatic model training on startup when artifacts are missing,
- And FastAPI serving traffic via Hugging Face Spaces.