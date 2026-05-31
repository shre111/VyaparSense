"""Tests for the rolling-origin backtesting harness."""

from __future__ import annotations

import pytest

from vyaparsense_ml.forecasting.backtest import backtest
from vyaparsense_ml.forecasting.models import Naive, SeasonalNaive


def test_fold_count_expanding_window() -> None:
    # n=10, min_train=5, horizon=1, step=1 -> cutoffs 5..9 = 5 folds
    result = backtest(list(range(10)), Naive(), min_train_size=5, horizon=1, step=1)
    assert result.n_folds == 5
    assert [f.cutoff for f in result.folds] == [5, 6, 7, 8, 9]


def test_step_advances_cutoff() -> None:
    result = backtest(list(range(12)), Naive(), min_train_size=4, horizon=1, step=3)
    assert [f.cutoff for f in result.folds] == [4, 7, 10]


def test_naive_perfect_on_constant_series() -> None:
    result = backtest([5.0] * 20, Naive(), min_train_size=10, horizon=1)
    assert result.metrics.wape == 0.0
    assert result.metrics.mae == 0.0


def test_seasonal_naive_perfect_on_seasonal_series() -> None:
    season = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    y = season * 6  # 42 points
    result = backtest(y, SeasonalNaive(season_length=7), min_train_size=14, horizon=7, step=7)
    assert result.metrics.wape == pytest.approx(0.0)


def test_multistep_horizon_pools_all_points() -> None:
    result = backtest(list(range(20)), Naive(), min_train_size=10, horizon=3, step=1)
    # each fold contributes `horizon` points to the pooled metrics
    assert all(len(f.y_true) == 3 for f in result.folds)


def test_too_short_series_raises() -> None:
    with pytest.raises(ValueError, match="single fold"):
        backtest([1.0, 2.0, 3.0], Naive(), min_train_size=3, horizon=1)


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError, match="min_train_size"):
        backtest([1.0, 2.0], Naive(), min_train_size=0)
    with pytest.raises(ValueError, match="step"):
        backtest([1.0, 2.0, 3.0], Naive(), min_train_size=1, step=0)
