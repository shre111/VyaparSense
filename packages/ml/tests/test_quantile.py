"""Tests for the empirical quantile forecaster."""

from __future__ import annotations

import pytest

from vyaparsense_ml.forecasting.models import Naive, SeasonalNaive
from vyaparsense_ml.forecasting.quantile import (
    EmpiricalQuantileForecaster,
    QuantileForecaster,
    _empirical_quantile,
)


def test_empirical_quantile_interpolation() -> None:
    vals = [0.0, 10.0]  # type-7: q is a linear interpolation
    assert _empirical_quantile(vals, 0.0) == 0.0
    assert _empirical_quantile(vals, 1.0) == 10.0
    assert _empirical_quantile(vals, 0.5) == pytest.approx(5.0)


def test_empirical_quantile_single_value() -> None:
    assert _empirical_quantile([7.0], 0.9) == 7.0


def test_forecaster_satisfies_protocol() -> None:
    f = EmpiricalQuantileForecaster(Naive())
    assert isinstance(f, QuantileForecaster)
    assert f.name == "empirical_quantile[naive]"
    assert f.quantiles == (0.5, 0.9, 0.95)


def test_forecast_quantiles_shape_and_keys() -> None:
    f = EmpiricalQuantileForecaster(Naive(), quantiles=(0.5, 0.9))
    out = f.forecast_quantiles(list(range(1, 21)), 3)
    assert set(out) == {0.5, 0.9}
    assert all(len(path) == 3 for path in out.values())


def test_quantiles_are_monotonic_nondecreasing() -> None:
    # higher quantile => at-or-above lower quantile, period by period
    f = EmpiricalQuantileForecaster(Naive(), quantiles=(0.1, 0.5, 0.9))
    y = [5.0, 7.0, 3.0, 9.0, 2.0, 8.0, 6.0, 4.0, 10.0, 1.0] * 3
    out = f.forecast_quantiles(y, 4)
    for i in range(4):
        assert out[0.1][i] <= out[0.5][i] <= out[0.9][i]


def test_forecast_quantiles_non_negative() -> None:
    f = EmpiricalQuantileForecaster(Naive(), quantiles=(0.05, 0.5))
    out = f.forecast_quantiles([0.0, 0.0, 5.0, 0.0, 0.0, 3.0, 0.0, 0.0], 2)
    assert all(v >= 0.0 for path in out.values() for v in path)


def test_residual_window_caps_history_used() -> None:
    # smoke: a small window still produces valid quantiles on a long series
    f = EmpiricalQuantileForecaster(Naive(), quantiles=(0.9,), residual_window=10)
    out = f.forecast_quantiles(list(range(200)), 1)
    assert len(out[0.9]) == 1 and out[0.9][0] >= 0.0


def test_degenerate_short_history_falls_back_to_point() -> None:
    # one observation => no residual => quantiles equal the (clamped) point
    f = EmpiricalQuantileForecaster(Naive(), quantiles=(0.5, 0.95))
    out = f.forecast_quantiles([4.0], 2)
    assert out[0.5] == [4.0, 4.0]
    assert out[0.95] == [4.0, 4.0]


def test_rejects_bad_quantiles() -> None:
    with pytest.raises(ValueError, match="at least one quantile"):
        EmpiricalQuantileForecaster(Naive(), quantiles=())
    for bad in (0.0, 1.0, 1.2):
        with pytest.raises(ValueError, match="quantile must be"):
            EmpiricalQuantileForecaster(Naive(), quantiles=(bad,))


def test_rejects_bad_residual_window() -> None:
    with pytest.raises(ValueError, match="residual_window"):
        EmpiricalQuantileForecaster(Naive(), residual_window=0)


def test_rejects_bad_horizon_and_empty() -> None:
    f = EmpiricalQuantileForecaster(Naive())
    with pytest.raises(ValueError, match="horizon"):
        f.forecast_quantiles([1.0, 2.0, 3.0], 0)
    with pytest.raises(ValueError, match="empty history"):
        f.forecast_quantiles([], 1)


def test_wraps_any_baseline() -> None:
    f = EmpiricalQuantileForecaster(SeasonalNaive(season_length=7), quantiles=(0.9,))
    out = f.forecast_quantiles(list(range(1, 36)), 7)
    assert len(out[0.9]) == 7
