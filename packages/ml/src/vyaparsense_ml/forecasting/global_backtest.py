"""Rolling-origin backtest for the global LightGBM model.

The per-series harness (:func:`vyaparsense_ml.forecasting.backtest.backtest`)
refits a model on one series' prefix per fold. A *global* model is fit once
across **all** series, so it needs a shared-cutoff path: at each origin we fit
one booster on every record strictly before the cutoff date, then recursively
forecast the next ``horizon`` days for every series and pool the results.

Pooling matches the per-series backtests (one WAPE over all forecast-vs-actual
points), so global-model WAPE is directly comparable to the Phase 1-3 numbers —
the apples-to-apples test of whether the global model earns its rung.

Refitting on a growing window each fold is expensive, so the default is a small
number of evenly spaced origins. Seeded throughout. Uses pandas.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from vyaparsense_ml.forecasting.global_model import GlobalLightGBM
from vyaparsense_ml.forecasting.metrics import ForecastMetrics, compute_metrics
from vyaparsense_ml.schema import SalesRecord


@dataclass(frozen=True)
class GlobalBacktestResult:
    """Pooled metrics for the global model across all series and folds."""

    model: str
    n_folds: int
    n_series: int
    metrics: ForecastMetrics


def _series_groups(
    records: Sequence[SalesRecord],
) -> dict[tuple[str, str], list[SalesRecord]]:
    groups: dict[tuple[str, str], list[SalesRecord]] = {}
    for r in records:
        groups.setdefault((r.store_id, r.sku_id), []).append(r)
    for key in groups:
        groups[key].sort(key=lambda r: r.date)
    return groups


def _origin_dates(
    all_dates: list[date], min_train_days: int, horizon: int, n_folds: int
) -> list[date]:
    """Pick up to ``n_folds`` cutoff dates evenly spaced across the valid range.

    A cutoff ``c`` is valid if at least ``min_train_days`` distinct dates precede
    it and at least ``horizon`` dates remain from ``c`` onward (so every series
    can be scored). Cutoffs are drawn from the observed calendar.
    """
    if len(all_dates) < min_train_days + horizon:
        return []
    first_valid = min_train_days  # index of earliest usable cutoff
    last_valid = len(all_dates) - horizon  # exclusive upper bound
    candidates = list(range(first_valid, last_valid))
    if not candidates:
        return []
    if n_folds >= len(candidates):
        chosen = candidates
    else:
        step = (len(candidates) - 1) / (n_folds - 1) if n_folds > 1 else 0
        chosen = sorted({round(i * step) for i in range(n_folds)})
        chosen = [candidates[i] for i in chosen]
    return [all_dates[i] for i in chosen]


def global_backtest(
    records: Sequence[SalesRecord],
    *,
    min_train_days: int,
    horizon: int = 7,
    n_folds: int = 4,
    model: GlobalLightGBM | None = None,
    season_length: int = 7,
) -> GlobalBacktestResult:
    """Rolling-origin backtest of a global LightGBM across all series.

    For each of up to ``n_folds`` evenly spaced cutoff dates: fit on all records
    strictly before the cutoff, recursively forecast the next ``horizon`` days
    for every series that has both history before and actuals at/after the
    cutoff, and pool forecast-vs-actual. ``season_length`` only scales pooled
    MASE.

    Raises:
        ValueError: invalid params, or not enough history for a single fold.
    """
    if min_train_days < 1:
        raise ValueError(f"min_train_days must be >= 1, got {min_train_days}")
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    if n_folds < 1:
        raise ValueError(f"n_folds must be >= 1, got {n_folds}")
    if not records:
        raise ValueError("no records to backtest")

    groups = _series_groups(records)
    all_dates = sorted({r.date for r in records})
    origins = _origin_dates(all_dates, min_train_days, horizon, n_folds)
    if not origins:
        raise ValueError(
            "not enough data for a single fold: need at least "
            f"min_train_days + horizon ({min_train_days} + {horizon}) distinct dates, "
            f"got {len(all_dates)}"
        )

    spec = model if model is not None else GlobalLightGBM()
    pooled_true: list[float] = []
    pooled_pred: list[float] = []
    train_for_scale: list[float] = []
    n_done = 0

    for cutoff in origins:
        train = [r for r in records if r.date < cutoff]
        if not train:
            continue
        fitted = GlobalLightGBM(
            lags=spec.lags,
            roll_windows=spec.roll_windows,
            num_boost_round=spec.num_boost_round,
            params=dict(spec.params),
            seed=spec.seed,
        ).fit(train)

        horizon_dates = [d for d in all_dates if d >= cutoff][:horizon]
        for hist in groups.values():
            past = [r for r in hist if r.date < cutoff]
            actual_by_date = {r.date: r.units_sold for r in hist if r.date in set(horizon_dates)}
            if not past or len(actual_by_date) < horizon:
                continue
            preds = fitted.forecast_series(past, horizon)
            pooled_pred.extend(preds)
            pooled_true.extend(float(actual_by_date[d]) for d in horizon_dates)
            if not train_for_scale:
                train_for_scale = [float(r.units_sold) for r in past]
        n_done += 1

    if not pooled_true:
        raise ValueError("no series had enough history and future actuals to score")

    metrics = compute_metrics(
        pooled_true,
        pooled_pred,
        y_train=train_for_scale,
        season_length=season_length,
    )
    return GlobalBacktestResult(
        model=spec.name,
        n_folds=n_done,
        n_series=len(groups),
        metrics=metrics,
    )
