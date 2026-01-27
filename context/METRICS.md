# Metrics

This document explains the evaluation metrics used in the RecAI MVP.

---

## 1. Recall@K

**Goal:** How many of the relevant items did we recover in the top-K recommendations?

Given:

- `R` – the set of relevant items for a user in the evaluation period.
- `L_K` – the list of top-K recommended items.

The **Recall@K** is:

```text
Recall@K = |R ∩ L_K| / |R|
```

Properties:

- Range: `[0, 1]`
- `1.0` means we retrieved **all** relevant items in the top-K list.
- If `R` is empty, we define Recall@K = `0.0` for that user in our implementation.

In this project, Recall@K is computed per user and then **averaged** across users.

---

## 2. NDCG@K (Normalized Discounted Cumulative Gain)

**Goal:** Capture the **ranking quality** in the top-K recommendations.

Given:

- A relevance score for each item (for the MVP we use binary relevance: relevant or not).
- A ranked list of top-K items `L_K`.

We first compute **Discounted Cumulative Gain** (DCG):

```text
DCG@K = Σ_{i=1..K} (rel_i / log2(i + 1))
```

Where:

- `rel_i` is the relevance of the item at position `i` (1 if relevant, 0 if not, in the MVP).
- The denominator discounts items at lower ranks.

Then we compute **Ideal DCG** (IDCG), which is DCG computed on the ideal ranking where
all relevant items are placed at the top.

Finally:

```text
NDCG@K = DCG@K / IDCG@K
```

Properties:

- Range: `[0, 1]`
- `1.0` means the ranking is perfectly ordered with all relevant items at the top.
- If `IDCG@K` is zero (no relevant items), we define NDCG@K = `0.0`.

As with Recall@K, we average NDCG@K across users.

---

## 3. RMSE (Optional / Future)

For rating predictions (not the core of this MVP), we may compute **Root Mean Squared Error**:

```text
RMSE = sqrt( (1/N) * Σ (y_true_i - y_pred_i)^2 )
```

Where:

- `y_true_i` is the true rating.
- `y_pred_i` is the predicted rating.
- `N` is the number of observations.

RMSE is more relevant when we care about predicting explicit ratings; for top-N recommendation
we prefer Recall@K and NDCG@K.

---

## 4. How Metrics Are Used Here

- During training in `app/training/train.py`:
  - A simple evaluation procedure holds out each user’s last interaction as “relevant”.
  - The recommender (content or MF) generates top-N recommendations.
  - Recall@K and NDCG@K are computed at a fixed K (e.g. 10).
  - Metrics are stored in Postgres in the `model_versions.metrics` JSON field.

- In the EDA notebook:
  - Metrics are visualised and compared across models.
  - We discuss trade-offs and limitations of offline evaluation.

In production, these metrics provide **signals and guardrails**, but **online A/B tests**
are ultimately required to validate improvements. That work is planned for a future prompt.