"""Inventory-policy simulation & business KPIs (Phase 5; ``CLAUDE.md`` §5).

Replays a continuous-review (s, S) reorder policy day by day over a realised
demand series and reports the business KPIs that make the case study — stockout
rate, fill rate, dead-stock value, inventory turns. This is how we put a number
on "dead stock ↓, stockouts ↓": run the same demand through a naive policy vs. a
forecast-driven one and compare.

Policy per simulated day:

1. **Receive** any order whose lead time has elapsed.
2. **Demand** hits; sales are capped at on-hand (the rest is a lost-sales
   stockout — we do not backorder).
3. **Review**: if the inventory position (on-hand + on-order) has fallen to or
   below the reorder point ``s``, place an order bringing the position up to the
   order-up-to level ``S`` (or by a fixed ``order_quantity`` if given), arriving
   after ``lead_time_days``.

KPIs (see :class:`SimulationResult`) are computed over the simulated horizon.
Pure stdlib; deterministic given its inputs.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationResult:
    """Business KPIs from one policy simulation over a demand series.

    * ``fill_rate`` — units sold / units demanded (demand-weighted service).
    * ``stockout_rate`` — fraction of days with any unmet demand.
    * ``service_level`` — fraction of days with no stockout (cycle service).
    * ``avg_on_hand`` — mean end-of-day on-hand.
    * ``dead_stock_value`` — on-hand units that sat through stretches with no
      sale (≥ ``dead_stock_days`` consecutive), valued at ``unit_cost``: the cash
      frozen on slow movers.
    * ``inventory_turns`` — total units sold / average on-hand over the horizon.
    """

    days: int
    units_demanded: float
    units_sold: float
    units_lost: float
    fill_rate: float
    stockout_days: int
    stockout_rate: float
    service_level: float
    avg_on_hand: float
    dead_stock_value: float
    inventory_turns: float
    n_orders: int


def simulate_policy(
    demand: Sequence[float],
    *,
    reorder_point: float,
    order_up_to: float | None = None,
    order_quantity: float | None = None,
    lead_time_days: int,
    initial_on_hand: float,
    unit_cost: float = 0.0,
    dead_stock_days: int = 30,
) -> SimulationResult:
    """Simulate a continuous-review (s, S) policy over realised ``demand``.

    Exactly one of ``order_up_to`` (order-up-to-S) or ``order_quantity``
    (fixed-Q) must be given. ``dead_stock_days`` defines "dead stock": stock that
    has sat without a sale for at least this many consecutive days counts toward
    dead-stock value (at ``unit_cost``).

    Raises:
        ValueError: invalid params (bad policy spec, negative inputs, empty demand).
    """
    if not demand:
        raise ValueError("demand series is empty")
    if lead_time_days < 1:
        raise ValueError(f"lead_time_days must be >= 1, got {lead_time_days}")
    if initial_on_hand < 0:
        raise ValueError(f"initial_on_hand must be >= 0, got {initial_on_hand}")
    if reorder_point < 0:
        raise ValueError(f"reorder_point must be >= 0, got {reorder_point}")
    if (order_up_to is None) == (order_quantity is None):
        raise ValueError("provide exactly one of order_up_to or order_quantity")
    if order_up_to is not None and order_up_to < reorder_point:
        raise ValueError(f"order_up_to ({order_up_to}) must be >= reorder_point ({reorder_point})")
    if order_quantity is not None and order_quantity <= 0:
        raise ValueError(f"order_quantity must be > 0, got {order_quantity}")
    if unit_cost < 0:
        raise ValueError(f"unit_cost must be >= 0, got {unit_cost}")
    if dead_stock_days < 1:
        raise ValueError(f"dead_stock_days must be >= 1, got {dead_stock_days}")

    on_hand = float(initial_on_hand)
    pipeline: list[tuple[int, float]] = []  # (arrival_day_index, qty)
    units_demanded = 0.0
    units_sold = 0.0
    stockout_days = 0
    on_hand_sum = 0.0
    dead_stock_units = 0.0
    n_orders = 0
    days_since_sale = 0

    for day, raw in enumerate(demand):
        d = float(raw)
        if d < 0:
            raise ValueError(f"demand must be >= 0, got {d} at index {day}")

        # 1. receive arrivals due today
        if pipeline:
            arrived = [q for a, q in pipeline if a == day]
            if arrived:
                on_hand += sum(arrived)
                pipeline = [(a, q) for a, q in pipeline if a != day]

        # 2. demand (lost sales, no backorder)
        units_demanded += d
        sold = min(on_hand, d)
        units_sold += sold
        on_hand -= sold
        if sold < d:
            stockout_days += 1

        # dead-stock accrual: stock held through a stretch with no sales
        days_since_sale = 0 if sold > 0 else days_since_sale + 1
        if days_since_sale >= dead_stock_days:
            dead_stock_units += on_hand

        # 3. review & reorder on inventory position
        on_order = sum(q for _, q in pipeline)
        position = on_hand + on_order
        if position <= reorder_point:
            if order_up_to is not None:
                qty = order_up_to - position
            else:
                assert order_quantity is not None
                qty = order_quantity
            if qty > 0:
                pipeline.append((day + lead_time_days, qty))
                n_orders += 1

        on_hand_sum += on_hand

    n = len(demand)
    units_lost = units_demanded - units_sold
    fill_rate = 1.0 if units_demanded == 0 else units_sold / units_demanded
    avg_on_hand = on_hand_sum / n
    inventory_turns = 0.0 if avg_on_hand == 0 else units_sold / avg_on_hand
    return SimulationResult(
        days=n,
        units_demanded=units_demanded,
        units_sold=units_sold,
        units_lost=units_lost,
        fill_rate=fill_rate,
        stockout_days=stockout_days,
        stockout_rate=stockout_days / n,
        service_level=1.0 - stockout_days / n,
        avg_on_hand=avg_on_hand,
        dead_stock_value=dead_stock_units * unit_cost,
        inventory_turns=inventory_turns,
        n_orders=n_orders,
    )
