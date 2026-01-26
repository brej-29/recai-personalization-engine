# RecAI – Multi-Domain Personalization Engine (MVP Goal)

## Scope

Build a **production-grade recommendation API** that can be deployed for free (later) on **Hugging Face Docker Spaces**, using:

1. **Popular / Trending baseline**
2. **Content-based TF‑IDF similarity**
3. **Collaborative filtering (matrix factorization) with `implicit` ALS/BPR**

Backed by:

- **Postgres** (Supabase in production) for:
  - users, items, interactions
  - model metadata / versions
- **Redis** (Upstash in production) for:
  - per-user recommendation result caching
- **FastAPI** + **SQLAlchemy 2.0** + **Alembic**
- **Docker** + **GitHub Actions CI**

The first milestone is a **MovieLens 1M**-based movie recommendation API, but the architecture must be usable for other domains later (e.g. content, products).

---

## Non‑Goals (for this MVP)

- Full-featured **A/B testing framework** (only noted as “coming next”)
- Real-time **feature store** or streaming ingestion (Kafka, Kinesis, etc.)
- Advanced model types (deep learning, sequence models, bandits)
- Complex back-office UI (only API + minimal scripts)
- Multi-tenant / multi-domain routing (yet – design should not block it)
- Advanced auth / RBAC (we assume trusted access for MVP)

---

## Success Criteria

### Functional

- `/health` and `/v1/recommendations` return valid JSON with `request_id`.
- At least three strategies exposed:
  - `popular`
  - `content`
  - `mf`
- Content-based API supports **item‑item similarity**:
  - `/v1/items/{item_id}/similar`
- `POST /v1/track` persists interactions.

### Data & Modeling

- `scripts/download_movielens_1m.py` and `scripts/seed_db.py` work for local dev.
- At least one trained model for:
  - `content_tfidf`
  - `mf_als`
- Model artifacts stored under `artifacts/` (gitignored) with metadata in Postgres.
- Basic offline evaluation implemented:
  - **Recall@K**
  - **NDCG@K**
  - Optional RMSE for rating baseline (not required for API).

### Engineering Quality

- Clean, typed Python where sensible.
- Centralized **config**, **logging**, and **exception handling**.
- `make lint` and `make test` pass.
- `docker-compose up` brings up:
  - API
  - Postgres
  - Redis
- **No secrets** committed. `.env.example` documents expected env vars.
- GitHub Actions CI runs lint + tests on PR/branch.

---

## Product Experience

- Fast responses for typical MovieLens users.
  - Popular baseline works even without any trained model.
  - Redis caches recommendations per (user, strategy, limit) with a short TTL.
- Explainability for content-based recommendations:
  - Simple text such as:  
    `Because similar to "The Matrix" (shared terms / genres).`
- Clear onboarding:
  - `README.md` explains quickstart, training, and deployment.
  - `notebooks/01_movielens_eda_and_eval.ipynb` explains choices and tradeoffs.

---

## What Future Work Should Optimize For

1. **Ease of extension to new domains** (e.g. different item types, features).
2. **Safe iteration**:
   - ADRs in `context/DECISIONS.md`
   - Changes recorded in `context/CHANGELOG.md`
3. **Observability**:
   - Add metrics (Prometheus / OpenTelemetry) next.
   - Add A/B testing and user-level experiment flags in a later prompt.
4. **Cold start solutions**:
   - Better content-based defaults.
   - New-user flows and cross-domain bootstrapping.

Before changing architecture or core behavior, always re-read this file and
`context/ARCHITECTURE.md` to keep RecAI focused and coherent.