"""CSV ingest for sales history.

Thin IO layer on top of :mod:`vyaparsense_ml.schema`. Reads a CSV file, checks
file/header-level problems eagerly with clear messages, then delegates row
validation to :func:`vyaparsense_ml.schema.validate_rows`.

Pure stdlib (``csv``) — no pandas dependency at this stage.
"""

from __future__ import annotations

import csv
from pathlib import Path

from vyaparsense_ml.schema import CANONICAL_COLUMNS, SalesRecord, validate_rows


class IngestError(Exception):
    """Raised for file- or header-level problems before row validation."""


def _normalize_header(field: str) -> str:
    # Strip BOM + surrounding whitespace that spreadsheets often introduce.
    return field.lstrip("﻿").strip()


def read_sales_csv(path: str | Path) -> list[SalesRecord]:
    """Read and validate a sales-history CSV into ``SalesRecord``s.

    Raises:
        IngestError: file missing, empty, or header lacks canonical columns.
        SalesValidationError: one or more data rows fail validation.
    """
    p = Path(path)
    if not p.exists():
        raise IngestError(f"file not found: {p}")
    if p.is_dir():
        raise IngestError(f"expected a file, got a directory: {p}")

    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            raw_header = next(reader)
        except StopIteration:
            raise IngestError(f"file is empty: {p}") from None

        header = [_normalize_header(h) for h in raw_header]
        expected = set(CANONICAL_COLUMNS)
        actual = set(header)
        missing = expected - actual
        extra = actual - expected
        if missing:
            raise IngestError(f"missing required column(s): {sorted(missing)}; got header {header}")
        if extra:
            raise IngestError(f"unexpected column(s): {sorted(extra)}; got header {header}")

        rows = [dict(zip(header, values, strict=False)) for values in reader]

    return validate_rows(rows)
