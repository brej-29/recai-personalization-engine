from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    env: str
    version: str
    request_id: str | None = None