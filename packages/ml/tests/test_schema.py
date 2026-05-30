"""Tests for the canonical sales-history schema."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from vyaparsense_ml.schema import (
    CANONICAL_COLUMNS,
    DemandPattern,
    SalesRecord,
    SalesValidationError,
    validate_rows,
)

# Repo root: packages/ml/tests/test_schema.py -> parents[3]
SAMPLE_CSV = Path(__file__).resolve().parents[3] / "data" / "samples" / "sales_history.csv"


def _row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "date": "2024-01-01",
        "store_id": "STORE-DEL-01",
        "sku_id": "SKU-MILK-1L",
        "units_sold": 42,
        "price": 28.0,
        "promo_flag": 1,
    }
    base.update(overrides)
    return base


def test_valid_row_parses() -> None:
    rec = SalesRecord.model_validate(_row())
    assert rec.date == date(2024, 1, 1)
    assert rec.units_sold == 42
    assert rec.promo_flag is True


def test_zero_units_is_valid() -> None:
    assert SalesRecord.model_validate(_row(units_sold=0)).units_sold == 0


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1", True), ("true", True), ("YES", True), ("0", False), ("no", False), ("", False)],
)
def test_promo_flag_coercion(value: str, expected: bool) -> None:
    assert SalesRecord.model_validate(_row(promo_flag=value)).promo_flag is expected


def test_ids_are_stripped() -> None:
    rec = SalesRecord.model_validate(_row(store_id="  STORE-DEL-01  "))
    assert rec.store_id == "STORE-DEL-01"


@pytest.mark.parametrize(
    "bad",
    [
        _row(units_sold=-1),
        _row(price=-5.0),
        _row(sku_id=""),
        _row(store_id="   "),
        _row(date="not-a-date"),
        _row(promo_flag="maybe"),
    ],
)
def test_invalid_rows_raise(bad: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SalesRecord.model_validate(bad)


def test_extra_columns_forbidden() -> None:
    with pytest.raises(ValidationError):
        SalesRecord.model_validate(_row(unexpected="x"))


def test_record_is_frozen() -> None:
    rec = SalesRecord.model_validate(_row())
    with pytest.raises(ValidationError):
        rec.units_sold = 99


def test_validate_rows_aggregates_errors() -> None:
    rows = [_row(), _row(units_sold=-1), _row(sku_id="")]
    with pytest.raises(SalesValidationError) as exc:
        validate_rows(rows)
    assert set(exc.value.errors) == {1, 2}


def test_validate_rows_returns_records() -> None:
    recs = validate_rows([_row(), _row(units_sold=0)])
    assert len(recs) == 2
    assert all(isinstance(r, SalesRecord) for r in recs)


def test_demand_pattern_values() -> None:
    assert {p.value for p in DemandPattern} == {
        "smooth",
        "erratic",
        "intermittent",
        "lumpy",
    }


def test_sample_csv_header_matches_canonical_columns() -> None:
    assert SAMPLE_CSV.exists(), f"sample dataset missing at {SAMPLE_CSV}"
    with SAMPLE_CSV.open() as f:
        header = next(csv.reader(f))
    assert tuple(header) == CANONICAL_COLUMNS


def test_sample_csv_first_rows_validate() -> None:
    with SAMPLE_CSV.open() as f:
        reader = csv.DictReader(f)
        rows = [next(reader) for _ in range(100)]
    recs = validate_rows(rows)
    assert len(recs) == 100
