from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.logging import get_request_id
from app.db.models import Item
from app.db.session import get_db
from app.recommenders.content_tfidf import get_content_recommender
from app.schemas.items import ItemResponse, SimilarItem, SimilarItemsResponse

router = APIRouter(prefix="/items", tags=["items"])


def _split_genres(genres: str | None) -> List[str] | None:
    if not genres:
        return None
    return [g for g in genres.split("|") if g]


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)) -> ItemResponse:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    return ItemResponse(
        id=item.id,
        title=item.title,
        genres=_split_genres(item.genres),
        text=item.text,
        metadata=item.metadata_,
        request_id=get_request_id(),
    )


@router.get("/{item_id}/similar", response_model=SimilarItemsResponse)
def similar_items(
    item_id: int,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> SimilarItemsResponse:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    recommender = get_content_recommender(db)
    neighbors = recommender.similar_items(item_id=item_id, limit=limit)

    results = [
        SimilarItem(id=n.item_id, title=n.title, score=n.score, reason=n.reason) for n in neighbors
    ]

    return SimilarItemsResponse(item_id=item_id, items=results, request_id=get_request_id())