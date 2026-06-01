"""Tests for the classical statsforecast adapter models (AutoETS / AutoARIMA).

These exercise the adapters' contract (shape, validation, guards) rather than
statsforecast's internal accuracy — that is what the backtest harness measures.
"""

from __future__ import annotations

import pytest

from vyaparsense_ml.forecasting.backtest import backtest
from vyaparsense_ml.forecasting.classical import AutoARIMA, AutoETS
from vyaparsense_ml.forecasting.models import Baseline

_SEASON = [10.0, 12.0, 9.0, 11.0, 15.0, 25.0, 22.0]
_Y = (_SEASON * 12)[:80]  # 80 daily points, clear weekly pattern


@pytest.mark.parametrize("model", [AutoETS(season_length=7), AutoARIMA(season_length=7)])
def test_forecast_shape_and_finiteness(model: Baseline) -> None:
    out = model.forecast(_Y, 7)
    assert len(out) == 7
    assert all(isinstance(v, float) for v in out)
    assert all(v == v for v in out)  # no NaN
    assert all(v >= 0.0 for v in out)  # demand is non-negative


@pytest.mark.parametrize("model", [AutoETS(season_length=7), AutoARIMA(season_length=7)])
def test_models_satisfy_baseline_protocol(model: Baseline) -> None:
    assert isinstance(model, Baseline)
    assert isinstance(model.name, str)


def test_names_are_stable_and_distinct() -> None:
    assert AutoETS(season_length=7).name == "auto_ets_7"
    assert AutoARIMA(season_length=7).name == "auto_arima_7"


@pytest.mark.parametrize("model", [AutoETS(season_length=7), AutoARIMA(season_length=7)])
def test_requires_two_full_seasons(model: Baseline) -> None:
    with pytest.raises(ValueError, match="2\\*season_length"):
        model.forecast(_SEASON, 7)  # only one season


@pytest.mark.parametrize("model", [AutoETS(season_length=7), AutoARIMA(season_length=7)])
def test_rejects_bad_horizon(model: Baseline) -> None:
    with pytest.raises(ValueError, match="horizon"):
        model.forecast(_Y, 0)


@pytest.mark.parametrize("model", [AutoETS(season_length=7), AutoARIMA(season_length=7)])
def test_all_zero_series_is_safe(model: Baseline) -> None:
    # degenerate no-demand series must not raise or produce NaN/negatives
    out = model.forecast([0.0] * 40, 7)
    assert len(out) == 7
    assert all(v >= 0.0 and v == v for v in out)


def test_classical_models_run_through_backtest_harness() -> None:
    # the adapters must drop straight into the existing harness unchanged
    result = backtest(_Y, AutoETS(season_length=7), min_train_size=28, horizon=7, step=7)
    assert result.model == "auto_ets_7"
    assert result.n_folds >= 1
    assert result.metrics.wape == result.metrics.wape  # finite (not NaN)
