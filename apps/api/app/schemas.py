"""API request/response models (pydantic)."""

from __future__ import annotations

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


class HealthResponse(BaseModel):
    status: str
    version: str
