from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from app.db.models import Interaction, Item
from app.services.model_registry import get_active_model_version

logger = logging.getLogger(__name__)


@dataclass
class ContentRecommendation:
    item_id: int
    title: str
    score: float
    reason: Optional[str] = None


@dataclass
class NeighborItem:
    item_id: int
    title: str
    score: float
    reason: Optional[str] = None


@dataclass
class ContentModelArtifact:
    vectorizer: TfidfVectorizer
    item_ids: np.ndarray  # shape (n_items,)
    item_titles: List[str]
    item_matrix: np.ndarray  # TF-IDF matrix (n_items, n_features)


class ContentRecommender:
    def __init__(self, db: Session, artifact: Optional[ContentModelArtifact]):
        self.db = db
        self.artifact = artifact

    def is_ready(self) -> bool:
        return self.artifact is not None

    def _liked_items_for_user(self, user_id: int, top_n: int = 20) -> List[Item]:
        q = (
            self.db.query(Interaction)
            .filter(
                Interaction.user_id == user_id,
                Interaction.event_type.in_(["rate", "click", "view"]),
            )
            .order_by(Interaction.rating.desc().nullslast(), Interaction.ts.desc())
            .limit(top_n)
        )
        interactions = q.all()
        if not interactions:
            return []
        item_ids = [i.item_id for i in interactions]
        items = self.db.query(Item).filter(Item.id.in_(item_ids)).all()
        return items

    def _explain(self, item_idx: int, source_idx: int) -> str:
        assert self.artifact is not None
        # For MVP, explanation is simple: reference the source title and overlapping genres.
        item_title = self.artifact.item_titles[item_idx]
        source_title = self.artifact.item_titles[source_idx]
        return f"Because similar to '{source_title}'"

    def recommend(self, user_id: int, limit: int = 20) -> List[ContentRecommendation]:
        if not self.is_ready():
            # Fallback to empty list; caller may fallback to popular recommender.
            logger.warning("Content recommender is not ready; returning empty list.")
            return []

        assert self.artifact is not None
        liked_items = self._liked_items_for_user(user_id)
        if not liked_items:
            logger.info("No interactions for user %s in content recommender.", user_id)
            return []

        id_to_index = {int(i): idx for idx, i in enumerate(self.artifact.item_ids)}
        liked_indices = [id_to_index[i.id] for i in liked_items if i.id in id_to_index]
        if not liked_indices:
            return []

        liked_matrix = self.artifact.item_matrix[liked_indices]
        user_profile = liked_matrix.mean(axis=0, keepdims=True)
        sims = cosine_similarity(user_profile, self.artifact.item_matrix)[0]

        seen_item_ids = {i.id for i in liked_items}
        candidates: List[Tuple[int, float]] = []
        for idx, score in enumerate(sims):
            item_id = int(self.artifact.item_ids[idx])
            if item_id in seen_item_ids:
                continue
            candidates.append((idx, float(score)))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top = candidates[:limit]

        recs: List[ContentRecommendation] = []
        for idx, score in top:
            item_id = int(self.artifact.item_ids[idx])
            title = self.artifact.item_titles[idx]
            # Choose most similar liked item for explanation
            liked_scores = cosine_similarity(
                self.artifact.item_matrix[[idx]],
                self.artifact.item_matrix[liked_indices],
            )[0]
            best_source_idx = liked_indices[int(np.argmax(liked_scores))]
            reason = self._explain(idx, best_source_idx)
            recs.append(
                ContentRecommendation(
                    item_id=item_id,
                    title=title,
                    score=float(score),
                    reason=reason,
                )
            )
        return recs

    def similar_items(self, item_id: int, limit: int = 20) -> List[NeighborItem]:
        if not self.is_ready():
            logger.warning("Content recommender is not ready; cannot compute similar items.")
            return []

        assert self.artifact is not None
        id_to_index = {int(i): idx for idx, i in enumerate(self.artifact.item_ids)}
        if item_id not in id_to_index:
            return []

        idx = id_to_index[item_id]
        sims = cosine_similarity(
            self.artifact.item_matrix[[idx]],
            self.artifact.item_matrix,
        )[0]

        candidates: List[Tuple[int, float]] = []
        for j, score in enumerate(sims):
            if j == idx:
                continue
            candidates.append((j, float(score)))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top = candidates[:limit]

        neighbors: List[NeighborItem] = []
        for j, score in top:
            neighbor_id = int(self.artifact.item_ids[j])
            title = self.artifact.item_titles[j]
            reason = self._explain(j, idx)
            neighbors.append(
                NeighborItem(item_id=neighbor_id, title=title, score=float(score), reason=reason)
            )
        return neighbors


def _load_artifact_from_disk(path: Path) -> Optional[ContentModelArtifact]:
    if not path.exists():
        return None
    with path.open("rb") as f:
        data = pickle.load(f)
    return ContentModelArtifact(
        vectorizer=data["vectorizer"],
        item_ids=data["item_ids"],
        item_titles=data["item_titles"],
        item_matrix=data["item_matrix"],
    )


def get_content_recommender(db: Session) -> ContentRecommender:
    active = get_active_model_version(db, name="content_tfidf")
    artifact: Optional[ContentModelArtifact] = None
    if active:
        artifact_path = Path(active.path)
        artifact = _load_artifact_from_disk(artifact_path)
        if artifact is None:
            logger.warning("Failed to load content artifact from %s", artifact_path)
    else:
        logger.info("No active content_tfidf model; content recommender will be empty.")
    return ContentRecommender(db=db, artifact=artifact)