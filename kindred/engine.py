"""Tiny numpy-only recommendation engine used by the evaluation harness."""

from __future__ import annotations

import numpy as np


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix / np.maximum(norms, 1e-12)


def family_center(matrix: np.ndarray, families: list[str] | np.ndarray) -> np.ndarray:
    """Subtract each family mean and re-normalize each row."""
    result = np.asarray(matrix, dtype=np.float32).copy()
    families = np.asarray(families)
    for family in np.unique(families):
        indices = np.flatnonzero(families == family)
        result[indices] -= result[indices].mean(axis=0, keepdims=True)
    return _normalize(result).astype(np.float32)


class KindredEngine:
    """Explicit dense/tag/popularity fusion over one in-memory catalogue."""

    def __init__(
        self,
        rows: list[dict],
        embeddings: np.ndarray,
        tag_features=None,
        centered: bool = False,
        adapter: np.ndarray | None = None,
        weights: dict[str, float] | None = None,
    ) -> None:
        self.rows = rows
        self.weights = dict(weights or {"a": 1.0, "b": 0.0, "c": 0.0})
        families = np.asarray([row.get("family", "") for row in rows])
        dense = family_center(embeddings, families) if centered else _normalize(embeddings)
        if adapter is not None:
            dense = _normalize(dense @ np.asarray(adapter, dtype=np.float32))
        self.embeddings = dense.astype(np.float32)
        self.tag_features = tag_features
        self.log_pop = np.log1p(np.asarray([row.get("pop") or 0 for row in rows], dtype=np.float32))

    def _candidate_indices(self, medium_filter: str | set[str] | list[str]) -> np.ndarray:
        allowed = {medium_filter} if isinstance(medium_filter, str) else set(medium_filter)
        return np.asarray(
            [
                i for i, row in enumerate(self.rows)
                if row.get("medium") in allowed or row.get("family") in allowed
            ],
            dtype=int,
        )

    def recommend(
        self,
        seeds: list[int] | tuple[int, ...] | np.ndarray,
        medium_filter: str | set[str] | list[str],
        k: int = 10,
        candidate_indices: list[int] | tuple[int, ...] | np.ndarray | None = None,
    ) -> np.ndarray:
        """Recommend top-k items for the mean vector of ``seeds``."""
        seeds = np.asarray(seeds, dtype=int)
        if not seeds.size:
            return np.asarray([], dtype=int)
        candidates = (
            np.asarray(candidate_indices, dtype=int)
            if candidate_indices is not None
            else self._candidate_indices(medium_filter)
        )
        allowed = self._candidate_indices(medium_filter)
        candidates = candidates[np.isin(candidates, allowed)]
        if not candidates.size:
            return candidates
        query = self.embeddings[seeds].mean(axis=0)
        query /= max(float(np.linalg.norm(query)), 1e-12)
        dense_cos = self.embeddings[candidates] @ query
        tag_cos = np.zeros(candidates.size, dtype=np.float32)
        if self.tag_features is not None:
            tag_query = np.asarray(self.tag_features[seeds].mean(axis=0)).ravel()
            tag_norm = max(float(np.linalg.norm(tag_query)), 1e-12)
            tag_cos = np.asarray(self.tag_features[candidates] @ (tag_query / tag_norm)).ravel()
        pop = self.log_pop[candidates]
        pop_prior = (pop - pop.mean()) / max(float(pop.std()), 1e-12)
        score = (
            self.weights.get("a", 0.0) * dense_cos
            + self.weights.get("b", 0.0) * tag_cos
            + self.weights.get("c", 0.0) * pop_prior
        )
        order = np.argsort(-score, kind="mergesort")[:k]
        return candidates[order]


def recommend(
    seeds: list[int] | tuple[int, ...] | np.ndarray,
    embedding_matrix: np.ndarray,
    rows: list[dict],
    medium_filter: str | set[str] | list[str],
    k: int = 10,
    tag_features=None,
    centered: bool = False,
    adapter: np.ndarray | None = None,
    weights: dict[str, float] | None = None,
    candidate_indices: list[int] | tuple[int, ...] | np.ndarray | None = None,
) -> np.ndarray:
    """Functional wrapper for callers that do not need a persistent engine."""
    engine = KindredEngine(
        rows, embedding_matrix, tag_features=tag_features, centered=centered,
        adapter=adapter, weights=weights
    )
    return engine.recommend(seeds, medium_filter, k, candidate_indices=candidate_indices)
