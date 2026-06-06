"""Rolling-origin (expanding-window) backtesting harness.

Repeatedly trains on a growing prefix of a series and forecasts the next
``horizon`` points, sliding the cutoff forward by ``step``. Predictions from
every fold are pooled and scored once — this pooled WAPE over a fixed holdout is
the "getting smarter" flywheel metric (``CLAUDE.md`` section 5).

Pure stdlib; no accuracy claim without one of these backtests behind it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from vyaparsense_ml.forecasting.metrics import ForecastMetrics, compute_metrics
from vyaparsense_ml.forecasting.models import Baseline


@dataclass(frozen=True)
class BacktestFold:
    """One train/forecast split: forecast made at ``cutoff`` vs. what followed."""

    cutoff: int
    y_true: list[float]
    y_pred: list[float]


@dataclass(frozen=True)
class BacktestResult:
    """All folds for one model on one series, plus pooled metrics."""

    model: str
    folds: list[BacktestFold]
    metrics: ForecastMetrics

    @property
    def n_folds(self) -> int:
        return len(self.folds)


def backtest(
    y: Sequence[float],
    model: Baseline,
    *,
    min_train_size: int,
    horizon: int = 1,
    step: int = 1,
    season_length: int = 1,
    max_folds: int | None = None,
) -> BacktestResult:
    """Expanding-window backtest of ``model`` over series ``y``.

    Folds start with ``y[:min_train_size]`` and advance the cutoff by ``step``
    while a full ``horizon`` of actuals remains. ``season_length`` only scales
    the pooled MASE; it does not change the folds.

    ``max_folds`` caps the backtest to the **most recent** ``max_folds`` origins
    (still expanding-window — each fold trains on its full prefix). This bounds
    the cost of model *selection* on long histories without affecting the final
    forward forecast, which is made separately on the full series.

    Raises:
        ValueError: invalid parameters, or the series is too short for even one
            fold (``min_train_size + horizon > len(y)``).
    """
    if min_train_size < 1:
        raise ValueError(f"min_train_size must be >= 1, got {min_train_size}")
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    if step < 1:
        raise ValueError(f"step must be >= 1, got {step}")
    if max_folds is not None and max_folds < 1:
        raise ValueError(f"max_folds must be >= 1, got {max_folds}")

    n = len(y)
    # First cutoff: usually min_train_size, but advanced to keep only the most
    # recent max_folds origins when the history is long.
    first_cutoff = min_train_size
    if max_folds is not None:
        last_cutoff = n - horizon
        if last_cutoff >= min_train_size:
            n_all = (last_cutoff - min_train_size) // step + 1
            if n_all > max_folds:
                first_cutoff = min_train_size + (n_all - max_folds) * step

    folds: list[BacktestFold] = []
    cutoff = first_cutoff
    while cutoff + horizon <= n:
        train = y[:cutoff]
        actual = [float(v) for v in y[cutoff : cutoff + horizon]]
        pred = model.forecast(train, horizon)
        folds.append(BacktestFold(cutoff=cutoff, y_true=actual, y_pred=pred))
        cutoff += step

    if not folds:
        raise ValueError(
            "not enough data for a single fold: "
            f"min_train_size + horizon ({min_train_size} + {horizon}) > len(y) ({n})"
        )

    pooled_true = [v for fold in folds for v in fold.y_true]
    pooled_pred = [v for fold in folds for v in fold.y_pred]
    metrics = compute_metrics(
        pooled_true,
        pooled_pred,
        y_train=[float(v) for v in y[:min_train_size]],
        season_length=season_length,
    )
    return BacktestResult(model=model.name, folds=folds, metrics=metrics)
