"""Tests for the intermittent-demand adapter models (Croston / SBA / TSB).

These exercise the adapters' contract (shape, validation, guards, flatness)
rather than statsforecast's internal accuracy — that is what the backtest
harness measures.
"""

from __future__ import annotations

import pytest

from vyaparsense_ml.forecasting.backtest import backtest
from vyaparsense_ml.forecasting.intermittent import TSB, Croston, CrostonSBA
from vyaparsense_ml.forecasting.models import Baseline

# A sparse intermittent series: mostly zeros with occasional demand.
_Y = [0.0, 0.0, 3.0, 0.0, 0.0, 0.0, 5.0, 0.0, 2.0, 0.0, 0.0, 4.0, 0.0, 0.0, 1.0, 0.0]

_MODELS: list[Baseline] = [Croston(), CrostonSBA(), TSB(alpha_d=0.2, alpha_p=0.2)]


@pytest.mark.parametrize("model", _MODELS)
def test_forecast_shape_and_finiteness(model: Baseline) -> None:
    out = model.forecast(_Y, 5)
    assert len(out) == 5
    assert all(isinstance(v, float) for v in out)
    assert all(v == v for v in out)  # no NaN
    assert all(v >= 0.0 for v in out)  # demand is non-negative


@pytest.mark.parametrize("model", _MODELS)
def test_forecast_is_flat(model: Baseline) -> None:
    # Croston-family methods produce a single repeated level
    out = model.forecast(_Y, 4)
    assert len(set(out)) == 1


@pytest.mark.parametrize("model", _MODELS)
def test_models_satisfy_baseline_protocol(model: Baseline) -> None:
    assert isinstance(model, Baseline)
    assert isinstance(model.name, str)


def test_names_are_stable_and_distinct() -> None:
    assert Croston().name == "croston"
    assert CrostonSBA().name == "croston_sba"
    assert TSB().name == "tsb"


@pytest.mark.parametrize("model", _MODELS)
def test_rejects_bad_horizon(model: Baseline) -> None:
    with pytest.raises(ValueError, match="horizon"):
        model.forecast(_Y, 0)


@pytest.mark.parametrize("model", _MODELS)
def test_rejects_empty_history(model: Baseline) -> None:
    with pytest.raises(ValueError, match="empty history"):
        model.forecast([], 3)


@pytest.mark.parametrize("model", _MODELS)
def test_all_zero_series_is_safe(model: Baseline) -> None:
    # a fully obsolete SKU must not raise or produce NaN/negatives
    out = model.forecast([0.0] * 12, 3)
    assert out == [0.0, 0.0, 0.0]


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.5])
def test_tsb_rejects_out_of_range_alpha(bad: float) -> None:
    with pytest.raises(ValueError, match="alpha"):
        TSB(alpha_d=bad)
    with pytest.raises(ValueError, match="alpha"):
        TSB(alpha_p=bad)


def test_intermittent_models_run_through_backtest_harness() -> None:
    # the adapters must drop straight into the existing harness unchanged
    y = _Y * 4  # 64 points
    result = backtest(y, CrostonSBA(), min_train_size=16, horizon=4, step=4)
    assert result.model == "croston_sba"
    assert result.n_folds >= 1
    assert result.metrics.wape == result.metrics.wape  # finite (not NaN)
