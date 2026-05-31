"""Tests for demand-pattern classification."""

from __future__ import annotations

from pathlib import Path

from vyaparsense_ml.classification import classify_demand, classify_series
from vyaparsense_ml.cleaning import clean_sales, to_series
from vyaparsense_ml.ingest import read_sales_csv
from vyaparsense_ml.schema import DemandPattern

SAMPLE_CSV = Path(__file__).resolve().parents[3] / "data" / "samples" / "sales_history.csv"


def test_smooth_series() -> None:
    stats = classify_demand([10, 11, 9, 10, 12, 10, 11, 9, 10, 10])
    assert stats.pattern is DemandPattern.SMOOTH
    assert stats.adi < 1.32
    assert stats.cv2 < 0.49


def test_intermittent_series() -> None:
    # frequent zeros, similar non-zero sizes -> high ADI, low CV2
    stats = classify_demand([0, 0, 5, 0, 0, 5, 0, 0, 5, 0, 0, 5])
    assert stats.pattern is DemandPattern.INTERMITTENT


def test_lumpy_series() -> None:
    # sparse AND highly variable sizes
    stats = classify_demand([0, 0, 0, 1, 0, 0, 0, 0, 50, 0, 0, 0])
    assert stats.pattern is DemandPattern.LUMPY


def test_all_zero_is_lumpy_no_crash() -> None:
    stats = classify_demand([0, 0, 0, 0])
    assert stats.pattern is DemandPattern.LUMPY
    assert stats.n_nonzero == 0


def test_single_nonzero_is_lumpy() -> None:
    stats = classify_demand([0, 0, 7, 0])
    assert stats.pattern is DemandPattern.LUMPY
    assert stats.n_nonzero == 1


def test_empty_series() -> None:
    stats = classify_demand([])
    assert stats.pattern is DemandPattern.LUMPY
    assert stats.n_periods == 0


def test_sample_dataset_reproduces_intended_quadrants() -> None:
    """The eight sample SKUs must land in their designed patterns (pooled per SKU)."""
    expected = {
        "SKU-MILK-1L": DemandPattern.SMOOTH,
        "SKU-BREAD-400": DemandPattern.SMOOTH,
        "SKU-RICE-5KG": DemandPattern.ERRATIC,
        "SKU-OIL-1L": DemandPattern.ERRATIC,
        "SKU-SHAMPOO-S": DemandPattern.INTERMITTENT,
        "SKU-BATTERY-AA": DemandPattern.INTERMITTENT,
        "SKU-PRESSURE-CK": DemandPattern.LUMPY,
        "SKU-GIFT-BOX": DemandPattern.LUMPY,
    }
    records = clean_sales(read_sales_csv(SAMPLE_CSV))
    stats = classify_series(to_series(records))

    # pool both stores per SKU by majority of the two store-level classifications
    by_sku: dict[str, list[DemandPattern]] = {}
    for (_, sku), s in stats.items():
        by_sku.setdefault(sku, []).append(s.pattern)

    for sku, exp in expected.items():
        patterns = by_sku[sku]
        assert all(p is exp for p in patterns), f"{sku}: {patterns} != {exp}"
