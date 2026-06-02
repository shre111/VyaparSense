"""Persistence helpers. All reads/writes are tenant-scoped (ADR-006)."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from vyaparsense_ml.schema import SalesRecord

from app.forecasting import ForecastRow
from app.models import Forecast, RefreshToken, SalesRecordRow, Tenant, Upload, User

SeriesKey = tuple[str, str]


def ensure_tenant(session: Session, tenant_id: str, name: str | None = None) -> Tenant:
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        tenant = Tenant(id=tenant_id, name=name or tenant_id)
        session.add(tenant)
        session.flush()
    return tenant


def get_user_by_email(session: Session, email: str) -> User | None:
    """Look up a user by (lower-cased) email; None if not found."""
    stmt = select(User).where(User.email == email.strip().lower())
    return session.scalars(stmt).first()


def get_user(session: Session, user_id: int) -> User | None:
    """Look up a user by id; None if not found."""
    return session.get(User, user_id)


def create_user(session: Session, *, tenant_id: str, email: str, password_hash: str) -> User:
    """Create a user under a tenant (creating the tenant if needed).

    Caller must ensure the email is not already taken (see
    :func:`get_user_by_email`); the DB also enforces a unique constraint.
    """
    ensure_tenant(session, tenant_id)
    user = User(
        tenant_id=tenant_id,
        email=email.strip().lower(),
        password_hash=password_hash,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def record_refresh_jti(session: Session, *, user_id: int, jti: str) -> None:
    """Record an issued refresh token's jti for a user (rotation tracking)."""
    session.add(RefreshToken(user_id=user_id, jti=jti, revoked=False))
    session.commit()


def get_refresh_token(session: Session, jti: str) -> RefreshToken | None:
    """Look up a stored refresh token by its jti; None if never issued."""
    return session.scalars(select(RefreshToken).where(RefreshToken.jti == jti)).first()


def revoke_refresh_jti(session: Session, jti: str) -> None:
    """Mark a single refresh token revoked (the normal rotation step)."""
    row = get_refresh_token(session, jti)
    if row is not None and not row.revoked:
        row.revoked = True
        session.commit()


def revoke_all_user_refresh(session: Session, user_id: int) -> int:
    """Revoke every outstanding refresh token for a user (reuse-detection
    response / global logout). Returns how many were revoked."""
    rows = session.scalars(
        select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
    ).all()
    for row in rows:
        row.revoked = True
    if rows:
        session.commit()
    return len(rows)


def store_upload(
    session: Session,
    *,
    tenant_id: str,
    filename: str,
    records: list[SalesRecord],
    series_count: int,
) -> Upload:
    """Persist an upload and its cleaned sales records for one tenant."""
    ensure_tenant(session, tenant_id)
    upload = Upload(
        tenant_id=tenant_id,
        filename=filename,
        row_count=len(records),
        series_count=series_count,
        status="completed",
    )
    session.add(upload)
    session.flush()  # assign upload.id

    session.add_all(
        SalesRecordRow(
            tenant_id=tenant_id,
            upload_id=upload.id,
            date=r.date,
            store_id=r.store_id,
            sku_id=r.sku_id,
            units_sold=r.units_sold,
            price=r.price,
            promo_flag=r.promo_flag,
        )
        for r in records
    )
    session.commit()
    return upload


def list_uploads(session: Session, tenant_id: str) -> list[Upload]:
    stmt = select(Upload).where(Upload.tenant_id == tenant_id).order_by(Upload.id)
    return list(session.scalars(stmt))


def count_sales(session: Session, tenant_id: str) -> int:
    stmt = (
        select(func.count())
        .select_from(SalesRecordRow)
        .where(SalesRecordRow.tenant_id == tenant_id)
    )
    return int(session.scalar(stmt) or 0)


def load_series(session: Session, tenant_id: str) -> dict[SeriesKey, list[tuple[dt.date, int]]]:
    """Load a tenant's sales as per-series ``(date, units)`` lists, date-sorted.

    Mirrors the shape of :func:`vyaparsense_ml.cleaning.to_series` so the
    forecasting service can consume it directly.
    """
    stmt = (
        select(
            SalesRecordRow.store_id,
            SalesRecordRow.sku_id,
            SalesRecordRow.date,
            SalesRecordRow.units_sold,
        )
        .where(SalesRecordRow.tenant_id == tenant_id)
        .order_by(SalesRecordRow.store_id, SalesRecordRow.sku_id, SalesRecordRow.date)
    )
    series: dict[SeriesKey, list[tuple[dt.date, int]]] = {}
    for store_id, sku_id, date, units in session.execute(stmt):
        series.setdefault((store_id, sku_id), []).append((date, units))
    return series


def store_forecasts(session: Session, tenant_id: str, rows: list[ForecastRow]) -> int:
    """Append forecast rows for a tenant (ADR-008: insert-only). Returns count."""
    session.add_all(
        Forecast(
            tenant_id=tenant_id,
            store_id=r.store_id,
            sku_id=r.sku_id,
            model=r.model,
            horizon_date=r.horizon_date,
            predicted_units=r.predicted_units,
            quantile=None,
        )
        for r in rows
    )
    session.commit()
    return len(rows)


def list_forecasts(
    session: Session,
    tenant_id: str,
    *,
    store_id: str | None = None,
    sku_id: str | None = None,
) -> list[Forecast]:
    """List a tenant's forecasts, newest first, optionally filtered by series."""
    stmt = select(Forecast).where(Forecast.tenant_id == tenant_id)
    if store_id is not None:
        stmt = stmt.where(Forecast.store_id == store_id)
    if sku_id is not None:
        stmt = stmt.where(Forecast.sku_id == sku_id)
    stmt = stmt.order_by(Forecast.created_at.desc(), Forecast.id.desc())
    return list(session.scalars(stmt))


def forecast_actual_pairs(session: Session, tenant_id: str) -> list[tuple[dt.date, float, float]]:
    """Join a tenant's point forecasts to realised actuals for accuracy scoring.

    Matches each point forecast (``quantile IS NULL``) to the realised
    ``sales_records`` demand on the same ``(store, sku, date)``. Returns
    ``(horizon_date, predicted_units, actual_units)`` for every forecast that has
    a realised actual — the raw material for accuracy-over-time. Keyed by the
    *horizon date* (the day forecast) so the rolling WAPE is plotted against the
    period being predicted, and a backfill spreads across the calendar.
    """
    stmt = (
        select(
            Forecast.horizon_date,
            Forecast.predicted_units,
            SalesRecordRow.units_sold,
        )
        .join(
            SalesRecordRow,
            (SalesRecordRow.tenant_id == Forecast.tenant_id)
            & (SalesRecordRow.store_id == Forecast.store_id)
            & (SalesRecordRow.sku_id == Forecast.sku_id)
            & (SalesRecordRow.date == Forecast.horizon_date),
        )
        .where(Forecast.tenant_id == tenant_id, Forecast.quantile.is_(None))
    )
    return [
        (horizon_date, float(predicted), float(actual))
        for horizon_date, predicted, actual in session.execute(stmt)
    ]
