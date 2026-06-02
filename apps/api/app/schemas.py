"""API request/response models (pydantic)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel


class UploadSummary(BaseModel):
    upload_id: int
    tenant_id: str
    filename: str
    row_count: int
    series_count: int
    patterns: dict[str, int]


class UploadListItem(BaseModel):
    upload_id: int
    filename: str
    row_count: int
    series_count: int
    status: str


class ForecastItem(BaseModel):
    store_id: str
    sku_id: str
    model: str
    horizon_date: dt.date
    predicted_units: float


class ForecastRunSummary(BaseModel):
    tenant_id: str
    horizon: int
    series_forecast: int
    forecasts_created: int


class AccuracyPointItem(BaseModel):
    period: str
    n: int
    wape: float | None  # None when undefined (zero actual demand in the period)


class HealthResponse(BaseModel):
    status: str
    version: str
