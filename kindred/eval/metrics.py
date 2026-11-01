"""Small, deterministic ranking metrics and paired bootstrap utilities."""

from __future__ import annotations

import numpy as np


def _binary_hits(ranked: np.ndarray, relevant: set[int], k: int) -> np.ndarray:
    return np.asarray([int(item in relevant) for item in ranked[:k]], dtype=float)


def ndcg_at_k(ranked: np.ndarray | list[int], relevant: set[int] | list[int], k: int = 10) -> float:
    """Binary-label NDCG for one ranked list."""
    hits = _binary_hits(np.asarray(ranked), set(relevant), k)
    discounts = 1.0 / np.log2(np.arange(2, hits.size + 2))
    dcg = float(np.dot(hits, discounts))
    ideal_n = min(len(relevant), k)
    ideal = float(np.sum(1.0 / np.log2(np.arange(2, ideal_n + 2)))) if ideal_n else 0.0
    return dcg / ideal if ideal else 0.0


def recall_at_k(ranked: np.ndarray | list[int], relevant: set[int] | list[int], k: int = 10) -> float:
    relevant = set(relevant)
    return float(sum(item in relevant for item in np.asarray(ranked)[:k])) / len(relevant) if relevant else 0.0


def mrr(ranked: np.ndarray | list[int], relevant: set[int] | list[int], k: int = 10) -> float:
    relevant = set(relevant)
    for rank, item in enumerate(np.asarray(ranked)[:k], start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def hit_rate_at_k(ranked: np.ndarray | list[int], relevant: set[int] | list[int], k: int = 10) -> float:
    relevant = set(relevant)
    return float(any(item in relevant for item in np.asarray(ranked)[:k]))


def query_metric_arrays(
    rankings: list[np.ndarray], relevant: list[set[int] | list[int]], k: int = 10
) -> dict[str, np.ndarray]:
    """Return one value per query, keeping paired comparisons aligned."""
    return {
        "ndcg@10": np.asarray([ndcg_at_k(r, rel, k) for r, rel in zip(rankings, relevant)]),
        "recall@10": np.asarray([recall_at_k(r, rel, k) for r, rel in zip(rankings, relevant)]),
        "mrr": np.asarray([mrr(r, rel, k) for r, rel in zip(rankings, relevant)]),
        "hit@10": np.asarray([hit_rate_at_k(r, rel, k) for r, rel in zip(rankings, relevant)]),
    }


def catalogue_coverage(rankings: list[np.ndarray], k: int = 10) -> float:
    if not rankings:
        return 0.0
    return float(len({int(item) for ranking in rankings for item in ranking[:k]}))


def mean_popularity_percentile(
    rankings: list[np.ndarray], popularity_percentile: np.ndarray, k: int = 10
) -> float:
    values = [popularity_percentile[int(item)] for ranking in rankings for item in ranking[:k]]
    return float(np.mean(values)) if values else 0.0


def paired_bootstrap(
    first: np.ndarray | list[float],
    second: np.ndarray | list[float],
    n_resamples: int = 10_000,
    seed: int = 13,
    batch_size: int = 512,
) -> dict[str, float]:
    """Bootstrap the paired mean difference (first minus second), vectorised in batches."""
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    if first.shape != second.shape or first.ndim != 1:
        raise ValueError("paired bootstrap inputs must be one-dimensional and equally sized")
    if not first.size:
        return {"mean_diff": 0.0, "ci_low": 0.0, "ci_high": 0.0, "n": 0}
    delta = first - second
    rng = np.random.default_rng(seed)
    estimates = np.empty(n_resamples, dtype=float)
    for start in range(0, n_resamples, batch_size):
        stop = min(start + batch_size, n_resamples)
        indices = rng.integers(0, delta.size, size=(stop - start, delta.size))
        estimates[start:stop] = delta[indices].mean(axis=1)
    low, high = np.quantile(estimates, [0.025, 0.975])
    return {
        "mean_diff": float(delta.mean()),
        "ci_low": float(low),
        "ci_high": float(high),
        "n": int(delta.size),
    }


def bootstrap_mean_ci(
    values: np.ndarray | list[float], n_resamples: int = 10_000, seed: int = 13
) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    zeros = np.zeros_like(values)
    result = paired_bootstrap(values, zeros, n_resamples=n_resamples, seed=seed)
    return {"mean": float(values.mean()) if values.size else 0.0,
            "ci_low": result["ci_low"], "ci_high": result["ci_high"], "n": result["n"]}
