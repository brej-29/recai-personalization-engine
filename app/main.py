from fastapi import FastAPI

from app.core.config import get_settings
from app.core.error_handler import init_error_handlers
from app.core.logging import configure_logging, logging_middleware
from app.routers import api_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(
        title="RecAI Personalization Engine",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.middleware("http")(logging_middleware)
    init_error_handlers(app)

    app.include_router(api_router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "RecAI Personalization Engine", "env": settings.env}

    @app.on_event("startup")
    async def on_startup() -> None:
        # Optionally train models on startup when configured (no-op if disabled).
        from app.services.auto_train import ensure_models_trained_if_missing

        ensure_models_trained_if_missing()

    return app


app = create_app()