"""Classical time-series models (model ladder rung 2; ``CLAUDE.md`` §4).

Thin adapters over Nixtla ``statsforecast`` (ADR-004) that conform to the
:class:`~vyaparsense_ml.forecasting.models.Baseline` protocol, so the existing
backtest/selection harness uses them unchanged:

* :class:`AutoETS` — automatic error/trend/seasonal exponential smoothing.
* :class:`AutoARIMA` — automatic (seasonal) ARIMA order selection.

Each call fits on the supplied history and returns an ``h``-step point forecast.
statsforecast's optimizer can return NaN/inf (or negative) values on hard or
degenerate series; we clamp negatives to zero (demand can't be negative) and
fall back to a seasonal-naive forecast if the result isn't finite, so a single
bad series never poisons a pooled backtest. ``numpy`` is the only heavy import.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from statsforecast.models import AutoARIMA as _SFAutoARIMA
from statsforecast.models import AutoETS as _SFAutoETS

from vyaparsense_ml.forecasting.models import SeasonalNaive


def _validate(y: Sequence[float], h: int, season_length: int) -> None:
    if h < 1:
        raise ValueError(f"horizon must be >= 1, got {h}")
    if season_length < 1:
        raise ValueError(f"season_length must be >= 1, got {season_length}")
    if len(y) < 2 * season_length:
        raise ValueError(
            f"classical models need at least 2*season_length={2 * season_length} "
            f"observations, got {len(y)}"
        )


def _finite_nonneg(
    values: np.ndarray, y: Sequence[float], h: int, season_length: int
) -> list[float]:
    """Clamp negatives to zero; if any value is non-finite, fall back to seasonal-naive."""
    if not np.all(np.isfinite(values)):
        return SeasonalNaive(season_length=season_length).forecast(y, h)
    return [max(0.0, float(v)) for v in values]


@dataclass(frozen=True)
class AutoETS:
    """Automatic exponential smoothing (ETS) via statsforecast."""

    season_length: int = 7

    @property
    def name(self) -> str:
        return f"auto_ets_{self.season_length}"

    def forecast(self, y: Sequence[float], h: int) -> list[float]:
        _validate(y, h, self.season_length)
        arr = np.asarray(y, dtype=np.float64)
        model = _SFAutoETS(season_length=self.season_length)
        out = model.forecast(y=arr, h=h)["mean"]
        return _finite_nonneg(np.asarray(out, dtype=np.float64), y, h, self.season_length)


@dataclass(frozen=True)
class AutoARIMA:
    """Automatic (seasonal) ARIMA via statsforecast."""

    season_length: int = 7

    @property
    def name(self) -> str:
        return f"auto_arima_{self.season_length}"

    def forecast(self, y: Sequence[float], h: int) -> list[float]:
        _validate(y, h, self.season_length)
        arr = np.asarray(y, dtype=np.float64)
        model = _SFAutoARIMA(season_length=self.season_length)
        out = model.forecast(y=arr, h=h)["mean"]
        return _finite_nonneg(np.asarray(out, dtype=np.float64), y, h, self.season_length)
