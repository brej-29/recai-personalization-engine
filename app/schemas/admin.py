from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
    event_type: str
    rating: Optional[float] = None
    ts: Optional[datetime] = None


class TrackEventResponse(BaseModel):
    status: str
    request_id: str | None = None