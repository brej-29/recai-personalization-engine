from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

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

    def recommend(self, user_id: int, limit: int = 20) -> List[PopularRecommendation]:
        # For MVP we simply ignore user_id and return globally popular items.
        rows = (
            self.db.query(
                Interaction.item_id,
                func.count(Interaction.id).label("cnt"),
                func.avg(Interaction.rating).label("avg_rating"),
            )
            .group_by(Interaction.item_id)
            .order_by(func.count(Interaction.id).desc())
            .limit(limit)
            .all()
        )

        item_ids = [r.item_id for r in rows]
        items_by_id = {
            item.id: item
            for item in self.db.query(Item).filter(Item.id.in_(item_ids)).all()
        }

        recs: List[PopularRecommendation] = []
        for r in rows:
            item = items_by_id.get(r.item_id)
            if not item:
                continue
            score = float(r.cnt or 0)
            reason = f"Popular item with {int(r.cnt or 0)} interactions"
            recs.append(
                PopularRecommendation(
                    item_id=item.id,
                    title=item.title,
                    score=score,
                    reason=reason,
                )
            )
        return recs


def get_popular_recommender(db: Session) -> PopularRecommender:
    return PopularRecommender(db=db)