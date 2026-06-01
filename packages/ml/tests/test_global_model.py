"""Tests for the global LightGBM model and its backtest.

Kept fast: small synthetic panels, few boosting rounds. These check the
contract (shape, recursion, non-negativity, determinism, validation, harness
integration), not LightGBM's accuracy — that's what the backtest measures.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from vyaparsense_ml.forecasting.features import feature_columns
from vyaparsense_ml.forecasting.global_backtest import global_backtest
from vyaparsense_ml.forecasting.global_model import GlobalLightGBM
from vyaparsense_ml.schema import SalesRecord

_LAGS = (1, 7)
_ROLLS = (7,)


def _fast(seed: int = 42) -> GlobalLightGBM:
    """A small, fast model config for tests."""
    return GlobalLightGBM(lags=_LAGS, roll_windows=_ROLLS, num_boost_round=30, seed=seed)


def _panel(n_days: int = 120, stores: tuple[str, ...] = ("A", "B")) -> list[SalesRecord]:
    """A multi-series panel with weekly seasonality + a per-series level."""
    start = date(2024, 1, 1)
    recs: list[SalesRecord] = []
    weekly = [20, 22, 19, 21, 25, 40, 38]
    for si, store in enumerate(stores):
        base = 10 * (si + 1)
        for i in range(n_days):
            units = base + weekly[i % 7] + (i // 7)  # level + season + slow trend
            recs.append(
                SalesRecord(
                    date=start + timedelta(days=i),
                    store_id=store,
                    sku_id="X",
                    units_sold=units,
                    price=10.0,
                    promo_flag=False,
                )
            )
    return recs


def test_fit_then_forecast_shape_and_nonneg() -> None:
    recs = _panel()
    model = _fast().fit(recs)
    series_a = [r for r in recs if r.store_id == "A"]
    out = model.forecast_series(series_a, 7)
    assert len(out) == 7
    assert all(isinstance(v, float) and v >= 0.0 and v == v for v in out)


def test_forecast_before_fit_raises() -> None:
    model = _fast()
    with pytest.raises(RuntimeError, match="not fitted"):
        model.forecast_series(_panel()[:30], 3)


def test_forecast_validates_horizon_and_empty_history() -> None:
    model = _fast().fit(_panel())
    with pytest.raises(ValueError, match="horizon"):
        model.forecast_series(_panel()[:30], 0)
    with pytest.raises(ValueError, match="empty history"):
        model.forecast_series([], 3)


def test_training_is_deterministic() -> None:
    recs = _panel()
    a = _fast(seed=7).fit(recs)
    b = _fast(seed=7).fit(recs)
    series_a = [r for r in recs if r.store_id == "A"]
    assert a.forecast_series(series_a, 5) == b.forecast_series(series_a, 5)


def test_feature_importance_keys_match_feature_columns() -> None:
    model = _fast().fit(_panel())
    imp = model.feature_importance()
    assert set(imp) == set(feature_columns(_LAGS, _ROLLS))
    assert all(isinstance(v, int) for v in imp.values())


def test_fit_too_short_raises() -> None:
    # one short series -> no rows survive feature dropna
    short = _panel(n_days=5, stores=("A",))
    with pytest.raises(ValueError, match="no training rows"):
        _fast().fit(short)


def test_recursive_forecast_tracks_level_difference() -> None:
    # store B has ~2x the level of A; forecasts should reflect that ordering
    recs = _panel()
    model = _fast().fit(recs)
    fa = model.forecast_series([r for r in recs if r.store_id == "A"], 7)
    fb = model.forecast_series([r for r in recs if r.store_id == "B"], 7)
    assert sum(fb) > sum(fa)


def test_global_backtest_runs_and_pools() -> None:
    recs = _panel(n_days=140)
    result = global_backtest(
        recs,
        min_train_days=90,
        horizon=7,
        n_folds=2,
        model=_fast(),
    )
    assert result.model == "global_lightgbm"
    assert result.n_series == 2
    assert result.n_folds >= 1
    assert result.metrics.wape == result.metrics.wape  # finite, not NaN
    assert result.metrics.wape >= 0.0


def test_global_backtest_validates_params() -> None:
    recs = _panel(n_days=60)
    with pytest.raises(ValueError, match="min_train_days"):
        global_backtest(recs, min_train_days=0)
    with pytest.raises(ValueError, match="horizon"):
        global_backtest(recs, min_train_days=30, horizon=0)


def test_global_backtest_too_short_raises() -> None:
    recs = _panel(n_days=20)
    with pytest.raises(ValueError, match="single fold"):
        global_backtest(recs, min_train_days=30, horizon=7)
