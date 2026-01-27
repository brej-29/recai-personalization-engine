from pydantic import BaseModel


class StatsCounts(BaseModel):
    users: int
    items: int
    interactions: int
    active_models: int


class StatsResponse(BaseModel):
    counts: StatsCounts
    request_id: str | None = None