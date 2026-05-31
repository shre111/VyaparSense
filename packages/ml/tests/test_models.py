"""Tests for the baseline forecasting models."""

from __future__ import annotations

import pytest

from vyaparsense_ml.forecasting.models import (
    Baseline,
    MovingAverage,
    Naive,
    SeasonalNaive,
)


def test_naive_repeats_last_value() -> None:
    assert Naive().forecast([3.0, 7.0, 5.0], 3) == [5.0, 5.0, 5.0]


def test_moving_average_uses_last_window() -> None:
    # mean of last 3 of [1,2,3,4,5,6] = (4+5+6)/3 = 5
    assert MovingAverage(window=3).forecast([1, 2, 3, 4, 5, 6], 2) == [5.0, 5.0]


def test_moving_average_clamps_window_to_history() -> None:
    # window larger than history -> average everything: (2+4)/2 = 3
    assert MovingAverage(window=10).forecast([2, 4], 1) == [3.0]


def test_moving_average_rejects_bad_window() -> None:
    with pytest.raises(ValueError, match="window"):
        MovingAverage(window=0)


def test_seasonal_naive_repeats_last_season() -> None:
    y = [1, 2, 3, 10, 20, 30]  # two seasons of length 3
    assert SeasonalNaive(season_length=3).forecast(y, 5) == [10.0, 20.0, 30.0, 10.0, 20.0]


def test_seasonal_naive_requires_full_season() -> None:
    with pytest.raises(ValueError, match="season_length"):
        SeasonalNaive(season_length=7).forecast([1, 2, 3], 1)


def test_seasonal_naive_rejects_bad_season_length() -> None:
    with pytest.raises(ValueError, match="season_length"):
        SeasonalNaive(season_length=0)


@pytest.mark.parametrize("model", [Naive(), MovingAverage(), SeasonalNaive(season_length=2)])
def test_empty_history_raises(model: Baseline) -> None:
    with pytest.raises(ValueError, match="empty history"):
        model.forecast([], 1)


@pytest.mark.parametrize("model", [Naive(), MovingAverage(), SeasonalNaive(season_length=1)])
def test_non_positive_horizon_raises(model: Baseline) -> None:
    with pytest.raises(ValueError, match="horizon"):
        model.forecast([1, 2, 3], 0)


@pytest.mark.parametrize("model", [Naive(), MovingAverage(window=4), SeasonalNaive()])
def test_models_satisfy_baseline_protocol(model: Baseline) -> None:
    assert isinstance(model, Baseline)
    assert isinstance(model.name, str)


def test_model_names_are_distinct_and_stable() -> None:
    assert Naive().name == "naive"
    assert MovingAverage(window=7).name == "moving_average_7"
    assert SeasonalNaive(season_length=7).name == "seasonal_naive_7"
