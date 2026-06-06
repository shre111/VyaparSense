"""Per-series model selection by backtest (``CLAUDE.md`` section 4).

Runs every candidate baseline through the same rolling backtest and picks the
one with the lowest pooled WAPE. Selection is by evidence, never by vibe — a
naive model winning is a valid, expected outcome.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from vyaparsense_ml.cleaning import SeriesKey
from vyaparsense_ml.forecasting.backtest import BacktestResult, backtest
from vyaparsense_ml.forecasting.models import Baseline


@dataclass(frozen=True)
class SelectionResult:
    """Outcome of comparing candidate models on one series.

    ``ranking`` is ``(model_name, pooled_wape)`` sorted best (lowest) first;
    ``best`` is its first entry; ``results`` holds the full backtest per model.
    """

    best: str
    results: dict[str, BacktestResult]
    ranking: list[tuple[str, float]]


def select_model(
    y: Sequence[float],
    models: Sequence[Baseline],
    *,
    min_train_size: int,
    horizon: int = 1,
    step: int = 1,
    season_length: int = 1,
    max_folds: int | None = None,
) -> SelectionResult:
    """Backtest every model on ``y`` and pick the lowest pooled WAPE.

    ``max_folds`` caps selection to the most recent folds (see
    :func:`~vyaparsense_ml.forecasting.backtest.backtest`).
    """
    if not models:
        raise ValueError("need at least one candidate model")
    results: dict[str, BacktestResult] = {}
    for model in models:
        results[model.name] = backtest(
            y,
            model,
            min_train_size=min_train_size,
            horizon=horizon,
            step=step,
            season_length=season_length,
            max_folds=max_folds,
        )
    ranking = sorted(
        ((name, result.metrics.wape) for name, result in results.items()),
        key=lambda item: item[1],
    )
    return SelectionResult(best=ranking[0][0], results=results, ranking=ranking)


def select_per_series(
    series: dict[SeriesKey, list[tuple[date, int]]],
    models: Sequence[Baseline],
    *,
    min_train_size: int,
    horizon: int = 1,
    step: int = 1,
    season_length: int = 1,
    max_folds: int | None = None,
) -> dict[SeriesKey, SelectionResult]:
    """Select the best model for every series from :func:`cleaning.to_series`.

    Each series must be long enough for at least one backtest fold; otherwise
    :func:`select_model` raises for that series. ``max_folds`` caps selection to
    the most recent folds (cheap on long histories).
    """
    out: dict[SeriesKey, SelectionResult] = {}
    for key, points in series.items():
        units = [float(u) for _, u in points]
        out[key] = select_model(
            units,
            models,
            min_train_size=min_train_size,
            horizon=horizon,
            step=step,
            season_length=season_length,
            max_folds=max_folds,
        )
    return out
