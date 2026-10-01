from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from APP_ environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    name: str = "Production AI Workflow Platform"
    env: str = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, ge=1, le=65535)
    database_url: str = "postgresql+psycopg://platform:platform@localhost:5432/platform"
    database_connect_timeout_seconds: int = Field(default=3, ge=1, le=30)
    kafka_bootstrap_servers: str = ""
    kafka_topic: str = "platform.events"


@lru_cache
def get_settings() -> Settings:
    return Settings()

