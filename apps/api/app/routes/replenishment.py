"""Replenishment endpoints: reorder suggestions and policy KPIs.

Surfaces the ``packages/ml`` replenishment engine over a tenant's stored sales.
Inventory parameters not yet in the schema (lead time, on-hand, service level,
unit cost) are taken as query params with sensible defaults.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app import repository
from app.deps import CurrentTenant, SessionDep
from app.replenishment import policy_kpis, reorder_suggestions
from app.schemas import KpiComparisonResponse, ReorderItem

router = APIRouter(tags=["replenishment"])

LeadTime = Annotated[int, Query(ge=1, le=90)]
ServiceLevel = Annotated[float, Query(gt=0.0, lt=1.0)]
OnHand = Annotated[float, Query(ge=0.0)]
UnitCost = Annotated[float, Query(ge=0.0)]


@router.get("/reorder-suggestions", response_model=list[ReorderItem])
def get_reorder_suggestions(
    session: SessionDep,
    tenant_id: CurrentTenant,
    lead_time_days: LeadTime = 7,
    service_level: ServiceLevel = 0.95,
    on_hand: OnHand = 0.0,
) -> list[ReorderItem]:
    """Per-series service-level reorder suggestions over the tenant's sales."""
    series = repository.load_series(session, tenant_id)
    rows = reorder_suggestions(
        series,
        lead_time_days=lead_time_days,
        service_level=service_level,
        on_hand=on_hand,
    )
    return [
        ReorderItem(
            store_id=r.store_id,
            sku_id=r.sku_id,
            service_level=r.service_level,
            lead_time_days=r.lead_time_days,
            on_hand=r.on_hand,
            reorder_point=r.reorder_point,
            safety_stock=r.safety_stock,
            should_reorder=r.should_reorder,
            order_quantity=r.order_quantity,
            days_of_cover=r.days_of_cover,
        )
        for r in rows
    ]


@router.get("/simulation-kpis", response_model=KpiComparisonResponse)
def get_simulation_kpis(
    session: SessionDep,
    tenant_id: CurrentTenant,
    lead_time_days: LeadTime = 7,
    service_level: ServiceLevel = 0.95,
    unit_cost: UnitCost = 1.0,
) -> KpiComparisonResponse:
    """Before/after KPIs: naive vs forecast-driven policy over realised demand."""
    series = repository.load_series(session, tenant_id)
    kpis = policy_kpis(
        series,
        lead_time_days=lead_time_days,
        service_level=service_level,
        unit_cost=unit_cost,
    )
    return KpiComparisonResponse(
        series_simulated=kpis.series_simulated,
        naive_fill_rate=kpis.naive_fill_rate,
        forecast_fill_rate=kpis.forecast_fill_rate,
        naive_units_lost=kpis.naive_units_lost,
        forecast_units_lost=kpis.forecast_units_lost,
        lost_sales_reduction_pct=kpis.lost_sales_reduction_pct,
        naive_avg_on_hand=kpis.naive_avg_on_hand,
        forecast_avg_on_hand=kpis.forecast_avg_on_hand,
    )
