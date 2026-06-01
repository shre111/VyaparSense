"""Quantile (probabilistic) forecast metrics — Phase 3, last rung.

Point metrics (``metrics.py``) score a single number per period; service-level
reorder math (Phase 5) needs *quantile* forecasts (e.g. the 0.95 quantile of
demand → safety stock for a 95% service level). These metrics score those:

* **pinball loss** (a.k.a. quantile loss) — the proper scoring rule for a single
  quantile ``q``: underestimates are penalised by ``q``, overestimates by
  ``1 - q``. Lower is better; it is minimised in expectation by the true
  ``q``-quantile. This is the selection metric for probabilistic forecasts.
* **mean pinball loss** — pinball averaged over several quantiles (a discrete
  approximation to CRPS); the headline probabilistic accuracy number.
* **coverage** — fraction of actuals at or below the ``q``-quantile forecast.
  A calibrated forecast has coverage ≈ ``q``. Diagnostic, not a selection metric.

Losses are in demand units (same scale as the data). Pure stdlib.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def _check_pair(y_true: Sequence[float], y_pred: Sequence[float]) -> None:
    if len(y_true) != len(y_pred):
        raise ValueError(f"length mismatch: y_true={len(y_true)}, y_pred={len(y_pred)}")
    if len(y_true) == 0:
        raise ValueError("need at least one observation")


def _check_quantile(q: float) -> None:
    if not 0.0 < q < 1.0:
        raise ValueError(f"quantile must be in (0, 1), got {q}")


def pinball_loss(y_true: Sequence[float], y_pred: Sequence[float], q: float) -> float:
    """Mean pinball (quantile) loss at quantile ``q`` for forecasts ``y_pred``.

    For each period the loss is ``q * (y - yhat)`` when ``y >= yhat`` and
    ``(1 - q) * (yhat - y)`` otherwise. Returned as the mean over all periods.
    """
    _check_pair(y_true, y_pred)
    _check_quantile(q)
    total = 0.0
    for t, p in zip(y_true, y_pred, strict=True):
        diff = t - p
        total += q * diff if diff >= 0 else (q - 1.0) * diff
    return total / len(y_true)


def mean_pinball_loss(
    y_true: Sequence[float],
    quantile_preds: Mapping[float, Sequence[float]],
) -> float:
    """Average pinball loss across several quantiles (discrete CRPS proxy).

    ``quantile_preds`` maps each quantile level ``q`` to its per-period forecast.
    Requires at least one quantile; every forecast must align with ``y_true``.
    """
    if not quantile_preds:
        raise ValueError("need at least one quantile forecast")
    losses = [pinball_loss(y_true, preds, q) for q, preds in quantile_preds.items()]
    return sum(losses) / len(losses)


def coverage(y_true: Sequence[float], y_pred: Sequence[float], q: float) -> float:
    """Empirical coverage: fraction of actuals ``<=`` the ``q``-quantile forecast.

    A well-calibrated ``q``-quantile forecast has coverage close to ``q``.
    ``q`` is validated for consistency with the other quantile metrics, though
    the value itself is not used in the computation.
    """
    _check_pair(y_true, y_pred)
    _check_quantile(q)
    hits = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t <= p)
    return hits / len(y_true)
