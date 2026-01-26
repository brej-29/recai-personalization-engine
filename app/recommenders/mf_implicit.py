from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Interaction, Item
from app.services.model_registry import get_active_model_version

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class MFRecommendation:
    item_id: int
    title: str
    score: float
    reason: Optional[str] = None


@dataclass
class MFModelArtifact:
    user_factors: np.ndarray  # (n_users, k)
    item_factors: np.ndarray  # (n_items, k)
    user_id_mapping: Dict[int, int]
    item_id_mapping: Dict[int, int]


class MFRecommender:
    def __init__(self, db: Session, artifact: Optional[MFModelArtifact]):
        self.db = db
        self.artifact = artifact

    def is_ready(self) -> bool:
        return self.artifact is not None

    def recommend(self, user_id: int, limit: int = 20) -> List[MFRecommendation]:
        if not self.is_ready():
            logger.warning("MF recommender is not ready; returning empty list.")
            return []

        assert self.artifact is not None

        if user_id not in self.artifact.user_id_mapping:
            logger.info("User %s unknown to MF model; returning empty list.", user_id)
            return []

        uidx = self.artifact.user_id_mapping[user_id]
        user_vec = self.artifact.user_factors[uidx]  # (k,)
        scores = user_vec @ self.artifact.item_factors.T  # (n_items,)

        # Filter out items the user has already interacted with
        seen_item_ids = {
            i.item_id
            for i in self.db.query(Interaction).filter(Interaction.user_id == user_id).all()
        }

        candidates: List[Tuple[int, float]] = []
        for item_id, iidx in self.artifact.item_id_mapping.items():
            if item_id in seen_item_ids:
                continue
            candidates.append((item_id, float(scores[iidx])))

        candidates.sort(key=lambda x: x[1], reverse=True)
        top = candidates[:limit]

        items_by_id = {
            item.id: item for item in self.db.query(Item).filter(Item.id.in_([c[0] for c in top])).all()
        }

        recs: List[MFRecommendation] = []
        for item_id, score in top:
            item = items_by_id.get(item_id)
            if not item:
                continue
            recs.append(
                MFRecommendation(
                    item_id=item.id,
                    title=item.title,
                    score=float(score),
                    reason="Latent-factor similarity",
                )
            )
        return recs


def _load_artifact_from_disk(path: Path) -> Optional[MFModelArtifact]:
    if not path.exists():
        return None
    with path.open("rb") as f:
        data = pickle.load(f)
    return MFModelArtifact(
        user_factors=data["user_factors"],
        item_factors=data["item_factors"],
        user_id_mapping=data["user_id_mapping"],
        item_id_mapping=data["item_id_mapping"],
    )


def get_mf_recommender(db: Session) -> MFRecommender:
    active = get_active_model_version(db, name="mf_als")
    artifact: Optional[MFModelArtifact] = None
    if active:
        artifact_path = Path(active.path)
        artifact = _load_artifact_from_disk(artifact_path)
        if artifact is None:
            logger.warning("Failed to load MF artifact from %s", artifact_path)
    else:
        logger.info("No active mf_als model; MF recommender will be empty.")
    return MFRecommender(db=db, artifact=artifact)