from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Interaction, Item


@dataclass
class PopularRecommendation:
    item_id: int
    title: str
    score: float
    reason: Optional[str] = None


class PopularRecommender:
    def __init__(self, db: Session):
        self.db = db

    def recommend(
        self,
        user_id: int,
        limit: int = 20,
        preferred_genres: Optional[Sequence[str]] = None,
    ) -> List[PopularRecommendation]:
        # For MVP we simply ignore user_id and return globally popular items,
        # optionally prioritising items in the user's preferred genres.
        rows = (
            self.db.query(
                Interaction.item_id,
                func.count(Interaction.id).label("cnt"),
                func.avg(Interaction.rating).label("avg_rating"),
            )
            .group_by(Interaction.item_id)
            .order_by(func.count(Interaction.id).desc())
            .limit(limit * 3)
            .all()
        )

        item_ids = [r.item_id for r in rows]
        items_by_id = {
            item.id: item for item in self.db.query(Item).filter(Item.id.in_(item_ids)).all()
        }

        preferred_genres_set = {g.lower() for g in preferred_genres or []}

        def in_preferred_genres(item: Item) -> bool:
            if not preferred_genres_set or not item.genres:
                return False
            genres = {g.strip().lower() for g in item.genres.split("|") if g.strip()}
            return bool(preferred_genres_set & genres)

        prioritized: List[PopularRecommendation] = []
        fallback: List[PopularRecommendation] = []

        for r in rows:
            item = items_by_id.get(r.item_id)
            if not item:
                continue
            score = float(r.cnt or 0)
            base_reason = f"Popular item with {int(r.cnt or 0)} interactions"
            if in_preferred_genres(item):
                reason = base_reason + " (in your preferred genres)"
                prioritized.append(
                    PopularRecommendation(
                        item_id=item.id,
                        title=item.title,
                        score=score,
                        reason=reason,
                    )
                )
            else:
                fallback.append(
                    PopularRecommendation(
                        item_id=item.id,
                        title=item.title,
                        score=score,
                        reason=base_reason,
                    )
                )

        recs: List[PopularRecommendation] = []
        for rec_list in (prioritized, fallback):
            for rec in rec_list:
                if len(recs) >= limit:
                    break
                recs.append(rec)
            if len(recs) >= limit:
                break
        return recs


def get_popular_recommender(db: Session) -> PopularRecommender:
    return PopularRecommender(db=db)