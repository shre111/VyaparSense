"""Unit tests for the job-path forecaster: global LightGBM vs per-series champions.

Driving ``generate_forecasts_full`` directly (not through the endpoint) keeps
these fast and lets us pin the global-vs-champions decision deterministically.
"""

from __future__ import annotations

import datetime as dt

import pytest
from app.forecasting import DEFAULT_MODELS, generate_forecasts_full
from vyaparsense_ml.schema import SalesRecord

_START = dt.date(2024, 1, 1)
_WEEKLY = [8, 9, 7, 10, 12, 20, 18]

# Tests drive the decision logic, not the per-series ladder's quality, so they
# run the cheap baselines (not statsforecast/AutoARIMA) with few folds — fast CI.
_FAST_N_FOLDS = 2


def _seasonal_records(days: int = 56, store: str = "S1", sku: str = "K1") -> list[SalesRecord]:
    """A perfectly weekly series — seasonal-naive nails it (champion WAPE 0)."""
    return [
        SalesRecord(
            date=_START + dt.timedelta(days=i),
            store_id=store,
            sku_id=sku,
            units_sold=_WEEKLY[i % 7],
            price=10.0,
            promo_flag=False,
        )
        for i in range(days)
    ]


def _noisy_records(days: int = 56, store: str = "S1", sku: str = "K1") -> list[SalesRecord]:
    """Weekly + drift so no model is perfect (champion WAPE > 0)."""
    return [
        SalesRecord(
            date=_START + dt.timedelta(days=i),
            store_id=store,
            sku_id=sku,
            units_sold=_WEEKLY[i % 7] + (i % 3),
            price=10.0,
            promo_flag=False,
        )
        for i in range(days)
    ]


def test_empty_records_returns_none_decision() -> None:
    rows, decision = generate_forecasts_full([], models=DEFAULT_MODELS, n_folds=_FAST_N_FOLDS)
    assert rows == []
    assert decision.winner == "none"
    assert decision.n_series == 0


def test_perfect_seasonal_keeps_champion_over_global() -> None:
    rows, decision = generate_forecasts_full(
        _seasonal_records(), horizon=7, models=DEFAULT_MODELS, n_folds=_FAST_N_FOLDS
    )
    # seasonal-naive is exact here (WAPE 0); the global model cannot strictly beat 0
    assert decision.winner == "per_series"
    assert decision.champion_wape == 0.0
    assert decision.global_wape is not None and decision.global_wape >= 0.0
    assert decision.n_series == 1
    assert {r.model for r in rows} == {"seasonal_naive_7"}
    assert len(rows) == 7


def test_global_path_used_when_it_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    # force the global backtest to win; noisy data so champion WAPE > 0
    monkeypatch.setattr("app.forecasting._global_backtest_wape", lambda *a, **k: 0.0)
    rows, decision = generate_forecasts_full(
        _noisy_records(), horizon=7, models=DEFAULT_MODELS, n_folds=_FAST_N_FOLDS
    )
    assert decision.winner == "global"
    assert decision.global_wape == 0.0
    assert decision.champion_wape is not None and decision.champion_wape > 0.0
    # the real global model produced these (exercises fit + forecast_series)
    assert {r.model for r in rows} == {"global_lightgbm"}
    assert len(rows) == 7


def test_decision_reports_both_wapes_multi_series() -> None:
    records = _noisy_records(sku="A") + _noisy_records(sku="B")
    _rows, decision = generate_forecasts_full(
        records, horizon=7, models=DEFAULT_MODELS, n_folds=_FAST_N_FOLDS
    )
    assert decision.winner in {"global", "per_series"}
    assert decision.champion_wape is not None
    assert decision.global_wape is not None
    assert decision.n_series == 2


def test_as_of_truncates_and_dates_forward() -> None:
    rows, _decision = generate_forecasts_full(
        _seasonal_records(60),
        horizon=7,
        as_of=dt.date(2024, 2, 10),
        models=DEFAULT_MODELS,
        n_folds=_FAST_N_FOLDS,
    )
    dates = sorted(r.horizon_date for r in rows)
    assert dates[0] == dt.date(2024, 2, 11)
    assert dates[-1] == dt.date(2024, 2, 17)
