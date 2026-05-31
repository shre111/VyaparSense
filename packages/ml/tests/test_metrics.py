"""Tests for forecast-accuracy metrics."""

from __future__ import annotations

import math

import pytest

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


def test_mae_and_rmse() -> None:
    y_true = [0.0, 0.0, 0.0]
    y_pred = [3.0, 0.0, 4.0]  # errors 3, 0, 4
    assert mae(y_true, y_pred) == pytest.approx(7 / 3)
    assert rmse(y_true, y_pred) == pytest.approx(math.sqrt(25 / 3))


def test_bias_sign() -> None:
    # forecast above actual -> positive bias (over-forecast)
    assert bias([1.0, 1.0], [2.0, 3.0]) == pytest.approx(1.5)
    assert bias([5.0, 5.0], [3.0, 3.0]) == pytest.approx(-2.0)


def test_wape_known_value() -> None:
    # sum|err| = 2 + 1 = 3 ; sum|y| = 10 + 20 = 30 -> 0.1
    assert wape([10.0, 20.0], [12.0, 21.0]) == pytest.approx(0.1)


def test_wape_perfect_is_zero() -> None:
    assert wape([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0


def test_wape_zero_actuals() -> None:
    assert wape([0.0, 0.0], [0.0, 0.0]) == 0.0  # perfect on no demand
    assert math.isinf(wape([0.0, 0.0], [1.0, 0.0]))  # error with nothing to scale


def test_mape_skips_zero_actuals() -> None:
    # only the non-zero actual (4 -> off by 2) counts: 0.5
    assert mape([0.0, 4.0], [1.0, 6.0]) == pytest.approx(0.5)


def test_mape_all_zero_actuals_is_inf() -> None:
    assert math.isinf(mape([0.0, 0.0], [1.0, 2.0]))


def test_mase_against_seasonal_naive() -> None:
    # train increases by 1 each step -> lag-1 scale = 1.0
    y_train = [1.0, 2.0, 3.0, 4.0, 5.0]
    # test MAE = 2.0 -> MASE = 2.0 / 1.0 = 2.0
    assert mase([10.0, 12.0], [12.0, 14.0], y_train, season_length=1) == pytest.approx(2.0)


def test_mase_zero_scale_flat_train() -> None:
    y_train = [5.0, 5.0, 5.0, 5.0]  # flat -> scale 0
    assert mase([5.0], [5.0], y_train) == 0.0
    assert math.isinf(mase([5.0], [9.0], y_train))


def test_mase_requires_enough_training() -> None:
    with pytest.raises(ValueError, match="training points"):
        mase([1.0], [1.0], [1.0], season_length=1)


def test_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="length mismatch"):
        wape([1.0, 2.0], [1.0])


def test_empty_raises() -> None:
    with pytest.raises(ValueError, match="at least one"):
        mae([], [])


def test_compute_metrics_bundle() -> None:
    m = compute_metrics(
        [10.0, 20.0],
        [12.0, 21.0],
        y_train=[1.0, 2.0, 3.0, 4.0],
        season_length=1,
    )
    assert isinstance(m, ForecastMetrics)
    assert m.wape == pytest.approx(0.1)
    assert m.mase is not None


def test_compute_metrics_mase_none_without_train() -> None:
    m = compute_metrics([1.0, 2.0], [1.0, 2.0])
    assert m.mase is None
