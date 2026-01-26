from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ItemBase(BaseModel):
    id: int
    title: str
    genres: List[str] | None = None
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ItemResponse(ItemBase):
    request_id: str | None = None


class SimilarItem(BaseModel):
    id: int
    title: str
    score: float
    reason: str | None = None


class SimilarItemsResponse(BaseModel):
    item_id: int
    items: List[SimilarItem]
    request_id: str | None = None