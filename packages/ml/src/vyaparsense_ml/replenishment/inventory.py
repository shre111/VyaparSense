"""Core replenishment math (Phase 5; ``CLAUDE.md`` §4 rung 7).

Turns demand statistics into the classic inventory-control quantities. These are
the textbook continuous-review (Q,R) formulas; the demand mean/std they consume
come from the forecasting layer (e.g. a forecast's point + spread, or realised
history), so better forecasts flow straight into better reorder decisions.

* :func:`safety_stock` — buffer for demand variability over the lead time at a
  target service level (cycle-service-level / in-stock probability).
* :func:`reorder_point` — the on-hand level that should trigger a new order:
  expected lead-time demand + safety stock.
* :func:`economic_order_quantity` — EOQ, the order size minimising combined
  ordering + holding cost.
* :func:`days_of_cover` — how many days current stock lasts at mean demand.
* :func:`order_up_to_level` — periodic-review target level (R + review period).

All quantities are in demand units (or days). Lead time and review period are in
days and may be fractional. Pure stdlib (``math`` + ``statistics.NormalDist``).
"""

from __future__ import annotations

import math
from statistics import NormalDist


def service_level_z(service_level: float) -> float:
    """Standard-normal quantile (safety factor) for a cycle service level.

    ``service_level`` is the probability of not stocking out during a
    replenishment cycle, in ``(0, 1)``. E.g. ``0.95 -> 1.645``.
    """
    if not 0.0 < service_level < 1.0:
        raise ValueError(f"service_level must be in (0, 1), got {service_level}")
    return NormalDist().inv_cdf(service_level)


def safety_stock(
    demand_std: float,
    lead_time_days: float,
    service_level: float = 0.95,
) -> float:
    """Safety stock = z(service_level) · demand_std · sqrt(lead_time_days).

    ``demand_std`` is the std of demand *per day*; it is scaled to the lead time
    assuming day-to-day demand is independent. Returns a non-negative buffer.
    """
    if demand_std < 0:
        raise ValueError(f"demand_std must be >= 0, got {demand_std}")
    if lead_time_days < 0:
        raise ValueError(f"lead_time_days must be >= 0, got {lead_time_days}")
    z = service_level_z(service_level)
    return z * demand_std * math.sqrt(lead_time_days)


def reorder_point(
    demand_mean: float,
    lead_time_days: float,
    demand_std: float = 0.0,
    service_level: float = 0.95,
) -> float:
    """Reorder point = expected lead-time demand + safety stock.

    ``demand_mean`` is mean demand *per day*. With ``demand_std=0`` this reduces
    to deterministic lead-time demand (no buffer).
    """
    if demand_mean < 0:
        raise ValueError(f"demand_mean must be >= 0, got {demand_mean}")
    if lead_time_days < 0:
        raise ValueError(f"lead_time_days must be >= 0, got {lead_time_days}")
    expected_ltd = demand_mean * lead_time_days
    return expected_ltd + safety_stock(demand_std, lead_time_days, service_level)


def economic_order_quantity(
    annual_demand: float,
    order_cost: float,
    holding_cost_per_unit: float,
) -> float:
    """EOQ = sqrt(2 · annual_demand · order_cost / holding_cost_per_unit).

    ``order_cost`` is the fixed cost per order; ``holding_cost_per_unit`` is the
    cost to hold one unit for the same period as ``annual_demand`` (typically a
    year). Returns the cost-minimising order quantity.
    """
    if annual_demand < 0:
        raise ValueError(f"annual_demand must be >= 0, got {annual_demand}")
    if order_cost < 0:
        raise ValueError(f"order_cost must be >= 0, got {order_cost}")
    if holding_cost_per_unit <= 0:
        raise ValueError(f"holding_cost_per_unit must be > 0, got {holding_cost_per_unit}")
    return math.sqrt(2.0 * annual_demand * order_cost / holding_cost_per_unit)


def days_of_cover(on_hand: float, demand_mean: float) -> float:
    """Days the current stock lasts at mean daily demand (``on_hand / demand_mean``).

    Returns ``inf`` when ``demand_mean`` is 0 (stock never depletes) and the
    stock is positive; ``0.0`` when there is no stock.
    """
    if on_hand < 0:
        raise ValueError(f"on_hand must be >= 0, got {on_hand}")
    if demand_mean < 0:
        raise ValueError(f"demand_mean must be >= 0, got {demand_mean}")
    if on_hand == 0:
        return 0.0
    if demand_mean == 0:
        return math.inf
    return on_hand / demand_mean


def order_up_to_level(
    demand_mean: float,
    lead_time_days: float,
    review_period_days: float,
    demand_std: float = 0.0,
    service_level: float = 0.95,
) -> float:
    """Periodic-review target level S = demand over (lead time + review period) + safety stock.

    For a review-period policy, protection is needed over lead time *plus* the
    review interval, so both the expected demand and the safety stock scale to
    ``lead_time_days + review_period_days``.
    """
    if review_period_days < 0:
        raise ValueError(f"review_period_days must be >= 0, got {review_period_days}")
    protection = lead_time_days + review_period_days
    return reorder_point(demand_mean, protection, demand_std, service_level)
