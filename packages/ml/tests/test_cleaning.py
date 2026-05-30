"""Tests for data cleaning + calendar gap-fill."""

from __future__ import annotations

from datetime import date

from vyaparsense_ml.cleaning import clean_sales, to_series
from vyaparsense_ml.schema import SalesRecord


def _rec(
    d: str,
    units: int,
    *,
    store: str = "S1",
    sku: str = "K1",
    price: float = 10.0,
    promo: bool = False,
) -> SalesRecord:
    return SalesRecord(
        date=date.fromisoformat(d),
        store_id=store,
        sku_id=sku,
        units_sold=units,
        price=price,
        promo_flag=promo,
    )


def test_calendar_gaps_filled_with_zeros() -> None:
    recs = clean_sales([_rec("2024-01-01", 5), _rec("2024-01-04", 3)])
    assert [r.date.day for r in recs] == [1, 2, 3, 4]
    assert [r.units_sold for r in recs] == [5, 0, 0, 3]
    assert all(r.units_sold == 0 and not r.promo_flag for r in recs[1:3])


def test_price_carried_forward_into_gaps() -> None:
    recs = clean_sales([_rec("2024-01-01", 5, price=12.5), _rec("2024-01-03", 2, price=99.0)])
    assert recs[1].units_sold == 0
    assert recs[1].price == 12.5  # carried from last known, not the future price


def test_dedupe_sums_units_and_ors_promo() -> None:
    recs = clean_sales(
        [_rec("2024-01-01", 2, promo=False), _rec("2024-01-01", 3, promo=True)],
        fill_calendar_gaps=False,
    )
    assert len(recs) == 1
    assert recs[0].units_sold == 5
    assert recs[0].promo_flag is True


def test_multiple_series_kept_separate_and_sorted() -> None:
    recs = clean_sales(
        [
            _rec("2024-01-02", 1, store="S2", sku="K1"),
            _rec("2024-01-01", 1, store="S1", sku="K1"),
        ],
        fill_calendar_gaps=False,
    )
    keys = [(r.store_id, r.sku_id) for r in recs]
    assert keys == [("S1", "K1"), ("S2", "K1")]


def test_no_gap_fill_preserves_only_present_days() -> None:
    recs = clean_sales([_rec("2024-01-01", 5), _rec("2024-01-04", 3)], fill_calendar_gaps=False)
    assert [r.date.day for r in recs] == [1, 4]


def test_idempotent() -> None:
    once = clean_sales([_rec("2024-01-01", 5), _rec("2024-01-04", 3)])
    twice = clean_sales(once)
    assert once == twice


def test_to_series_projects_ordered_pairs() -> None:
    recs = clean_sales([_rec("2024-01-01", 5), _rec("2024-01-03", 2)])
    series = to_series(recs)
    assert series[("S1", "K1")] == [
        (date(2024, 1, 1), 5),
        (date(2024, 1, 2), 0),
        (date(2024, 1, 3), 2),
    ]


def test_empty_input() -> None:
    assert clean_sales([]) == []
    assert to_series([]) == {}
