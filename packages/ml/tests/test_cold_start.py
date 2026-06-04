"""Tests for transfer-learning cold-start (borrow shape from donor series)."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pytest

from vyaparsense_ml.forecasting.cold_start import (
    cold_start_forecast,
    pooled_weekly_profile,
    select_donors,
    weekly_profile,
)

_START = dt.date(2024, 1, 1)  # a Monday


def _weekend_series(
    days: int = 56, weekday: int = 10, weekend: int = 30
) -> list[tuple[dt.date, int]]:
    """Higher demand on Sat/Sun (weekday()==5,6) than on weekdays."""
    out = []
    for i in range(days):
        d = _START + dt.timedelta(days=i)
        out.append((d, weekend if d.weekday() >= 5 else weekday))
    return out


def test_weekly_profile_is_normalized_to_mean_one() -> None:
    profile = weekly_profile(_weekend_series())
    assert profile is not None
    assert profile.shape == (7,)
    np.testing.assert_allclose(profile.mean(), 1.0, rtol=1e-9)
    # weekend positions (5,6) are above weekdays (0..4)
    assert profile[5] > profile[0]
    assert profile[6] > profile[4]


def test_weekly_profile_none_for_all_zero() -> None:
    zeros = [(_START + dt.timedelta(days=i), 0) for i in range(14)]
    assert weekly_profile(zeros) is None
    assert weekly_profile([]) is None


def test_pooled_profile_flat_when_no_usable_donors() -> None:
    flat = pooled_weekly_profile([[], [(_START, 0)]])
    np.testing.assert_allclose(flat, np.ones(7))


def test_select_donors_prefers_same_store() -> None:
    series = {
        ("S1", "A"): _weekend_series(weekday=10),
        ("S1", "B"): _weekend_series(weekday=12),
        ("S2", "C"): _weekend_series(weekday=11),
    }
    donors = select_donors(("S1", "NEW"), series, k=5)
    # only the same-store series qualify when same-store donors exist
    assert len(donors) == 2
    levels = {round(float(np.mean([u for _, u in h]))) for h in donors}
    assert levels == {
        round(float(np.mean([u for _, u in series[("S1", "A")]]))),
        round(float(np.mean([u for _, u in series[("S1", "B")]]))),
    }


def test_select_donors_excludes_short_and_target() -> None:
    series = {
        ("S1", "A"): _weekend_series(days=56),
        ("S1", "SHORT"): _weekend_series(days=5),  # below min_history
        ("S1", "NEW"): _weekend_series(days=3),
    }
    donors = select_donors(("S1", "NEW"), series, k=5, min_history=14)
    assert len(donors) == 1  # only ("S1","A")


def test_cold_start_borrows_shape_scaled_to_target_level() -> None:
    donors = [_weekend_series(weekday=10, weekend=30)]  # strong weekend shape
    # target: 1 week of flat-ish history at a small level (~2/day)
    target = [(_START + dt.timedelta(days=i), 2) for i in range(7)]
    # forecast the next 7 days: 2024-01-08 (Mon) .. 2024-01-14 (Sun)
    fc = cold_start_forecast(target, donors, horizon=7)
    assert len(fc) == 7
    assert all(v >= 0.0 for v in fc)
    # the borrowed weekend shape shows up: Sat/Sun forecasts exceed weekday ones
    sat, sun = fc[5], fc[6]  # 2024-01-13, -14
    mon, tue = fc[0], fc[1]  # 2024-01-08, -09
    assert sat > mon and sun > tue
    # scaled to the target's own level (~2), not the donor's (~16)
    assert max(fc) < 10.0


def test_cold_start_empty_target_uses_start_date_and_donor_level() -> None:
    donors = [_weekend_series(weekday=10, weekend=30)]
    fc = cold_start_forecast([], donors, horizon=7, start_date=dt.date(2024, 1, 8))
    assert len(fc) == 7
    # no target level -> uses donor mean level (~16), so values are donor-scaled
    assert max(fc) > 10.0


def test_cold_start_requires_history_or_start_date() -> None:
    with pytest.raises(ValueError, match="start_date"):
        cold_start_forecast([], [_weekend_series()], horizon=7)


def test_cold_start_invalid_horizon() -> None:
    with pytest.raises(ValueError, match="horizon must be"):
        cold_start_forecast(_weekend_series(), [], horizon=0)
