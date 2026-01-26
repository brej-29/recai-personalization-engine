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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()