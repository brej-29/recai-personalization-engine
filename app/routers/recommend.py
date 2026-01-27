from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.logging import get_request_id
from app.services.interaction_service import get_or_create_user
from app.db.session import get_db
from app.recommenders.content_tfidf import get_content_recommender
from app.recommenders.hybrid import get_hybrid_recommender
from app.recommenders.mf_implicit import get_mf_recommender
from app.recommenders.popular import get_popular_recommender
from app.schemas.recommendations import RecommendationResponse, RecommendedItem
from app.services.cache_service import (
    get_cached_recommendations,
    set_cached_recommendations,
)
from app.services.ab_testing_service import (
    get_or_create_experiment,
    assign_user_to_experiment,
    log_impression,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

Strategy = str  # literal type alias for readability


@router.get("", response_model=RecommendationResponse)
def recommend(
    user_id: int = Query(..., description="User ID to recommend for"),
    limit: int = Query(20, ge=1, le=200),
    strategy: Strategy = Query(
        "popular",
        pattern="^(popular|content|mf|hybrid)$",
        description="Recommendation strategy: popular | content | mf | hybrid",
    ),
    preferred_genres: list[str] | None = Query(
        default=None,
        description="Optional preferred genres for onboarding / cold-start users",
    ),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    # If caller provides preferred genres, persist them onto the user profile.
    if preferred_genres is not None:
        user = get_or_create_user(db, user_id)
        attrs = dict(user.attributes or {})
        attrs["preferred_genres"] = preferred_genres
        user.attributes = attrs
        db.add(user)
        db.commit()

    # Try cache first (without request_id; we add it per-request).
    cached = get_cached_recommendations(user_id=user_id, strategy=strategy, limit=limit)
    if cached:
        return RecommendationResponse(
            **cached,
            request_id=get_request_id(),
        )

    if strategy == "popular":
        recommender = get_popular_recommender(db)
        recs = recommender.recommend(user_id=user_id, limit=limit, preferred_genres=preferred_genres)
    elif strategy == "content":
        recommender = get_content_recommender(db)
        recs = recommender.recommend(user_id=user_id, limit=limit)
    elif strategy == "mf":
        recommender = get_mf_recommender(db)
        recs = recommender.recommend(user_id=user_id, limit=limit)
    elif strategy == "hybrid":
        recommender = get_hybrid_recommender(db)
        recs = recommender.recommend(user_id=user_id, limit=limit)
    else:  # pragma: no cover - Query pattern guards this
        raise HTTPException(status_code=400, detail="Unknown strategy")

    items: List[RecommendedItem] = [
        RecommendedItem(
            id=r.item_id,
            title=r.title,
            score=r.score,
            strategy=strategy,
            reason=getattr(r, "reason", None),
            reasons=getattr(r, "reasons", None),
        )
        for r in recs
    ]

    payload = {
        "user_id": user_id,
        "strategy": strategy,
        "items": [item.model_dump() for item in items],
    }
    set_cached_recommendations(user_id=user_id, strategy=strategy, limit=limit, data=payload)

    # A/B testing: hybrid_vs_popular experiment, only for matching variant requests
    if strategy in {"hybrid", "popular"}:
        experiment = get_or_create_experiment(db, name="hybrid_vs_popular")
        assignment = assign_user_to_experiment(db, experiment, user_id=user_id)
        if assignment.variant == strategy:
            log_impression(db, experiment, assignment.variant)

    return RecommendationResponse(
        **payload,
        request_id=get_request_id(),
    )