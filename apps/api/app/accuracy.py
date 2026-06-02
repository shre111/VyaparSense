"""Accuracy-over-time service — the "getting smarter" flywheel metric.

Buckets realised forecast-vs-actual pairs by the ISO year-week of the period
being predicted (the forecast's ``horizon_date``) and computes a pooled WAPE per
week. Plotting these chronologically is the public proof that the model improves
week over week (``CLAUDE.md`` §5, the hero chart).

Pure functions over already-joined ``(horizon_date, predicted, actual)`` tuples
(see ``repository.forecast_actual_pairs``); WAPE comes from the ML library so
the API and library never disagree on the metric definition.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from dataclasses import dataclass

from vyaparsense_ml.forecasting.metrics import wape


@dataclass(frozen=True)
class AccuracyPoint:
    """Pooled accuracy for one period: ``n`` forecast points and their WAPE."""

    period: str  # ISO year-week label, e.g. "2024-W05"
    n: int
    wape: float


def _iso_week_label(when: dt.datetime | dt.date) -> str:
    iso = when.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def accuracy_over_time(
    pairs: list[tuple[dt.date, float, float]],
) -> list[AccuracyPoint]:
    """Rolling WAPE by predicted-period week, oldest period first.

    ``pairs`` are ``(horizon_date, predicted, actual)``. Pairs are grouped by the
    ISO week of ``horizon_date`` and each group is scored with pooled WAPE.
    Empty input yields an empty list.
    """
    buckets: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for horizon_date, predicted, actual in pairs:
        buckets[_iso_week_label(horizon_date)].append((actual, predicted))

    points: list[AccuracyPoint] = []
    for period in sorted(buckets):
        rows = buckets[period]
        y_true = [a for a, _ in rows]
        y_pred = [p for _, p in rows]
        points.append(AccuracyPoint(period=period, n=len(rows), wape=wape(y_true, y_pred)))
    return points
