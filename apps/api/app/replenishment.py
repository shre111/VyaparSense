"""Replenishment service: reorder suggestions & policy KPIs over stored sales.

Bridges the API's persisted sales to the ``packages/ml`` replenishment engine.
For each ``(store, sku)`` series it produces a service-level reorder suggestion
(``suggest_reorder``) and, for the KPI view, simulates a forecast-driven policy
vs. a naive one (``simulate_policy``) to surface the before/after business
numbers (fill rate, stockouts, dead stock, turns).

Inventory parameters that the DB does not yet hold — lead time, on-hand,
service level, unit cost — are supplied by the caller (endpoint query params)
with sensible defaults. Persisting per-SKU inventory params is a later schema
change.

Uses the fast stdlib baselines (the request path); heavier models stay in the
async worker (ADR-007).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from statistics import mean, pstdev

from vyaparsense_ml.forecasting.models import MovingAverage
from vyaparsense_ml.replenishment.inventory import order_up_to_level, reorder_point
from vyaparsense_ml.replenishment.simulation import simulate_policy
from vyaparsense_ml.replenishment.suggestions import suggest_reorder

SeriesKey = tuple[str, str]

# Minimum history for the empirical-quantile reorder suggestion to be meaningful.
_MIN_HISTORY = 14


@dataclass(frozen=True)
class ReorderRow:
    """A reorder recommendation for one series (flattened ReorderSuggestion)."""

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


@dataclass(frozen=True)
class KpiComparison:
    """Forecast-driven vs naive policy KPIs, pooled across series."""

    series_simulated: int
    naive_fill_rate: float
    forecast_fill_rate: float
    naive_units_lost: float
    forecast_units_lost: float
    lost_sales_reduction_pct: float
    naive_avg_on_hand: float
    forecast_avg_on_hand: float


def reorder_suggestions(
    series: dict[SeriesKey, list[tuple[dt.date, int]]],
    *,
    lead_time_days: int,
    service_level: float = 0.95,
    on_hand: float = 0.0,
) -> list[ReorderRow]:
    """Per-series service-level reorder suggestions over the stored sales.

    Series with fewer than ``_MIN_HISTORY`` points are skipped (too little
    history to estimate the demand spread). Uses ``MovingAverage(7)`` as the
    point model behind the empirical-quantile suggestion.
    """
    rows: list[ReorderRow] = []
    for (store_id, sku_id), points in sorted(series.items()):
        if len(points) < _MIN_HISTORY:
            continue
        units = [float(u) for _, u in points]
        suggestion = suggest_reorder(
            MovingAverage(window=7),
            units,
            lead_time_days=lead_time_days,
            service_level=service_level,
            on_hand=on_hand,
        )
        rows.append(
            ReorderRow(
                store_id=store_id,
                sku_id=sku_id,
                service_level=suggestion.service_level,
                lead_time_days=suggestion.lead_time_days,
                on_hand=suggestion.on_hand,
                reorder_point=suggestion.reorder_point,
                safety_stock=suggestion.safety_stock,
                should_reorder=suggestion.should_reorder,
                order_quantity=suggestion.order_quantity,
                days_of_cover=suggestion.days_of_cover,
            )
        )
    return rows


def _pooled_fill_rate(demanded: float, lost: float) -> float:
    return 1.0 if demanded == 0 else (demanded - lost) / demanded


def policy_kpis(
    series: dict[SeriesKey, list[tuple[dt.date, int]]],
    *,
    lead_time_days: int,
    service_level: float = 0.95,
    unit_cost: float = 1.0,
) -> KpiComparison:
    """Simulate naive vs forecast-driven (s,S) policies and pool the KPIs.

    For each series: the naive policy uses lead-time mean demand as its reorder
    point (no safety stock); the forecast-driven policy adds service-level safety
    stock. Both are simulated over the realised demand; results are pooled.
    Series shorter than ``_MIN_HISTORY`` are skipped.
    """
    n = 0
    nd_demand = nd_lost = nd_onhand = 0.0
    fc_demand = fc_lost = fc_onhand = 0.0

    for _key, points in series.items():
        units = [float(u) for _, u in points]
        if len(units) < _MIN_HISTORY:
            continue
        mu, sigma = mean(units), pstdev(units)
        review = 7  # weekly review cadence

        rp_naive = reorder_point(mu, lead_time_days, demand_std=0.0)
        s_naive = order_up_to_level(mu, lead_time_days, review, demand_std=0.0)
        rp_fc = reorder_point(mu, lead_time_days, demand_std=sigma, service_level=service_level)
        s_fc = order_up_to_level(
            mu, lead_time_days, review, demand_std=sigma, service_level=service_level
        )

        naive = simulate_policy(
            units,
            reorder_point=rp_naive,
            order_up_to=s_naive,
            lead_time_days=lead_time_days,
            initial_on_hand=rp_naive,
            unit_cost=unit_cost,
        )
        forecast = simulate_policy(
            units,
            reorder_point=rp_fc,
            order_up_to=s_fc,
            lead_time_days=lead_time_days,
            initial_on_hand=rp_fc,
            unit_cost=unit_cost,
        )
        n += 1
        nd_demand += naive.units_demanded
        nd_lost += naive.units_lost
        nd_onhand += naive.avg_on_hand
        fc_demand += forecast.units_demanded
        fc_lost += forecast.units_lost
        fc_onhand += forecast.avg_on_hand

    naive_fill = _pooled_fill_rate(nd_demand, nd_lost)
    fc_fill = _pooled_fill_rate(fc_demand, fc_lost)
    reduction = 0.0 if nd_lost == 0 else (nd_lost - fc_lost) / nd_lost
    return KpiComparison(
        series_simulated=n,
        naive_fill_rate=naive_fill,
        forecast_fill_rate=fc_fill,
        naive_units_lost=nd_lost,
        forecast_units_lost=fc_lost,
        lost_sales_reduction_pct=reduction,
        naive_avg_on_hand=nd_onhand / n if n else 0.0,
        forecast_avg_on_hand=fc_onhand / n if n else 0.0,
    )
