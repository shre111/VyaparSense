"""Transfer-learning cold-start for new/short series (``CLAUDE.md`` §4 rung 6).

A brand-new store or SKU has too little history to forecast on its own — the
per-series models can't fit a backtest and even the global model's lags are
mostly empty. Cold-start borrows the demand *shape* (a normalized weekly profile)
from a pool of similar "donor" series that do have history, and scales it to the
new series' own level. This is the data moat: every existing series makes new
ones forecastable.

* **level** — the target's mean demand from its little history (or the donors'
  mean if the target is empty).
* **shape** — the donors' pooled weekly (day-of-week) profile, normalized to
  mean 1, so it transfers across series at different scales.

``forecast[d] = level * profile[d.weekday()]``, clamped to ``>= 0``. Donor
selection prefers other SKUs in the same store, then the nearest by demand level.
numpy only.
"""

from __future__ import annotations

import datetime as dt
import math
from collections.abc import Iterable, Mapping, Sequence

import numpy as np
import numpy.typing as npt

from vyaparsense_ml.cleaning import SeriesKey

FloatArray = npt.NDArray[np.float64]
History = Sequence[tuple[dt.date, int]]

_WEEK = 7


def _level(history: History) -> float:
    """Mean demand over a series' observed days (0 if empty)."""
    units = [u for _, u in history]
    return float(np.mean(units)) if units else 0.0


def weekly_profile(history: History) -> FloatArray | None:
    """Average demand per weekday, normalized to mean 1 — ``None`` if all-zero/empty.

    Captures the shape of the week (e.g. weekend spikes) independent of the
    overall level, so it can be transferred to a series at a different scale.
    Weekdays with no observations are left at 0.
    """
    sums = np.zeros(_WEEK, dtype=np.float64)
    counts = np.zeros(_WEEK, dtype=np.float64)
    for d, u in history:
        sums[d.weekday()] += u
        counts[d.weekday()] += 1
    observed = counts > 0
    if not observed.any():
        return None
    avg = np.divide(sums, counts, out=np.zeros(_WEEK, dtype=np.float64), where=observed)
    overall = float(avg[observed].mean())
    if overall <= 0:
        return None
    return np.asarray(avg / overall, dtype=np.float64)


def _donor_level(donors: Sequence[History]) -> float:
    """Mean demand level across the donors (0 if none have demand)."""
    levels = [lvl for lvl in (_level(h) for h in donors) if lvl > 0]
    return float(np.mean(levels)) if levels else 0.0


def pooled_weekly_profile(donors: Iterable[History]) -> FloatArray:
    """Pool donors' weekly profiles into one robust shape (flat if none usable)."""
    profiles = [p for p in (weekly_profile(h) for h in donors) if p is not None]
    if not profiles:
        return np.ones(_WEEK, dtype=np.float64)
    return np.asarray(np.mean(profiles, axis=0), dtype=np.float64)


def select_donors(
    target: SeriesKey,
    series: Mapping[SeriesKey, History],
    *,
    k: int = 5,
    min_history: int = 14,
) -> list[History]:
    """Pick up to ``k`` donor series for cold-starting ``target``.

    Prefers other SKUs in the same store; otherwise falls back to all series,
    ranked by closeness in (log) demand level to the target. Only series with at
    least ``min_history`` observed days and non-zero demand qualify as donors.
    """
    target_level = _level(series.get(target, []))
    candidates = [
        (key, h)
        for key, h in series.items()
        if key != target and len(h) >= min_history and _level(h) > 0
    ]
    same_store = [(key, h) for key, h in candidates if key[0] == target[0]]
    pool = same_store if same_store else candidates
    if target_level > 0:
        pool = sorted(pool, key=lambda kh: abs(math.log(_level(kh[1])) - math.log(target_level)))
    return [h for _key, h in pool[:k]]


def cold_start_forecast(
    target_history: History,
    donors: Iterable[History],
    *,
    horizon: int,
    start_date: dt.date | None = None,
) -> list[float]:
    """Forecast a cold series: donors' borrowed weekly shape times the target's level.

    Dates run from the day after the target's last observation, or from
    ``start_date`` when the target has no history at all. The level is the
    target's own mean demand, falling back to the donors' mean level when the
    target is empty (or flat-zero).

    Raises:
        ValueError: invalid ``horizon``, or no history *and* no ``start_date``.
    """
    if horizon < 1:
        raise ValueError(f"horizon must be >= 1, got {horizon}")
    donor_list = list(donors)

    if target_history:
        last_date = max(d for d, _ in target_history)
        level = _level(target_history)
    elif start_date is not None:
        last_date = start_date - dt.timedelta(days=1)
        level = 0.0
    else:
        raise ValueError("need target history or a start_date to date the forecast")

    if level <= 0:  # empty/flat-zero target -> borrow the donors' level outright
        level = _donor_level(donor_list)
    profile = pooled_weekly_profile(donor_list)
    return [
        max(0.0, level * float(profile[(last_date + dt.timedelta(days=h)).weekday()]))
        for h in range(1, horizon + 1)
    ]
