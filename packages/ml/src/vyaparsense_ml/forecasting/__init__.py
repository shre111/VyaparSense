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
        EmpiricalQuantileForecaster,                # probabilistic forecasting
        quantile_backtest, QuantileBacktestResult,
        build_features, feature_columns,            # global-model features
        GlobalLightGBM,                             # global ML model
        global_backtest, GlobalBacktestResult,
        build_hierarchy, Hierarchy, reconcile,      # hierarchical reconciliation
        aggregate_history, coherence_error,
        ModelCard, data_hash, write_card,           # model cards (reproducibility)
        card_from_global_backtest,
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
from vyaparsense_ml.forecasting.features import (
    build_features,
    feature_columns,
)
from vyaparsense_ml.forecasting.global_backtest import (
    GlobalBacktestResult,
    card_from_global_backtest,
    global_backtest,
)
from vyaparsense_ml.forecasting.global_model import (
    GlobalLightGBM,
)
from vyaparsense_ml.forecasting.hierarchy import (
    Hierarchy,
    aggregate_history,
    build_hierarchy,
    coherence_error,
    reconcile,
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
from vyaparsense_ml.forecasting.model_card import (
    ModelCard,
    data_hash,
    write_card,
)
from vyaparsense_ml.forecasting.models import (
    Baseline,
    MovingAverage,
    Naive,
    SeasonalNaive,
)
from vyaparsense_ml.forecasting.quantile import (
    EmpiricalQuantileForecaster,
    QuantileForecaster,
)
from vyaparsense_ml.forecasting.quantile_backtest import (
    QuantileBacktestResult,
    quantile_backtest,
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
    "EmpiricalQuantileForecaster",
    "ForecastMetrics",
    "GlobalBacktestResult",
    "GlobalLightGBM",
    "Hierarchy",
    "ModelCard",
    "MovingAverage",
    "Naive",
    "QuantileBacktestResult",
    "QuantileForecaster",
    "SeasonalNaive",
    "SelectionResult",
    "aggregate_history",
    "backtest",
    "bias",
    "build_features",
    "build_hierarchy",
    "card_from_global_backtest",
    "coherence_error",
    "compute_metrics",
    "coverage",
    "data_hash",
    "feature_columns",
    "global_backtest",
    "mae",
    "mape",
    "mase",
    "mean_pinball_loss",
    "pinball_loss",
    "quantile_backtest",
    "reconcile",
    "rmse",
    "select_model",
    "select_per_series",
    "wape",
    "write_card",
]
