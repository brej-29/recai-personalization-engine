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

## How to Use This File

- Before introducing new patterns (e.g. feature store, new model family), add an ADR explaining:
  - Context
  - Options considered
  - Decision
  - Consequences
- Keep ADRs short but explicit.
- Link to this file from PR descriptions when adding major changes.