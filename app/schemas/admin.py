from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ModelVersionResponse(BaseModel):
    id: int
    name: str
    version: str
    trained_at: datetime
    metrics: Optional[Dict[str, Any]] = None
    path: str
    is_active: bool


class TrainResponse(BaseModel):
    model: str
    status: str
    details: Optional[Dict[str, Any]] = None
    request_id: str | None = None


class TrackEventRequest(BaseModel):
    user_id: int
    item_id: int
    event_type: Literal["view", "click", "rate"]
    rating: Optional[float] = None
    ts: Optional[datetime] = None


class TrackEventResponse(BaseModel):
    status: str
    request_id: str | None = None


class AdminCreateItemRequest(BaseModel):
    title: str = Field(..., max_length=512)
    genres: Optional[List[str]] = None
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    explicit_id: Optional[int] = Field(
        default=None,
        description="Optional explicit item id. If omitted, an auto-increment id is used.",
    )


class AdminCreateItemResponse(BaseModel):
    id: int
    title: str
    genres: Optional[str] = None
    text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    request_id: str | None = None


class ExperimentSummary(BaseModel):
    name: str
    status: str
    created_at: datetime
    config: Dict[str, Any]


class ExperimentCreateResponse(BaseModel):
    experiment: ExperimentSummary
    request_id: str | None = None


class ExperimentReportVariant(BaseModel):
    variant: str
    impressions: int
    clicks: int
    ctr: float


class ExperimentReportResponse(BaseModel):
    name: str
    status: str
    variants: List[ExperimentReportVariant]
    request_id: str | None = None