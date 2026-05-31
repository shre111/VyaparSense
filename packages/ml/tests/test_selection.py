"""Tests for per-series model selection by backtest."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from vyaparsense_ml.forecasting.models import Baseline, MovingAverage, Naive, SeasonalNaive
from vyaparsense_ml.forecasting.selection import select_model, select_per_series

_MODELS: list[Baseline] = [Naive(), MovingAverage(window=7), SeasonalNaive(season_length=7)]


def test_seasonal_series_picks_seasonal_naive() -> None:
    season = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 20.0]
    y = season * 8  # strongly seasonal -> seasonal naive should win
    result = select_model(y, _MODELS, min_train_size=14, horizon=7, step=7, season_length=7)
    assert result.best == "seasonal_naive_7"


def test_ranking_is_sorted_by_wape() -> None:
    season = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 20.0]
    y = season * 8
    result = select_model(y, _MODELS, min_train_size=14, horizon=7, step=7, season_length=7)
    wapes = [w for _, w in result.ranking]
    assert wapes == sorted(wapes)
    assert result.ranking[0][0] == result.best


def test_empty_models_raises() -> None:
    with pytest.raises(ValueError, match="at least one"):
        select_model([1.0, 2.0, 3.0], [], min_train_size=1)


def test_select_per_series_maps_every_key() -> None:
    start = date(2024, 1, 1)
    season = [1, 2, 3, 4, 5, 6, 20]
    points = [(start + timedelta(days=i), season[i % 7]) for i in range(56)]
    series = {
        ("STORE-1", "SKU-A"): points,
        ("STORE-1", "SKU-B"): points,
    }
    out = select_per_series(series, _MODELS, min_train_size=14, horizon=7, step=7, season_length=7)
    assert set(out) == {("STORE-1", "SKU-A"), ("STORE-1", "SKU-B")}
    assert out[("STORE-1", "SKU-A")].best == "seasonal_naive_7"
