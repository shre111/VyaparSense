"""Probabilistic (quantile) forecasting — Phase 3, final rung (``CLAUDE.md`` §4).

A point forecast answers "how much will sell"; reorder math needs "how much
might sell, at a service level" — i.e. demand *quantiles*. The 0.95 quantile of
lead-time demand, for example, drives the safety stock for a 95% service level
(Phase 5).

Rather than rely on each model's own (inconsistent, sometimes unavailable)
interval support, we use a **model-agnostic empirical/conformal** wrapper:
:class:`EmpiricalQuantileForecaster` wraps any
:class:`~vyaparsense_ml.forecasting.models.Baseline`, measures that model's
in-sample one-step residuals, and forms quantiles as
``point_forecast + empirical_quantile(residuals, q)`` (clamped to ``>= 0`` —
demand is non-negative). This makes no distributional assumption and works
uniformly for every model on the ladder, including the intermittent ones that
don't expose analytic intervals.

Pure stdlib (uses the point models; no direct heavy imports here).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from vyaparsense_ml.forecasting.models import Baseline


@runtime_checkable
class QuantileForecaster(Protocol):
    """Structural type for a probabilistic forecaster.

    ``quantiles`` are the levels it predicts; ``forecast_quantiles`` maps each to
    an ``h``-step path. ``name`` keys it in backtests/selection.
    """

    @property
    def name(self) -> str: ...

    @property
    def quantiles(self) -> tuple[float, ...]: ...

    def forecast_quantiles(self, y: Sequence[float], h: int) -> dict[float, list[float]]: ...


def _empirical_quantile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolation empirical quantile of an already-sorted list.

    Matches the common "type 7" definition (numpy default) so results line up
    with downstream tooling. ``sorted_values`` must be non-empty.
    """
    n = len(sorted_values)
    if n == 1:
        return sorted_values[0]
    pos = q * (n - 1)
    lo = int(pos)
    frac = pos - lo
    if lo + 1 >= n:
        return sorted_values[-1]
    return sorted_values[lo] + frac * (sorted_values[lo + 1] - sorted_values[lo])


@dataclass(frozen=True)
class EmpiricalQuantileForecaster:
    """Wrap a point model; derive quantiles from its in-sample residuals.

    For each backtest the wrapped model is fit on the history once, its one-step
    residuals ``y[t] - forecast(y[:t])`` are collected over the recent past, and
    each quantile path is ``point + empirical_quantile(residuals, q)`` clamped to
    ``>= 0``. ``residual_window`` caps how many trailing one-step residuals are
    used (keeps it cheap on long series); ``None`` uses all available.
    """

    model: Baseline
    quantiles: tuple[float, ...] = (0.5, 0.9, 0.95)
    residual_window: int | None = 60

    def __post_init__(self) -> None:
        if not self.quantiles:
            raise ValueError("need at least one quantile")
        for q in self.quantiles:
            if not 0.0 < q < 1.0:
                raise ValueError(f"quantile must be in (0, 1), got {q}")
        if self.residual_window is not None and self.residual_window < 1:
            raise ValueError(f"residual_window must be >= 1 or None, got {self.residual_window}")

    @property
    def name(self) -> str:
        return f"empirical_quantile[{self.model.name}]"

    def _one_step_residuals(self, y: Sequence[float]) -> list[float]:
        """Trailing one-step residuals of the wrapped model on history ``y``.

        Cutoffs where the wrapped model cannot yet forecast (it needs more
        warmup than is available, e.g. seasonal-naive on a short prefix) are
        skipped rather than treated as errors.
        """
        n = len(y)
        # Start far enough in that the model has a little history to fit on.
        start = 1
        if self.residual_window is not None:
            start = max(start, n - self.residual_window)
        residuals: list[float] = []
        for t in range(start, n):
            try:
                pred = self.model.forecast(y[:t], 1)[0]
            except ValueError:
                continue  # not enough warmup for this model yet
            residuals.append(float(y[t]) - pred)
        return residuals

    def forecast_quantiles(self, y: Sequence[float], h: int) -> dict[float, list[float]]:
        if h < 1:
            raise ValueError(f"horizon must be >= 1, got {h}")
        if len(y) == 0:
            raise ValueError("cannot forecast from empty history")

        point = self.model.forecast(y, h)
        residuals = self._one_step_residuals(y)
        # Degenerate history (too short for a residual): fall back to the point
        # forecast for every quantile rather than guessing a spread.
        if not residuals:
            return {q: [max(0.0, v) for v in point] for q in self.quantiles}

        residuals.sort()
        out: dict[float, list[float]] = {}
        for q in self.quantiles:
            offset = _empirical_quantile(residuals, q)
            out[q] = [max(0.0, p + offset) for p in point]
        return out
