"""Application configuration and settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: Literal["local", "test", "dev", "prod"] = "local"
    log_level: str = Field(default="INFO")
    port: int = Field(default=8000, validation_alias="PORT")

    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/recai",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )

    data_dir: Path = Field(default=Path("data"), validation_alias="DATA_DIR")
    artifact_dir: Path = Field(default=Path("artifacts"), validation_alias="ARTIFACT_DIR")

    # Hybrid recommender weights (normalized at runtime)
    hybrid_weight_mf: float = Field(default=0.55, validation_alias="HYBRID_WEIGHT_MF")
    hybrid_weight_content: float = Field(default=0.35, validation_alias="HYBRID_WEIGHT_CONTENT")
    hybrid_weight_popular: float = Field(default=0.10, validation_alias="HYBRID_WEIGHT_POPULAR")

    # Optional simple rate limiting (per-IP, per-minute)
    rate_limit_enabled: bool = Field(default=False, validation_alias="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_min: int = Field(default=60, validation_alias="RATE_LIMIT_REQUESTS_PER_MIN")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()