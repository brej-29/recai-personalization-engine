# Architectural Decisions (ADR-style)

This file records key decisions made for the RecAI MVP.  
When you make a significant change, **add or update an entry here**.

---

## ADR-001 – Use FastAPI + Uvicorn

**Status:** Accepted  
**Date:** 2024-01-01

### Context

We need a modern, async-friendly web framework with:

- Good typing and developer experience.
- First-class OpenAPI schema generation.
- Ecosystem support (tutorials, examples, integrations).

### Decision

Use **FastAPI** with **Uvicorn** as the API stack.

### Consequences

- Easy to define request/response models with Pydantic.
- Automatic OpenAPI docs at `/docs` and `/redoc`.
- Works well in limited-resource environments such as HF Spaces.

---

## ADR-002 – SQLAlchemy 2.0 + Alembic + Postgres

**Status:** Accepted  
**Date:** 2024-01-01

### Context

We require:

- A relational database for users, items, interactions, and model metadata.
- Portable schema migrations.
- Compatibility with Supabase (managed Postgres) and local dev.

### Decision

- Use **Postgres** (Supabase in production) as the primary datastore.
- Use **SQLAlchemy 2.0** ORM for models.
- Use **Alembic** for schema migrations, with `app/db/migrations/` as the migration directory.

### Consequences

- Strong relational guarantees and indexing.
- Compatible with most deployment environments.
- Requires migration discipline when changing models.

---

## ADR-003 – Redis for Caching (Upstash in Prod)

**Status:** Accepted  
**Date:** 2024-01-01

### Context

Recommendation generation can be expensive, especially for MF or content-based models.  
We want to reduce latency and load by caching per-user recommendations.

### Decision

- Use **Redis** for caching recommendation results.
- In production, use **Upstash Redis** (serverless / pay-per-use).
- In local dev, run Redis via `docker-compose`.

### Consequences

- Reduced latency for repeated recommendation requests.
- Additional infrastructure component to monitor.
- The cache is **non-critical**: system falls back gracefully if Redis is unavailable.

---

## ADR-004 – Model Artifacts on Local Disk

**Status:** Accepted  
**Date:** 2024-01-01

### Context

We need to serialize trained models (TF‑IDF vectorizer, ALS factors, mappings) and load them online.

### Decision

- Store model artifacts as pickled objects in `artifacts/` (gitignored).
- Use Postgres `model_versions` table to know which artifact path is active.
- For HF Spaces and similar environments, mount `artifacts/` in the container filesystem.

### Consequences

- Simple deployment story: artifacts live alongside code.
- Models are not versioned in git; DB + disk pairing is the source of truth.
- For multi-instance deployments, future work might move artifacts to object storage (S3, GCS, etc.).

---

## ADR-005 – Use `implicit` ALS for Collaborative Filtering

**Status:** Accepted  
**Date:** 2024-01-01

### Context

For collaborative filtering we need:

- A library optimized for implicit feedback (views, clicks).
- Mature implementation, not research code.
- Reasonably fast training on MovieLens-scale datasets.

### Decision

- Use **`implicit`** library with **ALS (Alternating Least Squares)** as the first MF model.
- Optimize for implicit feedback rather than explicit ratings.

### Consequences

- ALS works well for user–item interaction data without explicit ratings.
- Library is actively maintained and battle-tested on similar workloads.
- Cold-start still needs help from popular/content-based models.

---

## ADR-006 – Metrics: Recall@K and NDCG@K

**Status:** Accepted  
**Date:** 2024-01-01

### Context

We need offline metrics that reflect ranking quality for top-N recommendations.

### Decision

- Use **Recall@K** and **NDCG@K** as primary evaluation metrics:
  - Recall@K focuses on hit rate.
  - NDCG@K captures ranking quality.
- Optional RMSE for rating-prediction baselines if needed later.

### Consequences

- Aligns with common recommender-system evaluation practice.
- Offline metrics provide a baseline, but **A/B testing is still needed**
  in production (planned for a later prompt).

---

## ADR-007 – Hugging Face Spaces (Docker) as Target Runtime

**Status:** Accepted  
**Date:** 2024-01-01

### Context

We want a **free-first** deployment story with low operational friction.

### Decision

- Target deployment to **Hugging Face Spaces** using the **Docker** runtime.
- The same Docker image should be usable locally and on Spaces.

### Consequences

- Constraints on resource usage (CPU, RAM, disk), so models must be efficient.
- Simpler operations: no bespoke infrastructure needed for MVP.
- Later work can extend to other deployment targets if needed.

---

## ADR-008 – Hybrid Recommender Weights and Fallback Ladder

**Status:** Accepted  
**Date:** 2024-01-02

### Context

We now have three recommenders:

- Collaborative filtering (ALS via `implicit`).
- Content-based TF‑IDF.
- Popularity / trending baseline.

We want:

- A **single hybrid strategy** that combines these signals.
- Explicit, configurable weights.
- Robust behaviour in cold-start and partial-failure scenarios (missing models, new users).

### Decision

- Introduce a `HybridRecommender` that:

  - Normalises scores within each component.
  - Combines them with configurable weights:
    - `hybrid_weight_mf = 0.55`
    - `hybrid_weight_content = 0.35`
    - `hybrid_weight_popular = 0.10`
  - Re-normalises weights over available components (if MF or content is missing).

- Implement a **fallback ladder**:

  1. If the user has no interactions, use onboarding preferences + popularity.
  2. If MF/content models are not ready, fall back to popularity.
  3. When all three are available, use the weighted ensemble.

- Expose hybrid as `strategy=hybrid` on `/v1/recommendations`.
- Attach lightweight explanations per item (reasons list) derived from the contributing models.

### Consequences

- A single endpoint (`strategy=hybrid`) gives the best available signal for each user.
- We can tune weights via environment/config without changing code.
- Cold-start users and partially trained deployments still return sensible results.
- Future work can refine the weighting scheme (e.g. per‑segment, per‑domain).

---

## ADR-009 – A/B Testing Framework and Metrics Aggregation

**Status:** Accepted  
**Date:** 2024-01-02

### Context

We need a minimal but real **online evaluation** loop:

- Compare `hybrid` vs `popular` strategies.
- Deterministically assign users to variants.
- Track impressions and clicks, and derive CTR-like metrics.
- Keep the design simple enough for a single-node HF Space.

### Decision

- Add three tables:

  - `experiments(id, name, status, config, created_at)`  
  - `assignments(id, user_id, experiment_id, variant, assigned_at)`  
  - `events_agg(id, date, experiment_id, variant, impressions, clicks)`

- Define a default experiment:

  - Name: `hybrid_vs_popular`
  - Variants: `["hybrid", "popular"]` (stored in `config` JSONB).

- Deterministic assignment:

  - Hash `(experiment_name, user_id)` via `utils.hashing.stable_hash`.
  - Map the hash bucket to one of the variants.
  - Persist the assignment once; subsequent requests reuse the stored row.

- Event aggregation:

  - Every `/v1/recommendations` call with `strategy in {"hybrid", "popular"}`:
    - Look up the experiment + assignment.
    - If the served strategy matches the assigned variant, increment **impressions** for that variant.
  - Every `/v1/track` `click` event:
    - Look up the assignment and increment **clicks** for the assigned variant.

- Admin APIs:

  - `POST /v1/admin/experiments/create` – ensure default experiment exists.
  - `GET /v1/admin/experiments` – list experiments.
  - `GET /v1/admin/experiments/{name}/report` – aggregate counts and CTR per variant.

### Consequences

- We have a **lightweight online evaluation loop** suitable for an MVP.
- Assignment is stable per user and persists beyond code changes.
- Metrics are aggregated daily in `events_agg`, small enough for HF Spaces.
- The framework can be extended to more experiments and metrics later.

---

## ADR-010 – Free-First Infra: Supabase + Upstash + HF Spaces

**Status:** Accepted  
**Date:** 2024-01-02

### Context

The project aims to be deployable on **free tiers** with minimal operations work.

### Decision

- Use **Supabase Postgres** as the recommended managed Postgres for production-like environments.
- Use **Upstash Redis** as the recommended managed Redis (serverless, pay-per-use).
- Use **Hugging Face Spaces (Docker runtime)** as the primary hosting platform.
- Document a clear path in `context/DEPLOYMENT.md` for setting up:

  - Supabase project and `DATABASE_URL`.
  - Upstash Redis and `REDIS_URL`.
  - HF Space with Docker runtime and environment variables.

### Consequences

- A complete, reproducible deployment story using only free/low-cost services.
- Supabase free tier may auto-pause; `/health` and the Supabase dashboard can be used to wake it.
- No vendor-specific code is baked into the core application – env vars remain the abstraction layer.

---

## How to Use This File

- Before introducing new patterns (e.g. feature store, new model family), add an ADR explaining:
  - Context
  - Options considered
  - Decision
  - Consequences
- Keep ADRs short but explicit.
- Link to this file from PR descriptions when adding major changes.