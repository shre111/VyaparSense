"""Forecasting: baseline models, accuracy metrics, backtesting, and selection.

This is rung 1 of the model ladder (see ``CLAUDE.md`` section 4): the honest
"dumb" baselines plus the harness that scores them. Every fancier model added
later must beat these on the same rolling backtest before it earns its place.

Public API::

    from vyaparsense_ml.forecasting import (
        Naive, MovingAverage, SeasonalNaive,        # baseline models
        AutoETS, AutoARIMA,                         # classical models
        Croston, CrostonSBA, TSB,                   # intermittent models
        wape, mase, rmse, bias, mape,               # point metrics
        ForecastMetrics, compute_metrics,
        pinball_loss, mean_pinball_loss, coverage,  # quantile metrics
        backtest, BacktestResult, BacktestFold,     # backtesting
        select_model, select_per_series, SelectionResult,
    )
"""

from __future__ import annotations

from vyaparsense_ml.forecasting.backtest import (
    BacktestFold,
    BacktestResult,
    backtest,
)
from vyaparsense_ml.forecasting.classical import (
    AutoARIMA,
    AutoETS,
)
from vyaparsense_ml.forecasting.intermittent import (
    TSB,
    Croston,
    CrostonSBA,
)
from vyaparsense_ml.forecasting.metrics import (
    ForecastMetrics,
    bias,
    compute_metrics,
    mae,
    mape,
    mase,
    rmse,
    wape,
)
from vyaparsense_ml.forecasting.models import (
    Baseline,
    MovingAverage,
    Naive,
    SeasonalNaive,
)
from vyaparsense_ml.forecasting.quantile_metrics import (
    coverage,
    mean_pinball_loss,
    pinball_loss,
)
from vyaparsense_ml.forecasting.selection import (
    SelectionResult,
    select_model,
    select_per_series,
)

__all__ = [
    "TSB",
    "AutoARIMA",
    "AutoETS",
    "BacktestFold",
    "BacktestResult",
    "Baseline",
    "Croston",
    "CrostonSBA",
    "ForecastMetrics",
    "MovingAverage",
    "Naive",
    "SeasonalNaive",
    "SelectionResult",
    "backtest",
    "bias",
    "compute_metrics",
    "coverage",
    "mae",
    "mape",
    "mase",
    "mean_pinball_loss",
    "pinball_loss",
    "rmse",
    "select_model",
    "select_per_series",
    "wape",
]
