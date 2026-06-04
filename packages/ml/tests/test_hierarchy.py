"""Tests for hierarchical reconciliation (total -> store -> SKU coherence)."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pytest

from vyaparsense_ml.forecasting.hierarchy import (
    TOTAL,
    FloatArray,
    Hierarchy,
    aggregate_history,
    bottom_node,
    build_hierarchy,
    coherence_error,
    reconcile,
    store_node,
)

_KEYS = [("S1", "A"), ("S1", "B"), ("S2", "A")]


def _hier() -> Hierarchy:
    return build_hierarchy(_KEYS)


def test_build_hierarchy_shape_and_nodes() -> None:
    h = _hier()
    # total + 2 stores + 3 bottoms = 6 nodes; 3 bottom columns
    assert h.n_nodes == 6
    assert h.n_bottom == 3
    assert h.S.shape == (6, 3)
    assert h.nodes[0] == TOTAL
    assert set(h.nodes) == {
        TOTAL,
        store_node("S1"),
        store_node("S2"),
        bottom_node(("S1", "A")),
        bottom_node(("S1", "B")),
        bottom_node(("S2", "A")),
    }


def test_summing_matrix_rows() -> None:
    h = _hier()
    idx = {node: i for i, node in enumerate(h.nodes)}
    # bottom order is sorted: (S1,A),(S1,B),(S2,A)
    assert list(h.S[idx[TOTAL]]) == [1.0, 1.0, 1.0]
    assert list(h.S[idx[store_node("S1")]]) == [1.0, 1.0, 0.0]
    assert list(h.S[idx[store_node("S2")]]) == [0.0, 0.0, 1.0]
    assert list(h.S[idx[bottom_node(("S1", "B"))]]) == [0.0, 1.0, 0.0]


def test_build_hierarchy_empty_raises() -> None:
    with pytest.raises(ValueError, match="at least one"):
        build_hierarchy([])


def test_aggregate_history_sums_levels() -> None:
    d0 = date(2024, 1, 1)
    series = {
        ("S1", "A"): [(d0, 3), (d0 + timedelta(days=1), 5)],
        ("S1", "B"): [(d0, 2), (d0 + timedelta(days=1), 1)],
        ("S2", "A"): [(d0, 10)],  # no day-2 -> counts as 0 in aggregates
    }
    agg = aggregate_history(series, build_hierarchy(series.keys()))
    assert agg[TOTAL] == [(d0, 15.0), (d0 + timedelta(days=1), 6.0)]
    assert agg[store_node("S1")] == [(d0, 5.0), (d0 + timedelta(days=1), 6.0)]
    assert agg[store_node("S2")] == [(d0, 10.0)]


def _base_forecasts(h: Hierarchy, horizon: int = 3) -> dict[str, FloatArray]:
    # deliberately INCOHERENT base forecasts (each level forecast independently)
    rng = np.random.default_rng(0)
    return {node: rng.uniform(1.0, 10.0, size=horizon) for node in h.nodes}


def test_base_forecasts_are_incoherent() -> None:
    h = _hier()
    assert coherence_error(_base_forecasts(h), h) > 1e-6


def test_bottom_up_is_coherent_and_keeps_bottoms() -> None:
    h = _hier()
    base = _base_forecasts(h)
    rec = reconcile(base, h, method="bottom_up")
    assert coherence_error(rec, h) < 1e-9
    # bottom-up leaves the bottom forecasts untouched (non-negative here)
    for key in h.bottom:
        np.testing.assert_allclose(rec[bottom_node(key)], base[bottom_node(key)])
    # and the total equals the sum of the bottoms
    bottoms = np.vstack([base[bottom_node(k)] for k in h.bottom])
    np.testing.assert_allclose(rec[TOTAL], bottoms.sum(axis=0))


def test_ols_is_coherent_and_nonnegative() -> None:
    h = _hier()
    rec = reconcile(_base_forecasts(h), h, method="ols")
    assert coherence_error(rec, h) < 1e-9
    for vec in rec.values():
        assert np.all(vec >= 0.0)


def test_reconcile_missing_node_raises() -> None:
    h = _hier()
    base = _base_forecasts(h)
    del base[TOTAL]
    with pytest.raises(ValueError, match="missing for nodes"):
        reconcile(base, h)


def test_reconcile_horizon_mismatch_raises() -> None:
    h = _hier()
    base = _base_forecasts(h, horizon=3)
    base[TOTAL] = np.ones(4)
    with pytest.raises(ValueError, match="share one horizon"):
        reconcile(base, h)


def test_reconcile_unknown_method_raises() -> None:
    h = _hier()
    with pytest.raises(ValueError, match="unknown reconciliation method"):
        reconcile(_base_forecasts(h), h, method="middle_out")
