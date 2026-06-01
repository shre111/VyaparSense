"""Tests for the probabilistic (quantile) backtest harness."""

from __future__ import annotations

import pytest

from vyaparsense_ml.forecasting.models import Naive
from vyaparsense_ml.forecasting.quantile import EmpiricalQuantileForecaster
from vyaparsense_ml.forecasting.quantile_backtest import quantile_backtest


def _forecaster(quantiles: tuple[float, ...] = (0.5, 0.9)) -> EmpiricalQuantileForecaster:
    return EmpiricalQuantileForecaster(Naive(), quantiles=quantiles, residual_window=None)


def test_fold_count_matches_point_backtest() -> None:
    # n=20, min_train=10, h=1, step=1 -> 10 folds
    result = quantile_backtest(list(range(20)), _forecaster(), min_train_size=10)
    assert result.n_folds == 10


def test_result_keys_cover_all_quantiles() -> None:
    result = quantile_backtest(list(range(30)), _forecaster((0.5, 0.9, 0.95)), min_train_size=10)
    assert set(result.pinball_by_quantile) == {0.5, 0.9, 0.95}
    assert set(result.coverage_by_quantile) == {0.5, 0.9, 0.95}
    assert result.quantiles == (0.5, 0.9, 0.95)


def test_mean_pinball_is_average_of_per_quantile() -> None:
    result = quantile_backtest(list(range(30)), _forecaster((0.5, 0.9)), min_train_size=10)
    expected = sum(result.pinball_by_quantile.values()) / 2
    assert result.mean_pinball == pytest.approx(expected)


def test_pinball_zero_on_constant_series() -> None:
    # constant series -> residuals all 0 -> every quantile equals the actual
    result = quantile_backtest([5.0] * 25, _forecaster((0.5, 0.9)), min_train_size=10)
    assert result.mean_pinball == pytest.approx(0.0)


def test_higher_quantile_has_higher_coverage_on_noisy_series() -> None:
    y = [5.0, 7.0, 3.0, 9.0, 2.0, 8.0, 6.0, 4.0, 10.0, 1.0] * 4
    result = quantile_backtest(y, _forecaster((0.5, 0.95)), min_train_size=20)
    assert result.coverage_by_quantile[0.95] >= result.coverage_by_quantile[0.5]


def test_too_short_series_raises() -> None:
    with pytest.raises(ValueError, match="single fold"):
        quantile_backtest([1.0, 2.0, 3.0], _forecaster(), min_train_size=3, horizon=1)


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError, match="min_train_size"):
        quantile_backtest([1.0, 2.0], _forecaster(), min_train_size=0)
    with pytest.raises(ValueError, match="step"):
        quantile_backtest([1.0, 2.0, 3.0], _forecaster(), min_train_size=1, step=0)
