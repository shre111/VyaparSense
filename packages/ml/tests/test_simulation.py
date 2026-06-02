"""Tests for the inventory-policy simulation and business KPIs."""

from __future__ import annotations

import pytest

from vyaparsense_ml.replenishment.simulation import SimulationResult, simulate_policy


def test_no_stockout_when_amply_stocked() -> None:
    # plenty of starting stock, low steady demand, no reorder needed
    result = simulate_policy(
        [5.0] * 10,
        reorder_point=0.0,
        order_up_to=0.0,
        lead_time_days=3,
        initial_on_hand=1000.0,
    )
    assert result.units_demanded == pytest.approx(50.0)
    assert result.units_sold == pytest.approx(50.0)
    assert result.units_lost == 0.0
    assert result.fill_rate == pytest.approx(1.0)
    assert result.stockout_days == 0
    assert result.service_level == pytest.approx(1.0)


def test_stockout_when_no_replenishment() -> None:
    # 10 on hand, 5/day, no reordering -> stock out after day 2
    result = simulate_policy(
        [5.0] * 6,
        reorder_point=0.0,
        order_quantity=0.001,  # effectively no real replenishment within horizon
        lead_time_days=99,
        initial_on_hand=10.0,
    )
    assert result.units_sold == pytest.approx(10.0)
    assert result.units_lost == pytest.approx(20.0)
    assert result.fill_rate == pytest.approx(10.0 / 30.0)
    assert result.stockout_days >= 1
    assert result.service_level < 1.0


def test_reorder_arrives_after_lead_time() -> None:
    # start 10, demand 4/day, ROP 8, order-up-to 20, lead 2.
    # day0: recv none; sell 4 -> 6; position 6<=8 -> order 14 arriving day2
    # day1: sell 4 -> 2; position 2+14=16 >8 no order
    # day2: receive 14 -> 16; sell 4 -> 12; ...
    result = simulate_policy(
        [4.0] * 6,
        reorder_point=8.0,
        order_up_to=20.0,
        lead_time_days=2,
        initial_on_hand=10.0,
    )
    # no day should have gone negative / all demand met (24 demanded)
    assert result.units_demanded == pytest.approx(24.0)
    assert result.units_sold == pytest.approx(24.0)
    assert result.fill_rate == pytest.approx(1.0)
    assert result.n_orders >= 1


def test_fixed_order_quantity_policy() -> None:
    result = simulate_policy(
        [3.0] * 20,
        reorder_point=5.0,
        order_quantity=15.0,
        lead_time_days=2,
        initial_on_hand=10.0,
    )
    assert isinstance(result, SimulationResult)
    assert result.n_orders >= 1
    assert result.days == 20


def test_inventory_turns_and_avg_on_hand() -> None:
    # constant: start 100, demand 10/day for 10 days, no reorder.
    # on_hand end-of-day: 90,80,...,0 -> avg 45 ; sold 100 -> turns 100/45
    result = simulate_policy(
        [10.0] * 10,
        reorder_point=0.0,
        order_quantity=0.001,
        lead_time_days=99,
        initial_on_hand=100.0,
    )
    assert result.avg_on_hand == pytest.approx(45.0)
    assert result.units_sold == pytest.approx(100.0)
    assert result.inventory_turns == pytest.approx(100.0 / 45.0)


def test_dead_stock_value_accrues_on_no_sale_stretch() -> None:
    # demand zero throughout; 50 units sit idle. days_since_sale reaches
    # dead_stock_days=3 on day index 2, so accrual runs days 2..9 = 8 days.
    result = simulate_policy(
        [0.0] * 10,
        reorder_point=0.0,
        order_quantity=0.001,
        lead_time_days=99,
        initial_on_hand=50.0,
        unit_cost=2.0,
        dead_stock_days=3,
    )
    assert result.fill_rate == 1.0  # no demand -> trivially fully filled
    assert result.dead_stock_value == pytest.approx(8 * 50 * 2.0)


def test_no_dead_stock_when_selling_regularly() -> None:
    result = simulate_policy(
        [5.0] * 20,
        reorder_point=10.0,
        order_up_to=40.0,
        lead_time_days=2,
        initial_on_hand=30.0,
        unit_cost=2.0,
        dead_stock_days=5,
    )
    assert result.dead_stock_value == 0.0


def test_forecast_driven_beats_naive_on_stockouts() -> None:
    # spiky demand; a higher reorder point (better forecast/safety stock) should
    # reduce lost sales vs a thin one.
    demand = [5.0, 5.0, 30.0, 5.0, 5.0, 30.0, 5.0, 5.0, 30.0, 5.0] * 3
    thin = simulate_policy(
        demand, reorder_point=8.0, order_up_to=20.0, lead_time_days=2, initial_on_hand=10.0
    )
    thick = simulate_policy(
        demand, reorder_point=40.0, order_up_to=70.0, lead_time_days=2, initial_on_hand=40.0
    )
    assert thick.units_lost <= thin.units_lost
    assert thick.fill_rate >= thin.fill_rate


def test_validation_errors() -> None:
    with pytest.raises(ValueError, match="demand series is empty"):
        simulate_policy(
            [], reorder_point=0.0, order_up_to=10.0, lead_time_days=1, initial_on_hand=0.0
        )
    with pytest.raises(ValueError, match="exactly one of"):
        simulate_policy([1.0], reorder_point=0.0, lead_time_days=1, initial_on_hand=0.0)
    with pytest.raises(ValueError, match="exactly one of"):
        simulate_policy(
            [1.0],
            reorder_point=0.0,
            order_up_to=10.0,
            order_quantity=5.0,
            lead_time_days=1,
            initial_on_hand=0.0,
        )
    with pytest.raises(ValueError, match="order_up_to"):
        simulate_policy(
            [1.0], reorder_point=10.0, order_up_to=5.0, lead_time_days=1, initial_on_hand=0.0
        )
    with pytest.raises(ValueError, match="lead_time_days"):
        simulate_policy(
            [1.0], reorder_point=0.0, order_up_to=10.0, lead_time_days=0, initial_on_hand=0.0
        )


def test_negative_demand_rejected() -> None:
    with pytest.raises(ValueError, match="demand must be >= 0"):
        simulate_policy(
            [5.0, -1.0], reorder_point=0.0, order_up_to=10.0, lead_time_days=1, initial_on_hand=20.0
        )
