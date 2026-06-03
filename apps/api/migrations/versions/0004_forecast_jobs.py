"""forecast_jobs table (async forecast jobs, ADR-007)

Revision ID: 0004_forecast_jobs
Revises: 0003_refresh_tokens
Create Date: 2026-06-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_forecast_jobs"
down_revision: str | None = "0003_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "forecast_jobs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "tenant_id", sa.String(64), sa.ForeignKey("tenants.id"), index=True, nullable=False
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("horizon", sa.Integer, nullable=False, server_default="7"),
        sa.Column("as_of", sa.Date, nullable=True),
        sa.Column("series_forecast", sa.Integer, nullable=False, server_default="0"),
        sa.Column("forecasts_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_forecast_jobs_status", "forecast_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_forecast_jobs_status", table_name="forecast_jobs")
    op.drop_table("forecast_jobs")
