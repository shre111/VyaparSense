"""Hierarchical reconciliation: coherent store/SKU forecasts (``CLAUDE.md`` §4 rung 5).

Independent per-series forecasts don't add up — the SKU forecasts rarely sum to
the store forecast, and stores rarely sum to the total. Reconciliation projects a
set of *base* forecasts (made at every level) onto the one coherent set that
respects the aggregation structure, so the numbers a user sees are consistent
across levels.

The hierarchy here is the one the data supports: ``total -> store -> (store, sku)``.
``S`` is the summing matrix mapping the bottom level to every node; reconciliation
is ``yhat = S G yhat_base`` for a method-specific ``G``:

* ``bottom_up`` — ``G`` selects the bottom rows (sum upward; ignores the
  aggregate-level base forecasts).
* ``ols`` — ``G = (Sᵀ S)⁻¹ Sᵀ``, the unweighted optimal projection; it blends
  every level's base forecast, which is where reconciliation can *improve*
  accuracy, not just enforce coherence.

Results are coherent by construction, and the bottom level is clamped to
non-negative before aggregating (demand can't be negative) — clamping the bottom
keeps the aggregates coherent. numpy only.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

import numpy as np
import numpy.typing as npt

from vyaparsense_ml.cleaning import SeriesKey

FloatArray = npt.NDArray[np.float64]

#: Node id of the top of the hierarchy.
TOTAL = "total"


def store_node(store: str) -> str:
    """Node id for a store-level aggregate."""
    return f"store:{store}"


def bottom_node(key: SeriesKey) -> str:
    """Node id for a bottom ``(store, sku)`` series."""
    return f"{key[0]}/{key[1]}"


@dataclass(frozen=True)
class Hierarchy:
    """A ``total -> store -> (store, sku)`` tree and its summing matrix.

    ``nodes`` lists every node id top-down (total, then stores, then the bottom
    series); ``bottom`` is the ordered bottom keys; ``S`` has shape
    ``(n_nodes, n_bottom)`` with each row summing the bottom series beneath that
    node (the bottom block is the identity).
    """

    nodes: tuple[str, ...]
    bottom: tuple[SeriesKey, ...]
    S: FloatArray

    @property
    def n_nodes(self) -> int:
        return len(self.nodes)

    @property
    def n_bottom(self) -> int:
        return len(self.bottom)


def build_hierarchy(keys: Iterable[SeriesKey]) -> Hierarchy:
    """Build the ``total -> store -> (store, sku)`` hierarchy from bottom keys."""
    bottom = tuple(sorted(set(keys)))
    if not bottom:
        raise ValueError("need at least one (store, sku) series to build a hierarchy")
    stores = sorted({store for store, _ in bottom})

    node_ids = [TOTAL, *(store_node(s) for s in stores), *(bottom_node(k) for k in bottom)]
    s_matrix = np.zeros((len(node_ids), len(bottom)), dtype=np.float64)
    s_matrix[0, :] = 1.0  # total = sum of all bottoms
    for i, store in enumerate(stores, start=1):
        for j, (b_store, _sku) in enumerate(bottom):
            if b_store == store:
                s_matrix[i, j] = 1.0
    offset = 1 + len(stores)  # bottom block is the identity
    for j in range(len(bottom)):
        s_matrix[offset + j, j] = 1.0
    return Hierarchy(nodes=tuple(node_ids), bottom=bottom, S=s_matrix)


def aggregate_history(
    series: Mapping[SeriesKey, list[tuple[date, int]]],
    hierarchy: Hierarchy,
) -> dict[str, list[tuple[date, float]]]:
    """Sum the bottom series up to every node, giving each node its own history.

    Missing ``(key, date)`` cells count as zero demand. The aggregate histories
    are what you forecast to get the aggregate-level *base* forecasts that
    reconciliation then blends.
    """
    by_key = {key: dict(points) for key, points in series.items()}
    out: dict[str, list[tuple[date, float]]] = {}
    for node_idx, node in enumerate(hierarchy.nodes):
        covered = [
            hierarchy.bottom[j] for j in range(hierarchy.n_bottom) if hierarchy.S[node_idx, j]
        ]
        dates = sorted({d for key in covered for d in by_key.get(key, {})})
        out[node] = [
            (d, float(sum(by_key.get(key, {}).get(d, 0) for key in covered))) for d in dates
        ]
    return out


def _reconciliation_matrix(hierarchy: Hierarchy, method: str) -> FloatArray:
    """The ``G`` that maps base forecasts (all nodes) to the bottom level."""
    if method == "bottom_up":
        g = np.zeros((hierarchy.n_bottom, hierarchy.n_nodes), dtype=np.float64)
        offset = hierarchy.n_nodes - hierarchy.n_bottom
        for j in range(hierarchy.n_bottom):
            g[j, offset + j] = 1.0
        return g
    if method == "ols":
        s = hierarchy.S
        return np.asarray(np.linalg.inv(s.T @ s) @ s.T, dtype=np.float64)
    raise ValueError(f"unknown reconciliation method: {method!r} (use 'bottom_up' or 'ols')")


def reconcile(
    base: Mapping[str, FloatArray],
    hierarchy: Hierarchy,
    *,
    method: str = "ols",
) -> dict[str, FloatArray]:
    """Reconcile per-node base forecasts into one coherent set.

    ``base`` maps every node id to its base forecast vector (all the same length
    ``h``). Returns a coherent forecast per node; the bottom level is clamped to
    non-negative first (so aggregates stay coherent and demand stays >= 0).

    Raises:
        ValueError: a node is missing, vectors differ in length, or bad method.
    """
    missing = [node for node in hierarchy.nodes if node not in base]
    if missing:
        raise ValueError(f"base forecasts missing for nodes: {missing}")
    horizons = {base[node].shape[0] for node in hierarchy.nodes}
    if len(horizons) != 1:
        raise ValueError(f"base forecasts must share one horizon, got lengths {sorted(horizons)}")

    yhat_base = np.vstack([base[node] for node in hierarchy.nodes])  # (n_nodes, h)
    g = _reconciliation_matrix(hierarchy, method)
    bottom_rec = np.maximum(0.0, g @ yhat_base)  # (n_bottom, h), demand >= 0
    rec = hierarchy.S @ bottom_rec  # (n_nodes, h), coherent
    return {node: np.asarray(rec[i], dtype=np.float64) for i, node in enumerate(hierarchy.nodes)}


def coherence_error(forecasts: Mapping[str, FloatArray], hierarchy: Hierarchy) -> float:
    """Max absolute gap between a node's forecast and the sum of its bottoms.

    Zero (up to float error) means the forecasts are coherent. A diagnostic for
    tests and for confirming a set of base forecasts is *in*coherent.
    """
    bottom = np.vstack([forecasts[bottom_node(k)] for k in hierarchy.bottom])
    implied = hierarchy.S @ bottom
    actual = np.vstack([forecasts[node] for node in hierarchy.nodes])
    return float(np.max(np.abs(implied - actual)))
