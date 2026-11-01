"""Non-learned and zero-shot ranking baselines."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TextFeatures:
    tags: object
    descriptions: object


def _feature_text(row: dict, weighted_tags: bool) -> str:
    genres = [f"genre_{genre}" for genre in row.get("genres", [])]
    tags = []
    for tag in row.get("tags", []):
        token = f"tag_{tag.get('n', '')}"
        repeats = max(1, round(float(tag.get("r", 0)) / 20)) if weighted_tags else 1
        tags.extend([token] * repeats)
    return " ".join(genres + tags)


def build_text_features(rows: list[dict]) -> TextFeatures:
    """Build normalized sparse matrices for the two TF-IDF channels."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    tag_vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w[\w-]+\b")
    tag_matrix = tag_vectorizer.fit_transform(
        [_feature_text(row, weighted_tags=True) for row in rows]
    )
    desc_vectorizer = TfidfVectorizer(max_features=80_000, ngram_range=(1, 2), min_df=1)
    desc_matrix = desc_vectorizer.fit_transform([row.get("text", "") for row in rows])
    return TextFeatures(tags=tag_matrix, descriptions=desc_matrix)


def _order(scores: np.ndarray, candidates: tuple[int, ...] | list[int], k: int) -> np.ndarray:
    candidates = np.asarray(candidates, dtype=int)
    if not candidates.size:
        return candidates
    order = np.argsort(-scores, kind="mergesort")
    return candidates[order[:k]]


def _jaccard(query: dict, candidate: dict) -> float:
    left = set(query.get("genres", []))
    right = set(candidate.get("genres", []))
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def rank_baseline(
    system: str,
    query_idx: int,
    candidates: tuple[int, ...] | list[int],
    rows: list[dict],
    features: TextFeatures,
    embeddings: np.ndarray | None = None,
    rng: np.random.Generator | None = None,
    k: int = 10,
) -> np.ndarray:
    """Rank one candidate pool using a named baseline."""
    candidates = tuple(candidates)
    if system == "random":
        rng = rng or np.random.default_rng(13)
        return np.asarray(rng.permutation(candidates)[:k], dtype=int)
    if system == "popularity":
        scores = np.asarray([np.log1p(rows[i].get("pop") or 0) for i in candidates])
    elif system == "genre":
        scores = np.asarray([_jaccard(rows[query_idx], rows[i]) for i in candidates])
    elif system == "tag_tfidf":
        scores = (features.tags.getrow(query_idx) @ features.tags[list(candidates)].T).toarray()[0]
    elif system == "description_tfidf":
        scores = (features.descriptions.getrow(query_idx) @ features.descriptions[list(candidates)].T).toarray()[0]
    elif system == "dense":
        if embeddings is None:
            raise ValueError("dense ranking requires embeddings")
        scores = embeddings[query_idx] @ embeddings[list(candidates)].T
    else:
        raise ValueError(f"unknown baseline: {system}")
    return _order(np.asarray(scores).ravel(), candidates, k)


def popularity_percentiles(rows: list[dict]) -> np.ndarray:
    """Return a 0..1 percentile where 1 is the most popular item."""
    popularity = np.asarray([float(row.get("pop") or 0) for row in rows])
    order = np.argsort(np.argsort(-popularity, kind="mergesort"), kind="mergesort")
    denominator = max(1, len(rows) - 1)
    return 1.0 - order / denominator
