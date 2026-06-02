"""Forecast generation service: stored sales -> per-series forecasts.

Bridges the API's persisted sales (``sales_records``) and the ``packages/ml``
forecasting library. For each ``(store, sku)`` series it picks the best baseline
by rolling backtest (:func:`vyaparsense_ml.forecasting.select_per_series`) and
produces an ``h``-step forward point forecast with that winner.

Scope (this PR): the **baseline** models only (naive / moving-average /
seasonal-naive). They are pure-stdlib and fast enough to run in the request
path. The classical / intermittent / global-LightGBM models are heavier and
belong in the async worker (ADR-007); wiring those in is a later change.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass

from vyaparsense_ml.forecasting.models import Baseline, MovingAverage, Naive, SeasonalNaive
from vyaparsense_ml.forecasting.selection import select_per_series

SeriesKey = tuple[str, str]

#: Candidate baselines, the permanent honest benchmark (CLAUDE.md §4 rung 1).
DEFAULT_MODELS: list[Baseline] = [
    Naive(),
    MovingAverage(window=7),
    SeasonalNaive(season_length=7),
]

# Backtest defaults: weekly origins after a four-week warmup, season length 7.
_MIN_TRAIN_SIZE = 28
_STEP = 7


@dataclass(frozen=True)
class ForecastRow:
    """One forecast point for a series: model, target date, predicted units."""

    store_id: str
    sku_id: str
    model: str
    horizon_date: dt.date
    predicted_units: float


def _series_last_date(points: Sequence[tuple[dt.date, int]]) -> dt.date:
    return max(d for d, _ in points)


def generate_forecasts(
    series: dict[SeriesKey, list[tuple[dt.date, int]]],
    *,
    horizon: int = 7,
    season_length: int = 7,
    models: Sequence[Baseline] | None = None,
) -> list[ForecastRow]:
    """Select the best baseline per series and forecast ``horizon`` days ahead.

    Series too short for even one backtest fold are skipped (they have no
    evidence to select on yet). Returns one :class:`ForecastRow` per forecast
    day per forecastable series, dated forward from each series' last date.

    Raises:
        ValueError: invalid ``horizon``.
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    candidates = list(models) if models is not None else DEFAULT_MODELS

    # select_per_series raises for series too short for a fold; filter to those
    # with enough history so one bad series doesn't fail the whole batch.
    min_len = _MIN_TRAIN_SIZE + horizon
    eligible = {key: pts for key, pts in series.items() if len(pts) >= min_len}
    if not eligible:
        return []

    selection = select_per_series(
        eligible,
        candidates,
        min_train_size=_MIN_TRAIN_SIZE,
        horizon=horizon,
        step=_STEP,
        season_length=season_length,
    )

    out: list[ForecastRow] = []
    for key, result in selection.items():
        store_id, sku_id = key
        points = eligible[key]
        units = [float(u) for _, u in points]
        winner = next(m for m in candidates if m.name == result.best)
        preds = winner.forecast(units, horizon)
        last_date = _series_last_date(points)
        for step, value in enumerate(preds, start=1):
            out.append(
                ForecastRow(
                    store_id=store_id,
                    sku_id=sku_id,
                    model=result.best,
                    horizon_date=last_date + dt.timedelta(days=step),
                    predicted_units=value,
                )
            )
    return out
