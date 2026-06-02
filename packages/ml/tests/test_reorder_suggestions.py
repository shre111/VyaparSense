"""Tests for service-level reorder suggestions."""

from __future__ import annotations

import pytest

from vyaparsense_ml.forecasting.models import Naive
from vyaparsense_ml.replenishment.suggestions import (
    ReorderSuggestion,
    build_reorder_suggestion,
    suggest_reorder,
)


def test_build_reorder_point_sums_quantile_over_protection_window() -> None:
    # lead 3 days; median 10/day, 0.95-quantile 14/day
    s = build_reorder_suggestion(
        [10.0] * 5,
        [14.0] * 5,
        service_level=0.95,
        lead_time_days=3,
        on_hand=0.0,
    )
    assert s.expected_demand == pytest.approx(30.0)  # 10*3
    assert s.reorder_point == pytest.approx(42.0)  # 14*3
    assert s.safety_stock == pytest.approx(12.0)  # 42 - 30


def test_protection_window_includes_review_period() -> None:
    s = build_reorder_suggestion(
        [10.0] * 10,
        [14.0] * 10,
        service_level=0.95,
        lead_time_days=3,
        review_period_days=4,  # protection = 7
        on_hand=0.0,
    )
    assert s.expected_demand == pytest.approx(70.0)  # 10*7
    assert s.reorder_point == pytest.approx(98.0)  # 14*7


def test_should_reorder_when_on_hand_at_or_below_reorder_point() -> None:
    low = build_reorder_suggestion(
        [10.0] * 3, [12.0] * 3, service_level=0.9, lead_time_days=3, on_hand=20.0
    )
    assert low.should_reorder is True
    # order back up to the reorder point: 36 - 20 = 16
    assert low.order_quantity == pytest.approx(16.0)

    high = build_reorder_suggestion(
        [10.0] * 3, [12.0] * 3, service_level=0.9, lead_time_days=3, on_hand=100.0
    )
    assert high.should_reorder is False
    assert high.order_quantity == 0.0


def test_eoq_floors_the_order_quantity() -> None:
    s = build_reorder_suggestion(
        [10.0] * 3,
        [12.0] * 3,
        service_level=0.9,
        lead_time_days=3,
        on_hand=30.0,  # reorder point 36 -> raw order 6
        eoq=50.0,
    )
    assert s.should_reorder is True
    assert s.order_quantity == pytest.approx(50.0)  # floored at EOQ


def test_days_of_cover_uses_mean_daily_demand() -> None:
    # protection 4, expected 40 -> mean daily 10; on_hand 25 -> 2.5 days
    s = build_reorder_suggestion(
        [10.0] * 4, [13.0] * 4, service_level=0.95, lead_time_days=4, on_hand=25.0
    )
    assert s.days_of_cover == pytest.approx(2.5)


def test_safety_stock_never_negative() -> None:
    # pathological: quantile path below median path -> clamp safety stock to 0
    s = build_reorder_suggestion(
        [10.0] * 3, [8.0] * 3, service_level=0.6, lead_time_days=3, on_hand=0.0
    )
    assert s.safety_stock == 0.0


def test_build_validates_inputs() -> None:
    with pytest.raises(ValueError, match="service_level"):
        build_reorder_suggestion([1.0], [1.0], service_level=1.0, lead_time_days=1, on_hand=0.0)
    with pytest.raises(ValueError, match="lead_time_days"):
        build_reorder_suggestion([1.0], [1.0], service_level=0.9, lead_time_days=0, on_hand=0.0)
    with pytest.raises(ValueError, match="on_hand"):
        build_reorder_suggestion([1.0], [1.0], service_level=0.9, lead_time_days=1, on_hand=-1.0)


def test_build_rejects_short_paths() -> None:
    with pytest.raises(ValueError, match="shorter than protection"):
        build_reorder_suggestion(
            [10.0, 10.0], [12.0, 12.0], service_level=0.9, lead_time_days=5, on_hand=0.0
        )


def test_suggest_reorder_end_to_end_with_naive() -> None:
    # flat history -> Naive forecasts the last value; high SL -> reorder point >= expected
    history = [10.0] * 40
    s = suggest_reorder(
        Naive(),
        history,
        lead_time_days=7,
        service_level=0.95,
        on_hand=0.0,
    )
    assert isinstance(s, ReorderSuggestion)
    assert s.service_level == 0.95
    assert s.reorder_point >= s.expected_demand
    assert s.should_reorder is True  # on_hand 0 <= reorder point
    assert s.order_quantity > 0.0


def test_suggest_reorder_higher_service_level_orders_more() -> None:
    # noisy history so quantiles spread; higher SL => higher reorder point
    history = [5.0, 15.0, 8.0, 12.0, 3.0, 20.0, 7.0, 11.0] * 6
    low = suggest_reorder(Naive(), history, lead_time_days=7, service_level=0.80, on_hand=0.0)
    high = suggest_reorder(Naive(), history, lead_time_days=7, service_level=0.99, on_hand=0.0)
    assert high.reorder_point >= low.reorder_point


def test_suggest_reorder_validates_inputs() -> None:
    with pytest.raises(ValueError, match="service_level"):
        suggest_reorder(Naive(), [1.0] * 30, lead_time_days=7, service_level=0.0, on_hand=0.0)
    with pytest.raises(ValueError, match="lead_time_days"):
        suggest_reorder(Naive(), [1.0] * 30, lead_time_days=0, on_hand=0.0)
