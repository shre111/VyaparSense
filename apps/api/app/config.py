"""Application settings, loaded from environment (.env in development)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://vyaparsense:vyaparsense@localhost:5432/vyaparsense"
    redis_url: str = "redis://localhost:6379/0"
    api_env: str = "development"

    # Async forecast jobs (ADR-007/011). "inline" runs them in-process via
    # BackgroundTasks (dev/CI, no Redis); "redis" enqueues to an RQ worker.
    forecast_queue: str = "inline"

    # --- Auth (ADR-006). Override auth_secret in production via env. ---
    auth_secret: str = "change-me-in-production"
    auth_jwt_algorithm: str = "HS256"
    #: Short-lived access tokens; longer-lived rotating refresh tokens.
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 30
    #: Per-IP cap on credential attempts (login + signup) per 60s window.
    auth_rate_limit_per_minute: int = 10


def get_settings() -> Settings:
    return Settings()
