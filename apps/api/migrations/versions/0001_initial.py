"""initial schema: tenants, uploads, sales_records, forecasts

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "uploads",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.String(64), sa.ForeignKey("tenants.id"), index=True, nullable=False
        ),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("row_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("series_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "sales_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.String(64), sa.ForeignKey("tenants.id"), index=True, nullable=False
        ),
        sa.Column("upload_id", sa.Integer, sa.ForeignKey("uploads.id"), index=True, nullable=False),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("store_id", sa.String(128), index=True, nullable=False),
        sa.Column("sku_id", sa.String(128), index=True, nullable=False),
        sa.Column("units_sold", sa.Integer, nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("promo_flag", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "forecasts",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.String(64), sa.ForeignKey("tenants.id"), index=True, nullable=False
        ),
        sa.Column("store_id", sa.String(128), index=True, nullable=False),
        sa.Column("sku_id", sa.String(128), index=True, nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("horizon_date", sa.Date, nullable=False),
        sa.Column("predicted_units", sa.Float, nullable=False),
        sa.Column("quantile", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("forecasts")
    op.drop_table("sales_records")
    op.drop_table("uploads")
    op.drop_table("tenants")
