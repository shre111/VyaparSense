"""Tests for CSV ingest."""

from __future__ import annotations

from pathlib import Path

import pytest

from vyaparsense_ml.ingest import IngestError, read_sales_csv
from vyaparsense_ml.schema import SalesValidationError

SAMPLE_CSV = Path(__file__).resolve().parents[3] / "data" / "samples" / "sales_history.csv"

_HEADER = "date,store_id,sku_id,units_sold,price,promo_flag\n"
_GOOD_ROW = "2024-01-01,STORE-DEL-01,SKU-MILK-1L,42,28.00,1\n"


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "sales.csv"
    p.write_text(content, encoding="utf-8")
    return p


def test_reads_sample_dataset_fully() -> None:
    recs = read_sales_csv(SAMPLE_CSV)
    assert len(recs) == 11680  # 2 stores x 8 SKUs x 730 days


def test_reads_minimal_valid_file(tmp_path: Path) -> None:
    recs = read_sales_csv(_write(tmp_path, _HEADER + _GOOD_ROW))
    assert len(recs) == 1
    assert recs[0].sku_id == "SKU-MILK-1L"


def test_missing_file_raises() -> None:
    with pytest.raises(IngestError, match="file not found"):
        read_sales_csv("/no/such/file.csv")


def test_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(IngestError, match="directory"):
        read_sales_csv(tmp_path)


def test_empty_file_raises(tmp_path: Path) -> None:
    with pytest.raises(IngestError, match="empty"):
        read_sales_csv(_write(tmp_path, ""))


def test_missing_column_raises(tmp_path: Path) -> None:
    bad = "date,store_id,sku_id,units_sold,price\n2024-01-01,S,K,1,1.0\n"
    with pytest.raises(IngestError, match="missing required column"):
        read_sales_csv(_write(tmp_path, bad))


def test_extra_column_raises(tmp_path: Path) -> None:
    bad = _HEADER.rstrip("\n") + ",extra\n" + _GOOD_ROW.rstrip("\n") + ",x\n"
    with pytest.raises(IngestError, match="unexpected column"):
        read_sales_csv(_write(tmp_path, bad))


def test_bom_and_whitespace_header_tolerated(tmp_path: Path) -> None:
    content = "﻿ date , store_id ,sku_id,units_sold,price,promo_flag\n" + _GOOD_ROW
    recs = read_sales_csv(_write(tmp_path, content))
    assert len(recs) == 1


def test_row_errors_surface_with_indices(tmp_path: Path) -> None:
    content = _HEADER + _GOOD_ROW + "2024-01-02,STORE-DEL-01,SKU-MILK-1L,-5,28.00,0\n"
    with pytest.raises(SalesValidationError) as exc:
        read_sales_csv(_write(tmp_path, content))
    assert set(exc.value.errors) == {1}
