from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Interaction, Item, User
from app.recommenders.content_tfidf import ContentRecommender, get_content_recommender
from app.recommenders.mf_implicit import MFRecommender, get_mf_recommender
from app.recommenders.popular import PopularRecommender, get_popular_recommender

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class HybridComponentScores:
    mf_score: float = 0.0
    content_score: float = 0.0
    popular_score: float = 0.0
    reasons: List[str] = None  # type: ignore[assignment]


@dataclass
class HybridRecommendation:
    item_id: int
    title: str
    score: float
    reasons: List[str]


def _get_user_preferred_genres(db: Session, user_id: int) -> List[str]:
    user = db.get(User, user_id)
    if not user or not user.attributes:
        return []
    genres = user.attributes.get("preferred_genres") or []
    if not isinstance(genres, list):
        return []
    return [str(g) for g in genres]


def _normalize(scores: List[float]) -> Dict[int, float]:
    """Normalize a list of scores into [0, 1] by index."""
    if not scores:
        return {}
    max_score = max(scores)
    if max_score <= 0:
        return {idx: 0.0 for idx, _ in enumerate(scores)}
    return {idx: float(s) / max_score for idx, s in enumerate(scores)}


class HybridRecommender:
    """Hybrid recommender combining MF, content-based and popular strategies."""

    def __init__(
        self,
        db: Session,
        mf_recommender: Optional[MFRecommender],
        content_recommender: Optional[ContentRecommender],
        popular_recommender: PopularRecommender,
    ):
        self.db = db
        self.mf_recommender = mf_recommender
        self.content_recommender = content_recommender
        self.popular_recommender = popular_recommender

    def _user_has_interactions(self, user_id: int) -> bool:
        return self.db.query(Interaction.id).filter(Interaction.user_id == user_id).limit(1).first() is not None

    def recommend(self, user_id: int, limit: int = 20) -> List[HybridRecommendation]:
        preferred_genres = _get_user_preferred_genres(self.db, user_id)

        # Collect component recommendations
        mf_recs = (
            self.mf_recommender.recommend(user_id=user_id, limit=limit * 2)
            if self.mf_recommender and self.mf_recommender.is_ready()
            else []
        )
        content_recs = (
            self.content_recommender.recommend(user_id=user_id, limit=limit * 2)
            if self.content_recommender and self.content_recommender.is_ready()
            else []
        )
        popular_recs = self.popular_recommender.recommend(
            user_id=user_id,
            limit=limit * 3,
            preferred_genres=preferred_genres,
        )

        # Fallback ladder for cold-start / missing models
        has_interactions = self._user_has_interactions(user_id)
        if not has_interactions:
            # New user: rely on onboarding preferences + popularity
            logger.info("Hybrid: user %s has no interactions, using onboarding-based popularity.", user_id)
            return self._build_from_single_component(popular_recs, limit, component="popular")

        if not mf_recs and not content_recs:
            # Models unavailable or under-trained: fallback to popularity
            logger.info("Hybrid: no MF or content recs available, falling back to popularity.")
            return self._build_from_single_component(popular_recs, limit, component="popular")

        # Hybrid weighting
        component_weights: Dict[str, float] = {
            "mf": settings.hybrid_weight_mf,
            "content": settings.hybrid_weight_content,
            "popular": settings.hybrid_weight_popular,
        }

        available_components: List[str] = []
        if mf_recs:
            available_components.append("mf")
        if content_recs:
            available_components.append("content")
        if popular_recs:
            available_components.append("popular")

        total_weight = sum(component_weights[c] for c in available_components)
        if total_weight <= 0:
            # Degenerate case: fall back to popularity
            return self._build_from_single_component(popular_recs, limit, component="popular")

        normalized_component_weights = {
            c: component_weights[c] / total_weight for c in available_components
        }

        # Normalize scores within each component
        mf_norm = _normalize([r.score for r in mf_recs])
        content_norm = _normalize([r.score for r in content_recs])
        popular_norm = _normalize([r.score for r in popular_recs])

        # Gather item metadata up front
        item_ids: List[int] = list(
            {
                r.item_id
                for r in (
                    [*mf_recs, *content_recs, *popular_recs]
                )
            }
        )
        items_by_id: Dict[int, Item] = {
            itm.id: itm for itm in self.db.query(Item).filter(Item.id.in_(item_ids)).all()
        }

        combined: Dict[int, HybridComponentScores] = {}

        def ensure_entry(item_id: int) -> HybridComponentScores:
            if item_id not in combined:
                combined[item_id] = HybridComponentScores(reasons=[])
            return combined[item_id]

        # MF contributions
        for idx, r in enumerate(mf_recs):
            entry = ensure_entry(r.item_id)
            entry.mf_score = mf_norm.get(idx, 0.0) * normalized_component_weights.get("mf", 0.0)
            if r.reason:
                entry.reasons.append(r.reason)

        # Content contributions
        for idx, r in enumerate(content_recs):
            entry = ensure_entry(r.item_id)
            entry.content_score = (
                entry.content_score
                + content_norm.get(idx, 0.0) * normalized_component_weights.get("content", 0.0)
            )
            if r.reason:
                entry.reasons.append(r.reason)

        # Popular contributions
        for idx, r in enumerate(popular_recs):
            entry = ensure_entry(r.item_id)
            entry.popular_score = (
                entry.popular_score
                + popular_norm.get(idx, 0.0) * normalized_component_weights.get("popular", 0.0)
            )
            if r.reason:
                entry.reasons.append(r.reason)

        # Build final recommendations, deduplicated
        recommendations: List[HybridRecommendation] = []
        for item_id, comp in combined.items():
            item = items_by_id.get(item_id)
            if not item:
                continue
            total_score = comp.mf_score + comp.content_score + comp.popular_score
            reasons = list(dict.fromkeys(comp.reasons or []))  # de-duplicate while preserving order

            # Add genre-based reason if applicable
            if preferred_genres and item.genres:
                item_genres = {g.strip() for g in item.genres.split("|") if g.strip()}
                overlap = item_genres & {g for g in preferred_genres}
                if overlap:
                    reasons.append(f"Trending in your preferred genres: {', '.join(sorted(overlap))}")

            if not reasons:
                reasons.append("Combined signal from collaborative, content, and popularity models")

            recommendations.append(
                HybridRecommendation(
                    item_id=item_id,
                    title=item.title,
                    score=float(total_score),
                    reasons=reasons,
                )
            )

        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:limit]

    @staticmethod
    def _build_from_single_component(
        recs: Sequence,
        limit: int,
        component: str,
    ) -> List[HybridRecommendation]:
        results: List[HybridRecommendation] = []
        for r in recs[:limit]:
            reasons: List[str] = []
            if getattr(r, "reason", None):
                reasons.append(r.reason)  # type: ignore[arg-type]
            if component == "popular" and "trending" not in " ".join(reasons).lower():
                reasons.append("Trending among many users")
            results.append(
                HybridRecommendation(
                    item_id=r.item_id,
                    title=r.title,
                    score=r.score,
                    reasons=reasons or [f"{component.capitalize()} baseline"],
                )
            )
        return results


def get_hybrid_recommender(db: Session) -> HybridRecommender:
    mf = get_mf_recommender(db)
    content = get_content_recommender(db)
    popular = get_popular_recommender(db)
    return HybridRecommender(db=db, mf_recommender=mf, content_recommender=content, popular_recommender=popular)