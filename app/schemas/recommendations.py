from typing import List, Optional

from pydantic import BaseModel


class RecommendedItem(BaseModel):
    id: int
    title: str
    score: float
    strategy: str
    reason: Optional[str] = None


class RecommendationResponse(BaseModel):
    user_id: int
    strategy: str
    items: List[RecommendedItem]
    request_id: str | None = None