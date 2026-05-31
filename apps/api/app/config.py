"""Application settings, loaded from environment (.env in development)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://vyaparsense:vyaparsense@localhost:5432/vyaparsense"
    redis_url: str = "redis://localhost:6379/0"
    api_env: str = "development"
    auth_secret: str = "change-me-in-production"


def get_settings() -> Settings:
    return Settings()
