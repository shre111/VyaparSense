"""Baseline ("dumb") forecasting models — the permanent honest benchmark.

Three deliberately simple models (``CLAUDE.md`` section 4, rung 1). They are the
floor every fancier model must clear on a fixed backtest before it ships, and
they are never deleted — a naive model winning for a given SKU is a valid,
expected outcome.

* :class:`Naive` — repeat the last observed value.
* :class:`MovingAverage` — repeat the mean of the last ``window`` observations.
* :class:`SeasonalNaive` — repeat the last full season.

A model maps an in-sample history and a horizon to an ``h``-step-ahead point
forecast. Models hold no learned state beyond their hyper-parameters, so one
instance can forecast any series. Pure stdlib.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class Baseline(Protocol):
    """Structural type for a point-forecast model."""

    @property
    def name(self) -> str:
        """Stable identifier used as the key in backtests and model selection."""
        ...

    def forecast(self, y: Sequence[float], h: int) -> list[float]:
        """Forecast the next ``h`` values given history ``y``."""
        ...


def _validate(y: Sequence[float], h: int) -> None:
    if h < 1:
        raise ValueError(f"horizon must be >= 1, got {h}")
    if len(y) == 0:
        raise ValueError("cannot forecast from empty history")


@dataclass(frozen=True)
class Naive:
    """Forecast every future period as the last observed value."""

    @property
    def name(self) -> str:
        return "naive"

    def forecast(self, y: Sequence[float], h: int) -> list[float]:
        _validate(y, h)
        return [float(y[-1])] * h


@dataclass(frozen=True)
class MovingAverage:
    """Forecast every future period as the mean of the last ``window`` values.

    If the history is shorter than ``window`` the whole history is averaged.
    """

    window: int = 7

    def __post_init__(self) -> None:
        if self.window < 1:
            raise ValueError(f"window must be >= 1, got {self.window}")

    @property
    def name(self) -> str:
        return f"moving_average_{self.window}"

    def forecast(self, y: Sequence[float], h: int) -> list[float]:
        _validate(y, h)
        k = min(self.window, len(y))
        avg = float(sum(y[-k:])) / k
        return [avg] * h


@dataclass(frozen=True)
class SeasonalNaive:
    """Forecast by repeating the last full season of length ``season_length``.

    Requires at least ``season_length`` observations; raises otherwise so the
    backtest harness is forced to use a large enough training window.
    """

    season_length: int = 7

    def __post_init__(self) -> None:
        if self.season_length < 1:
            raise ValueError(f"season_length must be >= 1, got {self.season_length}")

    @property
    def name(self) -> str:
        return f"seasonal_naive_{self.season_length}"

    def forecast(self, y: Sequence[float], h: int) -> list[float]:
        _validate(y, h)
        m = self.season_length
        if len(y) < m:
            raise ValueError(
                f"seasonal_naive needs at least season_length={m} observations, got {len(y)}"
            )
        last_season = [float(v) for v in y[-m:]]
        return [last_season[i % m] for i in range(h)]
