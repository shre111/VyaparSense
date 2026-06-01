"""Intermittent-demand models (model ladder rung 3; ``CLAUDE.md`` §4).

For sparse / lumpy SKUs (many zero-demand periods) the classical ETS/ARIMA and
the naive baselines forecast poorly. The Croston family decomposes demand into
*size* and *inter-arrival interval* and smooths each separately:

* :class:`Croston` — Croston's classic method.
* :class:`CrostonSBA` — Syntetos-Boylan Approximation; debiases Croston (usually
  more accurate).
* :class:`TSB` — Teunter-Syntetos-Babai; smooths demand *probability* instead of
  interval, so it can decay toward zero for obsolescent SKUs.

Thin adapters over Nixtla ``statsforecast`` (ADR-004) conforming to the
:class:`~vyaparsense_ml.forecasting.models.Baseline` protocol, so the existing
backtest/selection harness uses them unchanged. All three produce a *flat*
forecast (one smoothed level repeated across the horizon) — combine with
temporal aggregation/GBM later for trend+seasonality.

As with the classical adapters, negatives are clamped to zero (demand is
non-negative) and a non-finite optimizer result falls back to the flat
:class:`~vyaparsense_ml.forecasting.models.Naive` forecast so one bad series
never poisons a pooled backtest. ``numpy`` is the only heavy import.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from statsforecast.models import TSB as _SFTSB
from statsforecast.models import CrostonClassic as _SFCrostonClassic
from statsforecast.models import CrostonSBA as _SFCrostonSBA

from vyaparsense_ml.forecasting.models import Naive


def _validate(y: Sequence[float], h: int) -> None:
    if h < 1:
        raise ValueError(f"horizon must be >= 1, got {h}")
    if len(y) == 0:
        raise ValueError("cannot forecast from empty history")


def _finite_nonneg(values: np.ndarray, y: Sequence[float], h: int) -> list[float]:
    """Clamp negatives to zero; fall back to a flat naive forecast if non-finite."""
    if not np.all(np.isfinite(values)):
        return Naive().forecast(y, h)
    return [max(0.0, float(v)) for v in values]


@dataclass(frozen=True)
class Croston:
    """Croston's classic intermittent-demand method."""

    @property
    def name(self) -> str:
        return "croston"

    def forecast(self, y: Sequence[float], h: int) -> list[float]:
        _validate(y, h)
        arr = np.asarray(y, dtype=np.float64)
        out = _SFCrostonClassic().forecast(y=arr, h=h)["mean"]
        return _finite_nonneg(np.asarray(out, dtype=np.float64), y, h)


@dataclass(frozen=True)
class CrostonSBA:
    """Syntetos-Boylan Approximation (debiased Croston)."""

    @property
    def name(self) -> str:
        return "croston_sba"

    def forecast(self, y: Sequence[float], h: int) -> list[float]:
        _validate(y, h)
        arr = np.asarray(y, dtype=np.float64)
        out = _SFCrostonSBA().forecast(y=arr, h=h)["mean"]
        return _finite_nonneg(np.asarray(out, dtype=np.float64), y, h)


@dataclass(frozen=True)
class TSB:
    """Teunter-Syntetos-Babai; smooths demand probability (handles obsolescence).

    ``alpha_d`` smooths demand size, ``alpha_p`` smooths demand probability; both
    in ``(0, 1]``. Defaults follow common practice (0.1 / 0.1).
    """

    alpha_d: float = 0.1
    alpha_p: float = 0.1

    def __post_init__(self) -> None:
        for label, a in (("alpha_d", self.alpha_d), ("alpha_p", self.alpha_p)):
            if not 0.0 < a <= 1.0:
                raise ValueError(f"{label} must be in (0, 1], got {a}")

    @property
    def name(self) -> str:
        return "tsb"

    def forecast(self, y: Sequence[float], h: int) -> list[float]:
        _validate(y, h)
        arr = np.asarray(y, dtype=np.float64)
        out = _SFTSB(alpha_d=self.alpha_d, alpha_p=self.alpha_p).forecast(y=arr, h=h)["mean"]
        return _finite_nonneg(np.asarray(out, dtype=np.float64), y, h)
