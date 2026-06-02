"""Tests for the replenishment core formulas."""

from __future__ import annotations

import math

import pytest

from vyaparsense_ml.replenishment import (
    days_of_cover,
    economic_order_quantity,
    order_up_to_level,
    reorder_point,
    safety_stock,
    service_level_z,
)


def test_service_level_z_known_values() -> None:
    assert service_level_z(0.5) == pytest.approx(0.0)
    assert service_level_z(0.95) == pytest.approx(1.6449, abs=1e-4)
    assert service_level_z(0.975) == pytest.approx(1.9600, abs=1e-4)


def test_service_level_z_higher_level_is_larger() -> None:
    assert service_level_z(0.99) > service_level_z(0.90) > service_level_z(0.80)


def test_service_level_z_rejects_out_of_range() -> None:
    for bad in (0.0, 1.0, -0.1, 1.5):
        with pytest.raises(ValueError, match="service_level"):
            service_level_z(bad)


def test_safety_stock_known_value() -> None:
    # z(0.95)=1.6449, std=10, lead=4 -> 1.6449 * 10 * 2 = 32.897
    assert safety_stock(10.0, 4.0, 0.95) == pytest.approx(32.897, abs=1e-2)


def test_safety_stock_zero_variability_is_zero() -> None:
    assert safety_stock(0.0, 7.0, 0.99) == 0.0


def test_safety_stock_scales_with_sqrt_lead_time() -> None:
    s1 = safety_stock(5.0, 1.0, 0.95)
    s4 = safety_stock(5.0, 4.0, 0.95)
    assert s4 == pytest.approx(2.0 * s1)  # sqrt(4)=2


def test_safety_stock_rejects_negatives() -> None:
    with pytest.raises(ValueError, match="demand_std"):
        safety_stock(-1.0, 4.0)
    with pytest.raises(ValueError, match="lead_time_days"):
        safety_stock(10.0, -1.0)


def test_reorder_point_deterministic() -> None:
    # std=0 -> just mean demand over lead time
    assert reorder_point(20.0, 5.0, demand_std=0.0) == pytest.approx(100.0)


def test_reorder_point_adds_safety_stock() -> None:
    # 20/day * 5 days = 100, plus safety stock
    rop = reorder_point(20.0, 5.0, demand_std=8.0, service_level=0.95)
    expected = 100.0 + safety_stock(8.0, 5.0, 0.95)
    assert rop == pytest.approx(expected)
    assert rop > 100.0


def test_reorder_point_rejects_negatives() -> None:
    with pytest.raises(ValueError, match="demand_mean"):
        reorder_point(-1.0, 5.0)
    with pytest.raises(ValueError, match="lead_time_days"):
        reorder_point(10.0, -5.0)


def test_eoq_known_value() -> None:
    # D=1000, order_cost=50, holding=2 -> sqrt(2*1000*50/2)=sqrt(50000)=223.6
    assert economic_order_quantity(1000.0, 50.0, 2.0) == pytest.approx(223.607, abs=1e-2)


def test_eoq_zero_demand_is_zero() -> None:
    assert economic_order_quantity(0.0, 50.0, 2.0) == 0.0


def test_eoq_rejects_bad_costs() -> None:
    with pytest.raises(ValueError, match="holding_cost_per_unit"):
        economic_order_quantity(1000.0, 50.0, 0.0)
    with pytest.raises(ValueError, match="order_cost"):
        economic_order_quantity(1000.0, -1.0, 2.0)
    with pytest.raises(ValueError, match="annual_demand"):
        economic_order_quantity(-1.0, 50.0, 2.0)


def test_days_of_cover_basic() -> None:
    assert days_of_cover(100.0, 20.0) == pytest.approx(5.0)


def test_days_of_cover_no_demand_is_inf() -> None:
    assert math.isinf(days_of_cover(50.0, 0.0))


def test_days_of_cover_no_stock_is_zero() -> None:
    assert days_of_cover(0.0, 20.0) == 0.0
    # zero stock even with zero demand is 0, not inf
    assert days_of_cover(0.0, 0.0) == 0.0


def test_days_of_cover_rejects_negatives() -> None:
    with pytest.raises(ValueError, match="on_hand"):
        days_of_cover(-1.0, 20.0)
    with pytest.raises(ValueError, match="demand_mean"):
        days_of_cover(100.0, -1.0)


def test_order_up_to_level_covers_lead_plus_review() -> None:
    # protection window = lead 5 + review 7 = 12 days
    s = order_up_to_level(10.0, 5.0, 7.0, demand_std=4.0, service_level=0.95)
    expected = reorder_point(10.0, 12.0, demand_std=4.0, service_level=0.95)
    assert s == pytest.approx(expected)
    # and strictly larger than the lead-time-only reorder point
    assert s > reorder_point(10.0, 5.0, demand_std=4.0, service_level=0.95)


def test_order_up_to_level_rejects_bad_review() -> None:
    with pytest.raises(ValueError, match="review_period_days"):
        order_up_to_level(10.0, 5.0, -1.0)
