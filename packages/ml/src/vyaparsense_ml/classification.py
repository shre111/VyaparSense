"""Demand-pattern classification (Syntetos-Boylan).

Classifies a demand series into one of four patterns using two statistics:

* **ADI** (Average Demand Interval) = periods / number of non-zero periods
* **CV2** = squared coefficient of variation of the *non-zero* demand sizes

Quadrant thresholds (Syntetos-Boylan, 2005):

==============  ================  ================
pattern         ADI               CV2
==============  ================  ================
smooth          < 1.32            < 0.49
erratic         < 1.32            >= 0.49
intermittent    >= 1.32           < 0.49
lumpy           >= 1.32           >= 0.49
==============  ================  ================

These drive model routing later (e.g. Croston/SBA/TSB for intermittent/lumpy).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from vyaparsense_ml.cleaning import SeriesKey
from vyaparsense_ml.schema import DemandPattern

ADI_THRESHOLD = 1.32
CV2_THRESHOLD = 0.49


@dataclass(frozen=True)
class DemandStats:
    """Classification result for one series."""

    pattern: DemandPattern
    adi: float
    cv2: float
    n_periods: int
    n_nonzero: int


def _pattern(adi: float, cv2: float) -> DemandPattern:
    if adi < ADI_THRESHOLD:
        return DemandPattern.SMOOTH if cv2 < CV2_THRESHOLD else DemandPattern.ERRATIC
    return DemandPattern.INTERMITTENT if cv2 < CV2_THRESHOLD else DemandPattern.LUMPY


def classify_demand(units: list[int]) -> DemandStats:
    """Classify a single demand series given its per-period units.

    Degenerate series (no periods, or fewer than two non-zero periods so CV2 is
    undefined) are reported as ``lumpy`` with ``cv2=0.0`` — the conservative
    bucket that routes to intermittent-aware models rather than smooth ones.
    """
    n = len(units)
    nonzero = [u for u in units if u > 0]
    if n == 0 or len(nonzero) < 2:
        adi = float(n) / len(nonzero) if nonzero else float("inf")
        return DemandStats(
            pattern=DemandPattern.LUMPY,
            adi=adi,
            cv2=0.0,
            n_periods=n,
            n_nonzero=len(nonzero),
        )

    adi = n / len(nonzero)
    mean = statistics.mean(nonzero)
    cv2 = (statistics.pstdev(nonzero) / mean) ** 2 if mean else 0.0
    return DemandStats(
        pattern=_pattern(adi, cv2),
        adi=adi,
        cv2=cv2,
        n_periods=n,
        n_nonzero=len(nonzero),
    )


def classify_series(
    series: dict[SeriesKey, list[tuple[date, int]]],
) -> dict[SeriesKey, DemandStats]:
    """Classify every series produced by :func:`vyaparsense_ml.cleaning.to_series`."""
    return {key: classify_demand([u for _, u in points]) for key, points in series.items()}
