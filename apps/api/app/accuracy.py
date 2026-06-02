"""Accuracy-over-time service — the "getting smarter" flywheel metric.

Buckets realised forecast-vs-actual pairs by the period in which the forecast
was *made* (ISO year-week of ``created_at``) and computes a pooled WAPE per
period. Plotting these chronologically is the public proof that the model
improves week over week (``CLAUDE.md`` §5, the hero chart).

Pure functions over already-joined ``(created_at, predicted, actual)`` tuples
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
    pairs: list[tuple[dt.datetime, float, float]],
) -> list[AccuracyPoint]:
    """Rolling WAPE by forecast-run week, oldest period first.

    ``pairs`` are ``(forecast_created_at, predicted, actual)``. Pairs are grouped
    by the ISO week of ``created_at`` and each group is scored with pooled WAPE.
    Empty input yields an empty list.
    """
    buckets: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for created_at, predicted, actual in pairs:
        buckets[_iso_week_label(created_at)].append((actual, predicted))

    points: list[AccuracyPoint] = []
    for period in sorted(buckets):
        rows = buckets[period]
        y_true = [a for a, _ in rows]
        y_pred = [p for _, p in rows]
        points.append(AccuracyPoint(period=period, n=len(rows), wape=wape(y_true, y_pred)))
    return points
