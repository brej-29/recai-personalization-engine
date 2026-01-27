# Running RecAI locally

This guide walks through a **frictionless local setup** on:

- **Windows 11 (PowerShell)** – primary focus
- **macOS / Linux (bash)**

You’ll run:

- **FastAPI API** on your host machine (Uvicorn)
- **Postgres + Redis** via **Docker Compose**
- Optional helpers via **Make** and `scripts/run_local.*`.

The commands below assume:

- **Python** 3.11
- You are in the **repository root** (where `README.md` lives).


---

## 1. What you need installed

### 1.1 Git

Used to clone and update the repository.

- Windows: install from <https://git-scm.com/download/win>
- macOS: `xcode-select --install` or install from <https://git-scm.com/download/mac>
- Linux: `sudo apt-get install git` (Debian/Ubuntu) or your distro’s package manager

---

### 1.2 Python 3.11

The project targets **Python 3.11** (see `pyproject.toml` / CI).

- Windows:
  - Install from <https://www.python.org/downloads/release/python-3110/>
  - Ensure **“Add Python to PATH”** is checked during setup.
  - Verify:

    ```powershell
    py --version
    python --version
    ```

- macOS / Linux:
  - Use your package manager or `pyenv`:
    ```bash
    python3.11 --version
    ```
  - If you see `Python 3.11.x`, you are good.

---

### 1.3 Docker Desktop (with WSL2 on Windows)

We use Docker Compose to run **Postgres** and **Redis** locally.

- Windows:
  - Install Docker Desktop from <https://www.docker.com/products/docker-desktop/>
  - In Docker Desktop settings, ensure the **WSL2 backend** is enabled.
  - Verify from PowerShell:
    ```powershell
    docker version
    docker compose version   # or: docker-compose --version
    ```

- macOS:
  - Install Docker Desktop (Apple Silicon or Intel) from Docker website.
  - Verify:
    ```bash
    docker version
    docker compose version   # or: docker-compose --version
    ```

- Linux:
  - Install Docker Engine + Compose plugin via your distro.
  - Verify as above.

> If `docker compose` is not available, you may have **Compose v1** as `docker-compose`.
> All docs below show both variants where relevant.

---

### 1.4 Make (optional, but recommended)

Make is used for **quality-of-life commands** (lint, test, up/down, etc.).

- Windows:
  - Install via **Chocolatey**:  
    ```powershell
    choco install make
    ```
  - Or use **Git for Windows SDK** / MSYS2’s `make`.

- macOS:
  - Installed with Xcode command line tools:
    ```bash
    xcode-select --install
    make --version
    ```

- Linux:
  - Usually available via package manager:
    ```bash
    sudo apt-get install make
    ```

> If you don’t have Make, you can always use the **raw commands** shown below.

---

### 1.5 VS Code (optional)

Recommended editor with good Python + Docker integrations.

- Download from <https://code.visualstudio.com/>
- Install **Python**, **Docker**, and **Pylance** extensions.

---

### 1.6 HTTP client: curl / Postman / browser

For quick checks:

- **Windows PowerShell**: `Invoke-RestMethod` is built-in; `curl` is often aliased.
- **macOS / Linux**: `curl` is preinstalled on most systems.
- GUI options: **Postman**, **Insomnia**, or your web browser for `/docs`, `/dashboard`.


---

## 2. Repo overview for local running

### 2.1 What runs locally

By default, local development runs:

- **FastAPI API** (Uvicorn) on your host:
  - Default base URL: `http://127.0.0.1:8000`
- **Postgres** (via Docker Compose) on:
  - `localhost:5432`
- **Redis** (via Docker Compose) on:
  - `localhost:6379`

Docker is only used for **Postgres + Redis**. The API runs in your **local Python** environment.

You can also run the API in Docker via `docker-compose.yml`, but this guide focuses on the **host API + Dockerized dependencies** flow.

---

### 2.2 Environment variables

Configuration is handled by `pydantic-settings` in `app/core/config.py`.

Key env vars:

- `ENV` – environment name (`local`, `test`, `dev`, `prod`)
- `LOG_LEVEL` – e.g. `INFO`, `DEBUG`
- `PORT` – API port (default `8000`)
- `DATABASE_URL` – Postgres SQLAlchemy URL
- `REDIS_URL` – Redis URL
- `DATA_DIR` – base data directory (default `data`)
- `ARTIFACT_DIR` – model artifact directory (default `artifacts`)
- `AUTO_TRAIN_ON_BOOT` – if `true`, train content + MF models on startup when artifacts are missing (used mainly for HF Spaces; optional for local)

The default local `.env` file is:

- **Template**: `.env.example`
- **Your local file**: `.env` (not committed)

For **host-based local dev**, `.env.example` is already configured to use:

```text
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/recai
REDIS_URL=redis://localhost:6379/0
```

Docker Compose overrides these inside the `api` container so it can talk to `postgres`/`redis` services by name.

---

## 3. Step-by-step – Windows 11 (PowerShell)

This section assumes:

- You have **Python 3.11**, **Docker Desktop**, and optionally **Make** installed.
- You are running commands in **Windows PowerShell**, from the repo root.

### 3.1 Clone the repository

```powershell
git clone <your-fork-or-clone-url>
cd recai-personalization-engine
```

---

### 3.2 Create and activate a virtual environment

Use the Windows launcher to create a `.venv` with Python 3.11:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Verify Python:

```powershell
python --version
# Should print Python 3.11.x
```

---

### 3.3 Install dependencies

Install runtime + dev dependencies into the virtualenv:

```powershell
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

If you don’t need dev tooling, you can skip `requirements-dev.txt`.

---

### 3.4 Create your `.env`

Copy the example file:

```powershell
copy .env.example .env
```

For **local host-based development**, the defaults are already correct:

```text
ENV=local
LOG_LEVEL=INFO
PORT=8000

DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/recai
REDIS_URL=redis://localhost:6379/0
DATA_DIR=data
ARTIFACT_DIR=artifacts
```

You usually do **not** need to change these for local development. They assume:

- Postgres is listening on `localhost:5432`
- Redis is listening on `localhost:6379`  
  (exposed from Docker containers via `docker compose`)

> If you later run the API inside Docker instead of on the host, **do not** change `.env` – `docker-compose.yml` overrides the hostnames for the `api` container.

---

### 3.5 Start Postgres + Redis with Docker Compose

From the repo root:

```powershell
# Compose v2 (Docker Desktop default)
docker compose up -d postgres redis

# If you only have Compose v1:
# docker-compose up -d postgres redis
```

This will:

- Start a **Postgres 16** container with database `recai`
- Start a **Redis 7** container
- Expose ports:

  - Postgres: `localhost:5432`
  - Redis: `localhost:6379`

You can verify containers:

```powershell
docker ps
```

Look for `postgres` and `redis` services.

---

### 3.6 Run database migrations

Apply Alembic migrations so the database has all required tables:

```powershell
alembic upgrade head
```

Or using Make:

```powershell
make migrate
```

This uses `alembic.ini` at the repo root and `DATABASE_URL` from `.env`.

---

### 3.7 Download the MovieLens 1M dataset

```powershell
python scripts/download_movielens_1m.py
```

- On success, data will be under:

  ```text
  data/raw/ml-1m/
    users.dat
    movies.dat
    ratings.dat
  ```

- If the download is blocked (e.g. corporate firewall), the script will print:

  - The source URL: `https://files.grouplens.org/datasets/movielens/ml-1m.zip`
  - The expected location: `data/raw/ml-1m.zip`

  In that case:

  1. Manually download `ml-1m.zip` in your browser.
  2. Place it at `data/raw/ml-1m.zip`.
  3. Re-run:

     ```powershell
     python scripts/download_movielens_1m.py
     ```

---

### 3.8 Seed the database

Populate Postgres with users, items, and interactions from MovieLens 1M:

```powershell
python scripts/seed_db.py
```

You should see logs like:

```text
[INFO] Seeding DB at postgresql+psycopg2://postgres:postgres@localhost:5432/recai
[INFO] Using data directory data
[INFO] Seeding users...
[INFO] Seeding items...
[INFO] Seeding interactions (ratings)...
[OK] Seeding complete.
```

> The script is **not** intended to be run repeatedly against the same
> database. To re-seed, reset the Postgres volume (see Troubleshooting).

---

### 3.9 Train models (content + MF)

Train the **content-based TF‑IDF model**:

```powershell
python -m app.training.train --model content
```

Train the **matrix factorization (ALS) model**:

```powershell
python -m app.training.train --model mf
```

Expected behaviour:

- Artifacts are created under `artifacts/` (gitignored):

  ```text
  artifacts/
    content_tfidf.pkl
    mf_als.pkl
  ```

- Each run registers a row in the `model_versions` table with metrics.
- CLI prints lines like:

  ```text
  Training successful: TrainingResult(success=True, message='Content model trained', ...)
  ```

If you skip training:

- `strategy=popular` still works.
- `strategy=content`, `strategy=mf`, and `strategy=hybrid` will fall back
  to popularity when models are missing.

---

### 3.10 Run the API (Uvicorn)

From the repo root (venv active):

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- Base URL: `http://127.0.0.1:8000`
- Interactive docs: `http://127.0.0.1:8000/docs`
- Dashboard: `http://127.0.0.1:8000/dashboard`
- Metrics: `http://127.0.0.1:8000/metrics`

> If you prefer, you can also use:
>
> ```powershell
> make run
> ```

---

### 3.11 Smoke test (PowerShell)

With the API running:

```powershell
# Health check
Invoke-RestMethod http://127.0.0.1:8000/health

# Popular recommendations for user 1
Invoke-RestMethod "http://127.0.0.1:8000/v1/recommendations?user_id=1&limit=10&strategy=popular"
```

You should see JSON responses with:

- `"status": "ok"` for `/health`
- `"items": [...]` list for `/v1/recommendations`

To run the built-in Python smoke test:

```powershell
python scripts/smoke_test_api.py
```

---

### 3.12 Run tests

```powershell
pytest
# Or:
make test
```

---

### 3.13 Lint and format

```powershell
# Ruff lint
ruff check .

# Ruff formatter (auto-format)
ruff format .

# Or:
make lint
make fmt
```

---

### 3.14 Run the notebook

If you want to explore the MovieLens EDA notebook:

1. Ensure **dataset is downloaded** and **DB seeded** (steps 3.7–3.8).
2. Start Jupyter:

   ```powershell
   jupyter notebook
   # or:
   # jupyter lab
   ```

3. Open the notebook under `notebooks/` (e.g. `01_movielens_eda_and_eval.ipynb`).

You may need to install Jupyter if not already present:

```powershell
pip install jupyter
```

---

### 3.15 One-command helper script (optional)

You can use the helper script to perform all setup steps and start the API:

```powershell
.\scripts\run_local.ps1
```

The script will:

1. Ensure `.env` exists (`.env.example` → `.env`).
2. Start Postgres + Redis with Docker Compose.
3. Run Alembic migrations.
4. Download the MovieLens dataset (if missing).
5. Seed the database once (using a `data/.seeded` marker file).
6. Train content + MF models if artifacts are missing.
7. Start Uvicorn on `http://127.0.0.1:8000`.

You can re-run it safely; it won’t re-seed if `data/.seeded` exists.


---

## 4. Step-by-step – macOS / Linux (bash)

Commands below assume **bash** (or a similar POSIX shell) and that you are in the repo root.

### 4.1 Clone the repo

```bash
git clone <your-fork-or-clone-url>
cd recai-personalization-engine
```

---

### 4.2 Create and activate a virtualenv

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python --version    # should show 3.11.x
```

---

### 4.3 Install dependencies

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

---

### 4.4 Create `.env`

```bash
cp .env.example .env
```

Defaults are correct for host-based local dev:

```text
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/recai
REDIS_URL=redis://localhost:6379/0
```

---

### 4.5 Start Postgres + Redis

```bash
# Compose v2
docker compose up -d postgres redis

# Or if you have v1 only:
# docker-compose up -d postgres redis
```

---

### 4.6 Run migrations

```bash
alembic upgrade head
# or:
make migrate
```

---

### 4.7 Download dataset

```bash
python scripts/download_movielens_1m.py
```

If blocked, download `ml-1m.zip` from the URL printed by the script and place it at:

```text
data/raw/ml-1m.zip
```

Then re-run the script.

---

### 4.8 Seed database

```bash
python scripts/seed_db.py
```

---

### 4.9 Train models

```bash
python -m app.training.train --model content
python -m app.training.train --model mf
```

---

### 4.10 Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# or:
make run
```

Base URL: `http://127.0.0.1:8000`.

---

### 4.11 Smoke test (curl)

```bash
# Health
curl http://127.0.0.1:8000/health

# Popular recommendations
curl "http://127.0.0.1:8000/v1/recommendations?user_id=1&limit=10&strategy=popular"
```

---

### 4.12 Tests, lint, format

```bash
make test
make lint
make fmt
```

Or raw commands:

```bash
pytest
ruff check .
ruff format .
```

---

### 4.13 Notebook

```bash
pip install jupyter
jupyter notebook
```

Then open the notebook(s) in `notebooks/`.

---

### 4.14 One-command helper script (optional)

```bash
./scripts/run_local.sh
```

The script mirrors the PowerShell version (see 3.15) and is safe to re-run.


---

## 5. Makefile targets

If you have `make` installed, the Makefile exposes common workflows.

| Target          | What it does                                                     | Command                   |
|-----------------|------------------------------------------------------------------|---------------------------|
| `help`          | Print available targets and a short description                  | `make help`              |
| `install`       | Install runtime dependencies (`requirements.txt`)                | `make install`           |
| `install-dev`   | Install runtime + dev dependencies (`requirements-dev.txt`)      | `make install-dev`       |
| `up`            | Start **Postgres + Redis** via Docker Compose                    | `make up`                |
| `down`          | Stop all services defined in `docker-compose.yml`                | `make down`              |
| `logs`          | Tail logs from the `api` service (if running in Docker)         | `make logs`              |
| `migrate`       | Run Alembic migrations (`alembic upgrade head`)                  | `make migrate`           |
| `seed`          | Seed Postgres from the MovieLens 1M dataset                      | `make seed`              |
| `train-content` | Train the **content-based** TF‑IDF model                         | `make train-content`     |
| `train-mf`      | Train the **matrix factorization** (ALS) model                   | `make train-mf`          |
| `run`           | Run the API locally with Uvicorn (`PORT` default 8000)          | `make run`               |
| `test`          | Run the test suite via pytest                                    | `make test`              |
| `lint`          | Run Ruff linting                                                | `make lint`              |
| `fmt`           | Run Black formatter                                             | `make fmt`               |

Notes:

- `PYTHON` and `COMPOSE` can be overridden:
  - Example: `make PYTHON=py COMPOSE="docker-compose" up`
- `format` remains as a backward-compatible alias for `fmt`.

---

## 6. Troubleshooting

### 6.1 Port already in use

Symptoms:

- `uvicorn` fails with `OSError: [Errno 98] Address already in use`
- Docker fails to bind `5432` or `6379`

Fixes:

- Find the process on the port:
  - Windows:
    ```powershell
    netstat -ano | Select-String 8000
    ```
  - macOS/Linux:
    ```bash
    lsof -i :8000
    ```
- Stop the offending process or change `PORT` in `.env`:

  ```text
  PORT=8080
  ```

  Then restart Uvicorn:

  ```bash
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
  ```

For Postgres/Redis port conflicts, either stop the existing instances or update `docker-compose.yml` to use different host ports.

---

### 6.2 Docker not running / WSL2 issues (Windows)

Symptoms:

- `docker: Cannot connect to the Docker daemon`
- `docker compose up` hangs or fails

Checklist:

1. Ensure **Docker Desktop** is running.
2. In Docker Desktop → Settings → General:
   - Confirm **“Use the WSL 2 based engine”** is enabled.
3. In PowerShell:

   ```powershell
   wsl --status
   ```

   Ensure WSL2 is installed and running.

4. Try restarting Docker Desktop and/or WSL:

   ```powershell
   wsl --shutdown
   ```

Then re-run:

```powershell
docker compose up -d postgres redis
```

---

### 6.3 Database connection errors (`DATABASE_URL`)

Common issues:

- Wrong hostname (`postgres` vs `localhost`)
- Container not running

Error samples:

- `could not translate host name "postgres"`
- `connection refused`

Checklist:

1. For **host-based API** (recommended in this doc), ensure `.env` has:

   ```text
   DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/recai
   ```

2. Check Postgres container:

   ```powershell
   docker ps
   # or:
   docker compose ps postgres
   ```

3. If you previously edited `.env` to use `postgres` as hostname, revert it to `localhost` for host-based dev.

> Inside Docker containers, `docker-compose.yml` sets `DATABASE_URL` to use
> the internal hostname `postgres`. On the host, always use `localhost`.

---

### 6.4 Redis connection errors (`REDIS_URL`)

Symptoms:

- Errors like `Cannot connect to Redis` or timeouts when using caching.

Checklist:

1. For host-based API, ensure `.env` has:

   ```text
   REDIS_URL=redis://localhost:6379/0
   ```

2. Check Redis container:

   ```powershell
   docker compose ps redis
   ```

3. If Redis is down, start it:

   ```powershell
   docker compose up -d redis
   ```

If Redis is temporarily unavailable, the app is designed to continue serving responses using DB-based fallbacks.

---

### 6.5 Dataset download blocked

If `scripts/download_movielens_1m.py` fails due to network restrictions:

1. Note the URL printed by the script (usually):

   ```text
   https://files.grouplens.org/datasets/movielens/ml-1m.zip
   ```

2. Download `ml-1m.zip` manually in your browser.
3. Place it at:

   ```text
   data/raw/ml-1m.zip
   ```

4. Extract it so that you have:

   ```text
   data/raw/ml-1m/
     users.dat
     movies.dat
     ratings.dat
   ```

5. Re-run:

   ```bash
   python scripts/seed_db.py
   ```

---

### 6.6 “No recommendations” (empty `items` list)

Possible reasons:

1. **Database not seeded**

   - `/v1/stats` shows zero users/items/interactions.
   - Fix: run `scripts/download_movielens_1m.py` + `scripts/seed_db.py`.

2. **Models not trained**

   - For `strategy=content`, `strategy=mf`, or `strategy=hybrid`, content/MF models
     must be trained.
   - Fix:

     ```bash
     python -m app.training.train --model content
     python -m app.training.train --model mf
     ```

   - Hybrid will fall back to popularity if models are missing, but you may get
     less personalized results.

3. **New/cold-start user**

   - User has no interactions yet.
   - For hybrid, onboarding data (`preferred_genres`) helps:
     ```bash
     curl -X POST "http://127.0.0.1:8000/v1/users/onboard" \
       -H "Content-Type: application/json" \
       -d '{"user_id": 123, "preferred_genres": ["Action", "Sci-Fi"]}'
     ```
   - Then request recommendations again.

4. **Filters too restrictive**

   - Very small `limit` or unusual user IDs may yield few results.

---

### 6.7 Resetting the local DB quickly

If you want to **start from scratch** (fresh Postgres + Redis + data):

1. Stop services and remove volumes:

   ```bash
   # macOS/Linux
   docker compose down -v

   # Windows PowerShell
   docker compose down -v
   # (or: docker-compose down -v)
   ```

   This deletes the `recai_pg_data` volume defined in `docker-compose.yml`.

2. Remove the local seed marker (if created by `run_local` scripts):

   ```bash
   rm -f data/.seeded     # macOS/Linux
   # or:
   del data\.seeded       # Windows PowerShell
   ```

3. Re-start dependencies:

   ```bash
   docker compose up -d postgres redis
   alembic upgrade head
   python scripts/download_movielens_1m.py
   python scripts/seed_db.py
   python -m app.training.train --model content
   python -m app.training.train --model mf
   ```

Or just re-run the helper script:

- PowerShell:

  ```powershell
  .\scripts\run_local.ps1
  ```

- bash:

  ```bash
  ./scripts/run_local.sh
  ```

After reset, `/v1/recommendations` for `user_id=1` with `strategy=popular` or `strategy=hybrid` should return a non-empty list of items.