"""SQLAlchemy models.

Multi-tenant from day one (ADR-006): every business table carries ``tenant_id``.
Forecasts are append-only (ADR-008): rows are inserted, never updated, so the
"getting smarter" accuracy-over-time chart is always reconstructable.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    uploads: Mapped[list[Upload]] = relationship(back_populates="tenant")


class User(Base):
    """An authenticated user, scoped to a tenant (ADR-006).

    ``password_hash`` is an Argon2id encoded hash (never the plaintext); see
    ``app.security``. Email is unique across the system and stored lower-cased.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class RefreshToken(Base):
    """One issued refresh token, tracked by its ``jti`` for rotation + reuse
    detection (ADR-006).

    On refresh, the presented token's row is marked ``revoked`` and a new row is
    issued. Presenting an already-revoked jti is a reuse signal → revoke every
    outstanding token for that user (force re-login).
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    filename: Mapped[str] = mapped_column(String(512))
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    series_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tenant: Mapped[Tenant] = relationship(back_populates="uploads")
    sales: Mapped[list[SalesRecordRow]] = relationship(back_populates="upload")


class SalesRecordRow(Base):
    __tablename__ = "sales_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("uploads.id"), index=True)
    date: Mapped[dt.date] = mapped_column(Date)
    store_id: Mapped[str] = mapped_column(String(128), index=True)
    sku_id: Mapped[str] = mapped_column(String(128), index=True)
    units_sold: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Float)
    promo_flag: Mapped[bool] = mapped_column(Boolean, default=False)

    upload: Mapped[Upload] = relationship(back_populates="sales")


class ForecastJob(Base):
    """An async forecast-generation job (ADR-007).

    Forecasting/backtesting over many SKUs is too slow for an HTTP request, so a
    ``POST`` enqueues a job and the client polls this row for status. ``status``
    moves ``queued`` → ``running`` → ``completed`` | ``failed``; on success the
    counts mirror the produced forecasts, on failure ``error`` carries the reason.
    """

    __tablename__ = "forecast_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    horizon: Mapped[int] = mapped_column(Integer, default=7)
    as_of: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    series_forecast: Mapped[int] = mapped_column(Integer, default=0)
    forecasts_created: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Forecast(Base):
    """Append-only forecast records (ADR-008). Never updated."""

    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    store_id: Mapped[str] = mapped_column(String(128), index=True)
    sku_id: Mapped[str] = mapped_column(String(128), index=True)
    model: Mapped[str] = mapped_column(String(64))
    horizon_date: Mapped[dt.date] = mapped_column(Date)
    predicted_units: Mapped[float] = mapped_column(Float)
    quantile: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
