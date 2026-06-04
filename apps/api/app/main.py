"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.observability import install_observability
from app.routes import auth, forecasts, replenishment, uploads
from app.schemas import HealthResponse

_settings = get_settings()

app = FastAPI(title="VyaparSense API", version=__version__)
install_observability(app, level=_settings.log_level)
# CORS outermost (added last) so it answers preflight before anything else. The
# SPA sends cookies, so credentials are allowed and origins are explicit (ADR-003).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
app.include_router(uploads.router)
app.include_router(forecasts.router)
app.include_router(replenishment.router)
app.include_router(auth.router)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)
