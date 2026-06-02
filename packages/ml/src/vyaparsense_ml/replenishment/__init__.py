"""Replenishment: reorder math on top of demand forecasts (``CLAUDE.md`` §4 rung 7).

Converts demand statistics (mean/std per day, from the forecasting layer) into
inventory-control decisions: safety stock, reorder point, EOQ, days of cover,
and periodic-review order-up-to level. Pure formulas, unit-tested, no IO.

    from vyaparsense_ml.replenishment import (
        safety_stock, reorder_point, economic_order_quantity,
        days_of_cover, order_up_to_level, service_level_z,
    )
"""

from __future__ import annotations

from vyaparsense_ml.replenishment.inventory import (
    days_of_cover,
    economic_order_quantity,
    order_up_to_level,
    reorder_point,
    safety_stock,
    service_level_z,
)

__all__ = [
    "days_of_cover",
    "economic_order_quantity",
    "order_up_to_level",
    "reorder_point",
    "safety_stock",
    "service_level_z",
]
