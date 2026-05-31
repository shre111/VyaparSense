"""Persistence helpers. All reads/writes are tenant-scoped (ADR-006)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from vyaparsense_ml.schema import SalesRecord

from app.models import SalesRecordRow, Tenant, Upload


def ensure_tenant(session: Session, tenant_id: str, name: str | None = None) -> Tenant:
    tenant = session.get(Tenant, tenant_id)
    if tenant is None:
        tenant = Tenant(id=tenant_id, name=name or tenant_id)
        session.add(tenant)
        session.flush()
    return tenant


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
