"""Service-level reorder suggestions (Phase 5; ``CLAUDE.md`` §4 rung 7).

Where :mod:`vyaparsense_ml.replenishment.inventory` does the classic
normal-approximation math, this module turns the project's *probabilistic*
forecasts into reorder decisions — the payoff of the Phase 3 quantile work. A
service-level target maps directly to a demand **quantile**: the reorder point at
a 95% service level is the 0.95 quantile of demand over the protection window
(lead time + review period), no normality assumption required.

* :class:`ReorderSuggestion` — the bundled recommendation (reorder point, safety
  stock, order quantity, days of cover, whether to reorder now).
* :func:`build_reorder_suggestion` — pure core over already-forecast demand
  paths (a median path and a service-level-quantile path); trivially testable.
* :func:`suggest_reorder` — convenience that wraps any point
  :class:`~vyaparsense_ml.forecasting.models.Baseline` in an
  :class:`~vyaparsense_ml.forecasting.quantile.EmpiricalQuantileForecaster` and
  forecasts the protection window for you.

**Quantile-sum approximation (documented):** the reorder point sums the per-day
service-level quantiles over the protection window. The true quantile of *total*
demand is not the sum of daily quantiles unless days are perfectly correlated;
the sum is the standard, slightly conservative practitioner choice and keeps the
math transparent. Pure stdlib here; the convenience helper pulls in the
forecasting layer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from vyaparsense_ml.forecasting.models import Baseline
from vyaparsense_ml.forecasting.quantile import EmpiricalQuantileForecaster
from vyaparsense_ml.replenishment.inventory import days_of_cover


@dataclass(frozen=True)
class ReorderSuggestion:
    """A reorder recommendation for one series at a target service level."""

    service_level: float
    lead_time_days: int
    review_period_days: int
    on_hand: float
    expected_demand: float  # expected (median) demand over the protection window
    reorder_point: float  # service-level quantile demand over the protection window
    safety_stock: float  # reorder_point - expected_demand (>= 0)
    should_reorder: bool  # on_hand <= reorder_point
    order_quantity: float  # how much to order now (0 if not reordering)
    days_of_cover: float  # how long on_hand lasts at mean daily demand


def build_reorder_suggestion(
    median_path: Sequence[float],
    quantile_path: Sequence[float],
    *,
    service_level: float,
    lead_time_days: int,
    review_period_days: int = 0,
    on_hand: float,
    eoq: float | None = None,
) -> ReorderSuggestion:
    """Assemble a :class:`ReorderSuggestion` from forecast demand paths.

    ``median_path`` and ``quantile_path`` are per-day forecasts over the
    protection window (``lead_time_days + review_period_days`` entries): the
    median (expected) demand and the ``service_level``-quantile demand
    respectively. The order-up-to level is the reorder point; when a reorder is
    triggered we order back up to it, floored at ``eoq`` if given.
    """
    if not 0.0 < service_level < 1.0:
        raise ValueError(f"service_level must be in (0, 1), got {service_level}")
    if lead_time_days < 1:
        raise ValueError(f"lead_time_days must be >= 1, got {lead_time_days}")
    if review_period_days < 0:
        raise ValueError(f"review_period_days must be >= 0, got {review_period_days}")
    if on_hand < 0:
        raise ValueError(f"on_hand must be >= 0, got {on_hand}")
    protection = lead_time_days + review_period_days
    if len(median_path) < protection or len(quantile_path) < protection:
        raise ValueError(
            f"forecast paths shorter than protection window ({protection}): "
            f"median={len(median_path)}, quantile={len(quantile_path)}"
        )
    if eoq is not None and eoq < 0:
        raise ValueError(f"eoq must be >= 0, got {eoq}")

    expected = float(sum(median_path[:protection]))
    reorder_point = float(sum(quantile_path[:protection]))
    safety_stock = max(0.0, reorder_point - expected)
    should_reorder = on_hand <= reorder_point

    order_quantity = 0.0
    if should_reorder:
        order_quantity = max(0.0, reorder_point - on_hand)
        if eoq is not None:
            order_quantity = max(order_quantity, eoq)

    mean_daily = expected / protection if protection else 0.0
    cover = days_of_cover(on_hand, mean_daily)

    return ReorderSuggestion(
        service_level=service_level,
        lead_time_days=lead_time_days,
        review_period_days=review_period_days,
        on_hand=on_hand,
        expected_demand=expected,
        reorder_point=reorder_point,
        safety_stock=safety_stock,
        should_reorder=should_reorder,
        order_quantity=order_quantity,
        days_of_cover=cover,
    )


def suggest_reorder(
    model: Baseline,
    history: Sequence[float],
    *,
    lead_time_days: int,
    service_level: float = 0.95,
    review_period_days: int = 0,
    on_hand: float,
    eoq: float | None = None,
    residual_window: int | None = 60,
) -> ReorderSuggestion:
    """Forecast the protection window with ``model`` and build a suggestion.

    Wraps ``model`` in an :class:`EmpiricalQuantileForecaster` predicting the
    median and the ``service_level`` quantile, forecasts
    ``lead_time_days + review_period_days`` days ahead, and feeds the paths to
    :func:`build_reorder_suggestion`.
    """
    if not 0.0 < service_level < 1.0:
        raise ValueError(f"service_level must be in (0, 1), got {service_level}")
    if lead_time_days < 1:
        raise ValueError(f"lead_time_days must be >= 1, got {lead_time_days}")
    protection = lead_time_days + review_period_days
    forecaster = EmpiricalQuantileForecaster(
        model,
        quantiles=(0.5, service_level),
        residual_window=residual_window,
    )
    paths = forecaster.forecast_quantiles(history, protection)
    return build_reorder_suggestion(
        paths[0.5],
        paths[service_level],
        service_level=service_level,
        lead_time_days=lead_time_days,
        review_period_days=review_period_days,
        on_hand=on_hand,
        eoq=eoq,
    )
