"""Tests for quantile (probabilistic) forecast metrics."""

from __future__ import annotations

import pytest

from vyaparsense_ml.forecasting.quantile_metrics import (
    coverage,
    mean_pinball_loss,
    pinball_loss,
)


def test_pinball_loss_known_value() -> None:
    # q=0.9, actuals [10, 10], preds [8, 12].
    # period 1: y>=p (under-forecast by 2) -> 0.9 * 2 = 1.8
    # period 2: y<p  (over-forecast by 2)  -> (1-0.9) * 2 = 0.2
    # mean = (1.8 + 0.2) / 2 = 1.0
    assert pinball_loss([10.0, 10.0], [8.0, 12.0], 0.9) == pytest.approx(1.0)


def test_pinball_loss_zero_on_perfect() -> None:
    assert pinball_loss([3.0, 5.0, 7.0], [3.0, 5.0, 7.0], 0.5) == 0.0


def test_pinball_loss_median_is_half_mae() -> None:
    # at q=0.5 pinball loss equals half the MAE
    y, p = [1.0, 2.0, 9.0], [2.0, 2.0, 5.0]  # abs errors 1, 0, 4 -> MAE 5/3
    assert pinball_loss(y, p, 0.5) == pytest.approx((5 / 3) / 2)


def test_high_quantile_penalises_underforecast_more() -> None:
    # same magnitude miss: under-forecast costs more at a high quantile
    under = pinball_loss([10.0], [8.0], 0.9)  # actual above forecast
    over = pinball_loss([10.0], [12.0], 0.9)  # actual below forecast
    assert under > over


def test_pinball_rejects_bad_quantile() -> None:
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="quantile"):
            pinball_loss([1.0], [1.0], bad)


def test_pinball_length_mismatch_and_empty() -> None:
    with pytest.raises(ValueError, match="length mismatch"):
        pinball_loss([1.0, 2.0], [1.0], 0.5)
    with pytest.raises(ValueError, match="at least one"):
        pinball_loss([], [], 0.5)


def test_mean_pinball_averages_quantiles() -> None:
    y = [10.0, 10.0]
    preds = {0.5: [10.0, 10.0], 0.9: [8.0, 12.0]}  # losses 0.0 and 1.0
    assert mean_pinball_loss(y, preds) == pytest.approx(0.5)


def test_mean_pinball_requires_a_quantile() -> None:
    with pytest.raises(ValueError, match="at least one quantile"):
        mean_pinball_loss([1.0], {})


def test_coverage_counts_actuals_at_or_below() -> None:
    # preds = q-quantile; actuals <= pred count as covered
    # y=[1,5,9,9], p=[2,4,9,10] -> covered: 1<=2, 9<=9, 9<=10 => 3/4
    assert coverage([1.0, 5.0, 9.0, 9.0], [2.0, 4.0, 9.0, 10.0], 0.9) == pytest.approx(0.75)


def test_coverage_calibrated_high_quantile() -> None:
    # a forecast above every actual covers everything (1.0)
    assert coverage([1.0, 2.0, 3.0], [100.0, 100.0, 100.0], 0.9) == 1.0
    # a forecast below every actual covers nothing (0.0)
    assert coverage([1.0, 2.0, 3.0], [0.0, 0.0, 0.0], 0.9) == 0.0


def test_coverage_rejects_bad_quantile() -> None:
    with pytest.raises(ValueError, match="quantile"):
        coverage([1.0], [1.0], 0.0)
