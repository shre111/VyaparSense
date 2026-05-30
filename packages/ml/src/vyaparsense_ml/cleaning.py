"""Data cleaning for sales history.

Turns raw validated :class:`~vyaparsense_ml.schema.SalesRecord`s into clean,
gap-free per-series daily history that downstream classification and
forecasting can rely on:

* group by ``(store_id, sku_id)`` and sort by date
* dedupe collisions on the same ``(store, sku, date)`` (sum units, carry price,
  OR the promo flag)
* fill calendar gaps within each series' span with explicit zero-demand days
  (a missing day is *no demand*, not missing data)

Pure functions, stdlib only.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from vyaparsense_ml.schema import SalesRecord

SeriesKey = tuple[str, str]


def _group(records: list[SalesRecord]) -> dict[SeriesKey, list[SalesRecord]]:
    groups: dict[SeriesKey, list[SalesRecord]] = defaultdict(list)
    for r in records:
        groups[(r.store_id, r.sku_id)].append(r)
    return groups


def _dedupe_day(same_day: list[SalesRecord]) -> SalesRecord:
    """Collapse multiple records for one (store, sku, date) into one.

    Units sum; promo is OR-ed; price uses the last record's value.
    """
    total_units = sum(r.units_sold for r in same_day)
    promo = any(r.promo_flag for r in same_day)
    price = same_day[-1].price
    first = same_day[0]
    return SalesRecord(
        date=first.date,
        store_id=first.store_id,
        sku_id=first.sku_id,
        units_sold=total_units,
        price=price,
        promo_flag=promo,
    )


def clean_sales(
    records: list[SalesRecord], *, fill_calendar_gaps: bool = True
) -> list[SalesRecord]:
    """Clean raw records into ordered, de-duplicated, gap-free daily series.

    Returns records sorted by (store_id, sku_id, date). Idempotent.
    """
    groups = _group(records)
    out: list[SalesRecord] = []

    for key in sorted(groups):
        store_id, sku_id = key
        by_date: dict[date, list[SalesRecord]] = defaultdict(list)
        for r in groups[key]:
            by_date[r.date].append(r)

        deduped = {d: _dedupe_day(rs) for d, rs in by_date.items()}
        days = sorted(deduped)

        if fill_calendar_gaps and days:
            last_price = deduped[days[0]].price
            cur = days[0]
            end = days[-1]
            while cur <= end:
                if cur in deduped:
                    rec = deduped[cur]
                    last_price = rec.price
                    out.append(rec)
                else:
                    out.append(
                        SalesRecord(
                            date=cur,
                            store_id=store_id,
                            sku_id=sku_id,
                            units_sold=0,
                            price=last_price,
                            promo_flag=False,
                        )
                    )
                cur += timedelta(days=1)
        else:
            out.extend(deduped[d] for d in days)

    return out


def to_series(records: list[SalesRecord]) -> dict[SeriesKey, list[tuple[date, int]]]:
    """Project records into per-series ``(date, units)`` lists, date-ordered."""
    series: dict[SeriesKey, list[tuple[date, int]]] = defaultdict(list)
    for r in records:
        series[(r.store_id, r.sku_id)].append((r.date, r.units_sold))
    for key in series:
        series[key].sort(key=lambda t: t[0])
    return dict(series)
