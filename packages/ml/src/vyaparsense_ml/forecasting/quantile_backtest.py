"""Rolling-origin backtest for probabilistic (quantile) forecasts.

The point :func:`~vyaparsense_ml.forecasting.backtest.backtest` scores a single
number per period; this scores a :class:`QuantileForecaster` across the same
expanding-window folds using the quantile metrics (mean pinball loss as the
headline, per-quantile pinball loss, and coverage for calibration).

Pure stdlib; no accuracy claim without one of these behind it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from vyaparsense_ml.forecasting.quantile import QuantileForecaster
from vyaparsense_ml.forecasting.quantile_metrics import (
    coverage,
    mean_pinball_loss,
    pinball_loss,
)


@dataclass(frozen=True)
class QuantileBacktestResult:
    """Pooled probabilistic scores for one forecaster on one series.

    ``mean_pinball`` is the headline (lower is better). ``pinball_by_quantile``
    and ``coverage_by_quantile`` are keyed by quantile level; coverage near the
    level means the forecast is well calibrated.
    """

    model: str
    quantiles: tuple[float, ...]
    n_folds: int
    mean_pinball: float
    pinball_by_quantile: dict[float, float]
    coverage_by_quantile: dict[float, float]


def quantile_backtest(
    y: Sequence[float],
    forecaster: QuantileForecaster,
    *,
    min_train_size: int,
    horizon: int = 1,
    step: int = 1,
) -> QuantileBacktestResult:
    """Expanding-window probabilistic backtest of ``forecaster`` over ``y``.

    Folds match the point backtest: start at ``y[:min_train_size]`` and advance
    the cutoff by ``step`` while a full ``horizon`` of actuals remains. Each
    quantile's predictions are pooled across folds and scored once.

    Raises:
        ValueError: invalid parameters, or the series is too short for one fold.
    """
    if min_train_size < 1:
        raise ValueError(f"min_train_size must be >= 1, got {min_train_size}")
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    if step < 1:
        raise ValueError(f"step must be >= 1, got {step}")

    quantiles = forecaster.quantiles
    n = len(y)
    pooled_true: list[float] = []
    pooled_pred: dict[float, list[float]] = {q: [] for q in quantiles}
    n_folds = 0

    cutoff = min_train_size
    while cutoff + horizon <= n:
        train = y[:cutoff]
        actual = [float(v) for v in y[cutoff : cutoff + horizon]]
        preds = forecaster.forecast_quantiles(train, horizon)
        pooled_true.extend(actual)
        for q in quantiles:
            pooled_pred[q].extend(preds[q])
        n_folds += 1
        cutoff += step

    if n_folds == 0:
        raise ValueError(
            "not enough data for a single fold: "
            f"min_train_size + horizon ({min_train_size} + {horizon}) > len(y) ({n})"
        )

    pinball_by_q = {q: pinball_loss(pooled_true, pooled_pred[q], q) for q in quantiles}
    coverage_by_q = {q: coverage(pooled_true, pooled_pred[q], q) for q in quantiles}
    mean_pb = mean_pinball_loss(pooled_true, pooled_pred)

    return QuantileBacktestResult(
        model=forecaster.name,
        quantiles=quantiles,
        n_folds=n_folds,
        mean_pinball=mean_pb,
        pinball_by_quantile=pinball_by_q,
        coverage_by_quantile=coverage_by_q,
    )
