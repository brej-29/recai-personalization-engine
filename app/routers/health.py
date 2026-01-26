from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings
from app.core.logging import get_request_id
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        env=settings.env,
        version=__version__,
        request_id=get_request_id(),
    )