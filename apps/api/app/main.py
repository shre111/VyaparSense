"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.routes import forecasts, replenishment, uploads
from app.schemas import HealthResponse

app = FastAPI(title="VyaparSense API", version=__version__)
app.include_router(uploads.router)
app.include_router(forecasts.router)
app.include_router(replenishment.router)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)
