from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.logging import get_request_id
from app.db.session import get_db
from app.recommenders.content_tfidf import get_content_recommender
from app.recommenders.mf_implicit import get_mf_recommender
from app.recommenders.popular import get_popular_recommender
from app.schemas.recommendations import RecommendationResponse, RecommendedItem
from app.services.cache_service import (
    get_cached_recommendations,
    set_cached_recommendations,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

Strategy = str  # literal type alias for readability


@router.get("", response_model=RecommendationResponse)
def recommend(
    user_id: int = Query(..., description="User ID to recommend for"),
    limit: int = Query(20, ge=1, le=200),
    strategy: Strategy = Query(
        "popular",
        pattern="^(popular|content|mf)$",
        description="Recommendation strategy: popular | content | mf",
    ),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    # Try cache first (without request_id; we add it per-request).
    cached = get_cached_recommendations(user_id=user_id, strategy=strategy, limit=limit)
    if cached:
        return RecommendationResponse(
            **cached,
            request_id=get_request_id(),
        )

    if strategy == "popular":
        recommender = get_popular_recommender(db)
        recs = recommender.recommend(user_id=user_id, limit=limit)
    elif strategy == "content":
        recommender = get_content_recommender(db)
        recs = recommender.recommend(user_id=user_id, limit=limit)
    elif strategy == "mf":
        recommender = get_mf_recommender(db)
        recs = recommender.recommend(user_id=user_id, limit=limit)
    else:  # pragma: no cover - Query pattern guards this
        raise HTTPException(status_code=400, detail="Unknown strategy")

    items: List[RecommendedItem] = [
        RecommendedItem(
            id=r.item_id,
            title=r.title,
            score=r.score,
            strategy=strategy,
            reason=r.reason,
        )
        for r in recs
    ]

    payload = {
        "user_id": user_id,
        "strategy": strategy,
        "items": [item.dict() for item in items],
    }
    set_cached_recommendations(user_id=user_id, strategy=strategy, limit=limit, data=payload)

    return RecommendationResponse(
        **payload,
        request_id=get_request_id(),
    )