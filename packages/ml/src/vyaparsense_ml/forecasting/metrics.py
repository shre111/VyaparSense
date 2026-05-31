"""Forecast-accuracy metrics (see ``decisions.md`` ADR-005).

* **WAPE** — primary optimization/selection metric. Robust to the zeros that
  dominate retail demand. ``sum|y - yhat| / sum|y|``.
* **MASE** — error scaled by the in-sample seasonal-naive benchmark; preferred
  for intermittent series where MAPE/WAPE can mislead.
* **RMSE** — squared-error scale.
* **bias** — mean signed error (forecast - actual); positive = over-forecast.
* **MAPE** — display only. Explodes on zero actuals, so it is computed over
  non-zero actuals and **never** used to select models.

Error ratios are returned as fractions (``0.1`` == 10%); the display layer
multiplies by 100. Pure stdlib.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


def _check_pair(y_true: Sequence[float], y_pred: Sequence[float]) -> None:
    if len(y_true) != len(y_pred):
        raise ValueError(f"length mismatch: y_true={len(y_true)}, y_pred={len(y_pred)}")
    if len(y_true) == 0:
        raise ValueError("need at least one observation")


def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Mean absolute error."""
    _check_pair(y_true, y_pred)
    total = sum(abs(t - p) for t, p in zip(y_true, y_pred, strict=True))
    return float(total) / len(y_true)


def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Root mean squared error."""
    _check_pair(y_true, y_pred)
    total = sum((t - p) ** 2 for t, p in zip(y_true, y_pred, strict=True))
    return math.sqrt(float(total) / len(y_true))


def bias(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Mean signed error (forecast - actual). Positive means over-forecasting."""
    _check_pair(y_true, y_pred)
    total = sum(p - t for t, p in zip(y_true, y_pred, strict=True))
    return float(total) / len(y_true)


def wape(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Weighted absolute percentage error: ``sum|y - yhat| / sum|y|``.

    When total actual demand is zero, returns ``0.0`` if the forecast was also
    perfect, else ``inf`` (there is nothing to scale the error against).
    """
    _check_pair(y_true, y_pred)
    denom = sum(abs(t) for t in y_true)
    num = sum(abs(t - p) for t, p in zip(y_true, y_pred, strict=True))
    if denom == 0:
        return 0.0 if num == 0 else math.inf
    return float(num) / float(denom)


def mape(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
    """Mean absolute percentage error over non-zero actuals (display only).

    Zero-actual periods are skipped (the percentage is undefined there). If no
    actual is non-zero, returns ``inf``.
    """
    _check_pair(y_true, y_pred)
    terms = [abs(t - p) / abs(t) for t, p in zip(y_true, y_pred, strict=True) if t != 0]
    if not terms:
        return math.inf
    return sum(terms) / len(terms)


def mase(
    y_true: Sequence[float],
    y_pred: Sequence[float],
    y_train: Sequence[float],
    *,
    season_length: int = 1,
) -> float:
    """Mean absolute scaled error.

    Scales test MAE by the in-sample MAE of a one-step seasonal-naive forecast
    on ``y_train`` (lag ``season_length``). ``< 1`` beats that benchmark.

    When the in-sample scale is zero (a flat training series), returns ``0.0``
    if the forecast was perfect, else ``inf``.
    """
    _check_pair(y_true, y_pred)
    if season_length < 1:
        raise ValueError(f"season_length must be >= 1, got {season_length}")
    if len(y_train) <= season_length:
        raise ValueError(
            f"MASE needs more than season_length={season_length} training points, "
            f"got {len(y_train)}"
        )
    diffs = [
        abs(y_train[i] - y_train[i - season_length]) for i in range(season_length, len(y_train))
    ]
    scale = sum(diffs) / len(diffs)
    test_mae = mae(y_true, y_pred)
    if scale == 0:
        return 0.0 if test_mae == 0 else math.inf
    return test_mae / scale


@dataclass(frozen=True)
class ForecastMetrics:
    """Bundle of accuracy metrics for one forecast-vs-actual comparison.

    ``mase`` is ``None`` when no training history was supplied to scale against.
    """

    wape: float
    mae: float
    rmse: float
    bias: float
    mape: float
    mase: float | None


def compute_metrics(
    y_true: Sequence[float],
    y_pred: Sequence[float],
    *,
    y_train: Sequence[float] | None = None,
    season_length: int = 1,
) -> ForecastMetrics:
    """Compute all metrics at once. ``mase`` requires ``y_train``."""
    mase_value: float | None = None
    if y_train is not None and len(y_train) > season_length:
        mase_value = mase(y_true, y_pred, y_train, season_length=season_length)
    return ForecastMetrics(
        wape=wape(y_true, y_pred),
        mae=mae(y_true, y_pred),
        rmse=rmse(y_true, y_pred),
        bias=bias(y_true, y_pred),
        mape=mape(y_true, y_pred),
        mase=mase_value,
    )
