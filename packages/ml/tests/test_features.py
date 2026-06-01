"""Tests for global-model feature engineering (calendar/price/promo/lags/rolling)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from vyaparsense_ml.forecasting.features import build_features
from vyaparsense_ml.schema import SalesRecord


def _series(
    store: str, sku: str, units: list[int], *, start: date = date(2024, 1, 1), price: float = 10.0
) -> list[SalesRecord]:
    return [
        SalesRecord(
            date=start + timedelta(days=i),
            store_id=store,
            sku_id=sku,
            units_sold=u,
            price=price,
            promo_flag=False,
        )
        for i, u in enumerate(units)
    ]


def test_calendar_features_present_and_correct() -> None:
    recs = _series("A", "X", list(range(40)))
    df = build_features(recs, lags=(1,), roll_windows=(7,), dropna=False)
    # 2024-01-01 is a Monday -> dayofweek 0, not weekend, month 1
    first = df.iloc[0]
    assert first["dayofweek"] == 0
    assert first["is_weekend"] == 0
    assert first["month"] == 1
    # Saturday is index 5 (2024-01-06) -> weekend
    assert df.iloc[5]["is_weekend"] == 1
    for col in ("dow_sin", "dow_cos", "month_sin", "month_cos"):
        assert col in df.columns


def test_lag_features_are_past_values() -> None:
    recs = _series("A", "X", [10, 20, 30, 40, 50, 60, 70, 80])
    df = build_features(recs, lags=(1, 2), roll_windows=(), dropna=False)
    # lag_1 at position i is units at i-1
    assert df.iloc[3]["lag_1"] == 30
    assert df.iloc[3]["lag_2"] == 20
    # first row has no past -> NaN
    assert df.iloc[0]["lag_1"] != df.iloc[0]["lag_1"]  # NaN


def test_rolling_is_leakage_safe() -> None:
    # roll_mean_2 at t must use t-1, t-2 only (NOT the current value)
    recs = _series("A", "X", [10, 20, 30, 40, 50])
    df = build_features(recs, lags=(1,), roll_windows=(2,), dropna=False)
    # at index 2 (value 30): mean(10, 20) = 15, not mean(20, 30)
    assert df.iloc[2]["roll_mean_2"] == pytest.approx(15.0)
    assert df.iloc[3]["roll_mean_2"] == pytest.approx(25.0)


def test_rolling_does_not_cross_series_boundary() -> None:
    recs = _series("A", "X", [10, 20, 30, 40, 50]) + _series("B", "X", [1, 2, 3, 4, 5])
    df = build_features(recs, lags=(1,), roll_windows=(2,), dropna=False)
    b = df[df["store_id"] == "B"].reset_index(drop=True)
    # B's first two rolling values are NaN (its own history only); 3rd = mean(1,2)=1.5
    assert b.iloc[0]["roll_mean_2"] != b.iloc[0]["roll_mean_2"]  # NaN
    assert b.iloc[2]["roll_mean_2"] == pytest.approx(1.5)
    # B's lag_1 at row 0 must be NaN, never A's last value (50)
    assert b.iloc[0]["lag_1"] != b.iloc[0]["lag_1"]  # NaN


def test_dropna_removes_warmup_rows() -> None:
    recs = _series("A", "X", list(range(30)))
    df = build_features(recs, lags=(1, 7), roll_windows=(7,), dropna=True)
    # with max lag 7 and roll window 7 (needs 8 prior), the first rows are dropped
    assert not df[["lag_1", "lag_7", "roll_mean_7", "roll_std_7"]].isna().any().any()
    assert len(df) < 30


def test_price_and_promo_passed_through() -> None:
    recs = [
        SalesRecord(
            date=date(2024, 1, 1) + timedelta(days=i),
            store_id="A",
            sku_id="X",
            units_sold=i,
            price=9.5,
            promo_flag=(i % 2 == 0),
        )
        for i in range(10)
    ]
    df = build_features(recs, lags=(1,), roll_windows=(), dropna=False)
    assert (df["price"] == 9.5).all()
    assert df.iloc[0]["promo_flag"] == 1  # i=0 -> True -> 1
    assert df.iloc[1]["promo_flag"] == 0


def test_output_sorted_by_group_then_date() -> None:
    recs = _series("B", "X", [1, 2, 3]) + _series("A", "X", [4, 5, 6])
    df = build_features(recs, lags=(1,), roll_windows=(), dropna=False)
    stores = df["store_id"].tolist()
    assert stores == sorted(stores)  # A before B


def test_empty_records_raises() -> None:
    with pytest.raises(ValueError, match="no records"):
        build_features([])


def test_invalid_lags_and_windows_raise() -> None:
    recs = _series("A", "X", list(range(10)))
    with pytest.raises(ValueError, match="lags must be positive"):
        build_features(recs, lags=(0,))
    with pytest.raises(ValueError, match="roll_windows must be positive"):
        build_features(recs, roll_windows=(-1,))
