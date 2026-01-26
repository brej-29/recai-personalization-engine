from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np


def recall_at_k(recommended: Iterable[int], relevant: Iterable[int], k: int) -> float:
    recommended_k = list(recommended)[:k]
    if not relevant:
        return 0.0
    hits = len(set(recommended_k) & set(relevant))
    return hits / float(len(set(relevant)))


def ndcg_at_k(recommended: Iterable[int], relevant: Iterable[int], k: int) -> float:
    recommended_k = list(recommended)[:k]
    if not relevant:
        return 0.0
    rel_set = set(relevant)

    def dcg(scores: List[int]) -> float:
        return float(sum(score / np.log2(idx + 2) for idx, score in enumerate(scores)))

    gains = [1 if item in rel_set else 0 for item in recommended_k]
    ideal_gains = sorted(gains, reverse=True)

    dcg_val = dcg(gains)
    idcg_val = dcg(ideal_gains)
    if idcg_val == 0:
        return 0.0
    return dcg_val / idcg_val


def evaluate_recommender(
    user_recs: Dict[int, List[int]],
    user_relevant: Dict[int, List[int]],
    k: int = 10,
) -> Dict[str, float]:
    recalls: List[float] = []
    ndcgs: List[float] = []

    for user_id, recs in user_recs.items():
        relevant = user_relevant.get(user_id, [])
        recalls.append(recall_at_k(recs, relevant, k))
        ndcgs.append(ndcg_at_k(recs, relevant, k))

    if not recalls:
        return {"recall_at_k": 0.0, "ndcg_at_k": 0.0}

    return {
        "recall_at_k": float(np.mean(recalls)),
        "ndcg_at_k": float(np.mean(ndcgs)),
    }