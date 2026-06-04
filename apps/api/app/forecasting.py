"""Forecast generation service: stored sales -> per-series forecasts.

Bridges the API's persisted sales (``sales_records``) and the ``packages/ml``
forecasting library. For each ``(store, sku)`` series it picks the best baseline
by rolling backtest (:func:`vyaparsense_ml.forecasting.select_per_series`) and
produces an ``h``-step forward point forecast with that winner.

Two candidate sets share this one path:

* ``DEFAULT_MODELS`` — the pure-stdlib **baselines**, fast enough for the
  synchronous ``POST /forecasts`` request path.
* ``FULL_LADDER_MODELS`` — baselines + classical + intermittent (rungs 1-3).
  Heavier to backtest (statsforecast refits per fold), so it runs in the async
  job path (ADR-007).
* ``generate_forecasts_full`` — the job path: runs the per-series ladder **and** a
  global LightGBM (rung 4), then keeps whichever has the lower pooled-WAPE on a
  rolling backtest. The honest "does the global model beat the champions" test.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from vyaparsense_ml.forecasting.classical import AutoARIMA, AutoETS
from vyaparsense_ml.forecasting.global_backtest import global_backtest
from vyaparsense_ml.forecasting.global_model import GlobalLightGBM
from vyaparsense_ml.forecasting.intermittent import TSB, Croston, CrostonSBA
from vyaparsense_ml.forecasting.metrics import wape
from vyaparsense_ml.forecasting.models import Baseline, MovingAverage, Naive, SeasonalNaive
from vyaparsense_ml.forecasting.selection import SelectionResult, select_per_series
from vyaparsense_ml.schema import SalesRecord

SeriesKey = tuple[str, str]

#: Candidate baselines, the permanent honest benchmark (CLAUDE.md §4 rung 1).
DEFAULT_MODELS: list[Baseline] = [
    Naive(),
    MovingAverage(window=7),
    SeasonalNaive(season_length=7),
]

#: The full per-series ladder (CLAUDE.md §4 rungs 1-3): baselines + classical
#: (ETS/ARIMA) + intermittent (Croston/SBA/TSB). Each series still picks its own
#: winner by backtest — a baseline beating the fancier models is a valid result.
FULL_LADDER_MODELS: list[Baseline] = [
    *DEFAULT_MODELS,
    AutoETS(season_length=7),
    AutoARIMA(season_length=7),
    Croston(),
    CrostonSBA(),
    TSB(),
]

# Backtest defaults: weekly origins after a four-week warmup, season length 7.
_MIN_TRAIN_SIZE = 28
_STEP = 7

# The global model's lag/rolling features (up to a 28-day window) need more
# warmup than the per-series baselines, so its backtest uses a larger floor.
# Below this, the global model simply can't be scored and we keep the champions.
_GLOBAL_MIN_TRAIN_DAYS = 42


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
    as_of: dt.date | None = None,
    models: Sequence[Baseline] | None = None,
) -> list[ForecastRow]:
    """Select the best baseline per series and forecast ``horizon`` days ahead.

    With ``as_of`` set, each series is truncated to dates ``<= as_of`` before
    selection/forecasting, and forecasts are dated forward from ``as_of``. This
    is how the accuracy backfill works: forecasting "as of" a past cutoff yields
    horizon dates that already have realised actuals to score against. Without
    it, forecasts run forward from each series' last observed date.

    Series too short for even one backtest fold (after truncation) are skipped.
    Returns one :class:`ForecastRow` per forecast day per forecastable series.

    Raises:
        ValueError: invalid ``horizon``.
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    candidates = list(models) if models is not None else DEFAULT_MODELS

    if as_of is not None:
        series = {key: [(d, u) for d, u in pts if d <= as_of] for key, pts in series.items()}

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
    return _champion_rows(eligible, selection, candidates, horizon)


def _champion_rows(
    eligible: dict[SeriesKey, list[tuple[dt.date, int]]],
    selection: dict[SeriesKey, SelectionResult],
    candidates: Sequence[Baseline],
    horizon: int,
) -> list[ForecastRow]:
    """Forward-forecast each series with its backtest-winning model."""
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


def _pooled_champion_wape(selection: dict[SeriesKey, SelectionResult]) -> float:
    """Pool every champion's backtest folds into one WAPE, comparable to global.

    Pools ``sum|y-yhat| / sum|y|`` over all forecast-vs-actual points of each
    series' winning model — the same pooling :func:`global_backtest` uses.
    """
    pooled_true: list[float] = []
    pooled_pred: list[float] = []
    for result in selection.values():
        for fold in result.results[result.best].folds:
            pooled_true.extend(fold.y_true)
            pooled_pred.extend(fold.y_pred)
    return wape(pooled_true, pooled_pred)


@dataclass(frozen=True)
class LadderDecision:
    """Which approach won the job's backtest, and the pooled WAPEs behind it."""

    winner: str  # "global" | "per_series" | "none"
    champion_wape: float | None
    global_wape: float | None
    n_series: int


def generate_forecasts_full(
    records: Sequence[SalesRecord],
    *,
    horizon: int = 7,
    season_length: int = 7,
    as_of: dt.date | None = None,
    n_folds: int = 4,
    models: Sequence[Baseline] | None = None,
) -> tuple[list[ForecastRow], LadderDecision]:
    """Job-path forecasting: per-series ladder vs a global LightGBM, pick by backtest.

    Runs the per-series ladder (``models``, default :data:`FULL_LADDER_MODELS`)
    and a global LightGBM, compares their pooled rolling-backtest WAPE, and
    forecasts forward with the winner — global only if it *strictly* beats the
    per-series champions (ties keep the cheaper, simpler per-series models).
    Honest reporting: the returned :class:`LadderDecision` carries both WAPEs.

    ``records`` are a tenant's clean :class:`SalesRecord`s (the global model needs
    price/promo). ``as_of`` truncates to that cutoff first, as in
    :func:`generate_forecasts`. (``models`` is overridable mainly so tests can run
    a cheap candidate set; production uses the full ladder.)
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    candidates = list(models) if models is not None else FULL_LADDER_MODELS
    if as_of is not None:
        records = [r for r in records if r.date <= as_of]

    series: dict[SeriesKey, list[tuple[dt.date, int]]] = {}
    records_by_key: dict[SeriesKey, list[SalesRecord]] = {}
    for r in records:
        key = (r.store_id, r.sku_id)
        series.setdefault(key, []).append((r.date, r.units_sold))
        records_by_key.setdefault(key, []).append(r)

    min_len = _MIN_TRAIN_SIZE + horizon
    eligible = {key: pts for key, pts in series.items() if len(pts) >= min_len}
    if not eligible:
        return [], LadderDecision("none", None, None, 0)

    selection = select_per_series(
        eligible,
        candidates,
        min_train_size=_MIN_TRAIN_SIZE,
        horizon=horizon,
        step=_STEP,
        season_length=season_length,
    )
    champion_wape = _pooled_champion_wape(selection)
    champion_rows = _champion_rows(eligible, selection, candidates, horizon)

    global_wape = _global_backtest_wape(
        records, horizon=horizon, season_length=season_length, n_folds=n_folds
    )
    n_series = len(eligible)

    if global_wape is not None and global_wape < champion_wape:
        rows = _global_rows(records_by_key, eligible.keys(), horizon)
        return rows, LadderDecision("global", champion_wape, global_wape, n_series)
    return champion_rows, LadderDecision("per_series", champion_wape, global_wape, n_series)


def _global_backtest_wape(
    records: Sequence[SalesRecord], *, horizon: int, season_length: int, n_folds: int
) -> float | None:
    """Pooled global-model backtest WAPE, or ``None`` if there isn't enough data."""
    try:
        result = global_backtest(
            records,
            min_train_days=_GLOBAL_MIN_TRAIN_DAYS,
            horizon=horizon,
            n_folds=n_folds,
            season_length=season_length,
        )
    except ValueError:
        return None
    return result.metrics.wape


def _global_rows(
    records_by_key: dict[SeriesKey, list[SalesRecord]],
    keys: Iterable[SeriesKey],
    horizon: int,
) -> list[ForecastRow]:
    """Fit one global LightGBM on all records and forecast each eligible series."""
    all_records = [r for recs in records_by_key.values() for r in recs]
    model = GlobalLightGBM().fit(all_records)
    out: list[ForecastRow] = []
    for key in keys:
        history = records_by_key[key]
        preds = model.forecast_series(history, horizon)
        last_date = history[-1].date
        for step, value in enumerate(preds, start=1):
            out.append(
                ForecastRow(
                    store_id=key[0],
                    sku_id=key[1],
                    model=model.name,
                    horizon_date=last_date + dt.timedelta(days=step),
                    predicted_units=value,
                )
            )
    return out
