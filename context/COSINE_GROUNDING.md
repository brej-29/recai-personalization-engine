# Cosine Grounding Guidance

This document describes how future work on this repository should stay **grounded**, consistent, and safe.

---

## 1. Always Read Context Before Coding

For any non-trivial task:

1. Read:
   - `context/GOAL.md`
   - `context/ARCHITECTURE.md`
   - `context/DECISIONS.md`
2. Skim:
   - `context/CHANGELOG.md`
   - `context/DATASET.md`
   - `context/METRICS.md`

This ensures you understand:

- The **scope** and **non-goals**.
- The current **architecture** and expected flows.
- The **ADR decisions** already made.

If your change contradicts an ADR or goal, pause and reconsider.

---

## 2. Update Context When You Change Behavior

For any significant change:

- If you **change architecture** or add a new technology:
  - Update `context/DECISIONS.md` with a new ADR entry.
- If you **change user-facing behavior** or add new endpoints:
  - Update `context/CHANGELOG.md`.
  - Update `README.md` if needed for onboarding.
- If you change dataset assumptions or schemas:
  - Update `context/DATASET.md`.

Do not treat these files as optional documentation – they are **part of the contract** for this project.

---

## 3. Respect the Engineering Baseline

When implementing new functionality:

- Keep:
  - Structured logging with `request_id`.
  - Central exception handling and consistent error schema.
  - SQLAlchemy 2.0 ORM + Alembic migrations.
  - Pydantic models for request/response schemas.
- Avoid:
  - Ad-hoc global state.
  - Copy-pasted or untyped code when typing is reasonable.
  - Introducing new tech (message queues, feature stores, etc.) without an ADR.

---

## 4. Data & Model Grounding

- MovieLens 1M is the **reference dataset** for EDA and evaluation.
- If you introduce new datasets or domains:
  - Document them in `context/DATASET.md`.
  - Explain schema and mapping to existing `users/items/interactions` tables.
- For new models:
  - Register them via `model_versions` table.
  - Store artifacts under `artifacts/`.
  - Add a short rationale and metric discussion to:
    - `context/DECISIONS.md`
    - `context/METRICS.md` (if new metrics appear)

---

## 5. Operational & Deployment Grounding

- Keep the system deployable to **Hugging Face Spaces (Docker)** with:
  - Postgres (Supabase in production).
  - Redis (Upstash in production).
- Do not hardcode secrets or provider-specific values.
  - Always use environment variables.
- If deployment / infra behavior changes, reflect it in:
  - `README.md` (Quickstart + deployment sections).
  - `context/ARCHITECTURE.md` and `context/DECISIONS.md` as appropriate.

---

## 6. Experimentation and Future Extensions

A/B testing and advanced experimentation will be added later.

When that work begins:

- Keep experiment logic as a thin layer that selects **which recommender** to call.
- Do not bake experiment logic deep into the recommenders.
- Document experiment design choices and metrics explicitly.

---

## 7. Summary Checklist for Future Tasks

Before opening or updating a PR:

- [ ] Re-read `GOAL.md` and `ARCHITECTURE.md`.
- [ ] Check if your change needs a new ADR in `DECISIONS.md`.
- [ ] Update `CHANGELOG.md` for user-visible changes.
- [ ] Make sure CI (`make lint` & `make test`) passes.
- [ ] Ensure no secrets are committed; `.env.example` is updated if needed.
- [ ] Confirm the Docker-based workflow still works conceptually.

This is how we keep RecAI coherent, trustworthy, and easy to extend over time.