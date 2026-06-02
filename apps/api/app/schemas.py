"""API request/response models (pydantic)."""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


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


class ReorderItem(BaseModel):
    store_id: str
    sku_id: str
    service_level: float
    lead_time_days: int
    on_hand: float
    reorder_point: float
    safety_stock: float
    should_reorder: bool
    order_quantity: float
    days_of_cover: float


class KpiComparisonResponse(BaseModel):
    series_simulated: int
    naive_fill_rate: float
    forecast_fill_rate: float
    naive_units_lost: float
    forecast_units_lost: float
    lost_sales_reduction_pct: float
    naive_avg_on_hand: float
    forecast_avg_on_hand: float


class SignupRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=1024)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class AuthResponse(BaseModel):
    """Login/signup result: the access token in the body; refresh set as a cookie."""

    access_token: str
    token_type: str = "bearer"
    user_id: int
    tenant_id: str
    email: str


class HealthResponse(BaseModel):
    status: str
    version: str
