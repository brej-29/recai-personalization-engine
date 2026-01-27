from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class UserOnboardRequest(BaseModel):
    user_id: int = Field(..., description="External user identifier")
    preferred_genres: Optional[List[str]] = Field(
        default=None,
        description="List of preferred genres, e.g. ['Action', 'Drama']",
    )
    preferred_keywords: Optional[List[str]] = Field(
        default=None,
        description="Free-text keywords describing interests",
    )


class UserOnboardResponse(BaseModel):
    user_id: int
    status: str
    request_id: str | None = None