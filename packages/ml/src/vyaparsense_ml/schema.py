"""Canonical sales-history schema for VyaparSense.

This module is the single source of truth for the shape of sales data flowing
through the system. It is pure (no IO) — CSV/DB ingest builds on top of it.

Canonical columns (order matters for CSV output):
    date, store_id, sku_id, units_sold, price, promo_flag
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

# --- Canonical column names (single source of truth) -------------------------

COL_DATE = "date"
COL_STORE_ID = "store_id"
COL_SKU_ID = "sku_id"
COL_UNITS_SOLD = "units_sold"
COL_PRICE = "price"
COL_PROMO_FLAG = "promo_flag"

#: Canonical column order for sales-history tables/CSVs.
CANONICAL_COLUMNS: tuple[str, ...] = (
    COL_DATE,
    COL_STORE_ID,
    COL_SKU_ID,
    COL_UNITS_SOLD,
    COL_PRICE,
    COL_PROMO_FLAG,
)

# Truthy/falsy tokens accepted for promo_flag when it arrives as a string.
_TRUE_TOKENS = frozenset({"1", "true", "t", "yes", "y"})
_FALSE_TOKENS = frozenset({"0", "false", "f", "no", "n", ""})


class DemandPattern(StrEnum):
    """Syntetos-Boylan demand classification (by ADI and CV^2).

    Thresholds: ADI = 1.32 (avg inter-demand interval), CV^2 = 0.49.
    """

    SMOOTH = "smooth"  # ADI < 1.32 and CV^2 < 0.49
    ERRATIC = "erratic"  # ADI < 1.32 and CV^2 >= 0.49
    INTERMITTENT = "intermittent"  # ADI >= 1.32 and CV^2 < 0.49
    LUMPY = "lumpy"  # ADI >= 1.32 and CV^2 >= 0.49


class SalesRecord(BaseModel):
    """One row of sales history: units of a SKU sold at a store on a date.

    A ``units_sold`` of 0 is meaningful (no demand or stockout), not missing.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    date: date
    store_id: str = Field(min_length=1)
    sku_id: str = Field(min_length=1)
    units_sold: int = Field(ge=0)
    price: float = Field(ge=0.0)
    promo_flag: bool = False

    @field_validator("store_id", "sku_id", mode="before")
    @classmethod
    def _strip_ids(cls, v: Any) -> Any:
        return v.strip() if isinstance(v, str) else v

    @field_validator("promo_flag", mode="before")
    @classmethod
    def _coerce_promo_flag(cls, v: Any) -> Any:
        if isinstance(v, str):
            token = v.strip().lower()
            if token in _TRUE_TOKENS:
                return True
            if token in _FALSE_TOKENS:
                return False
            raise ValueError(f"invalid promo_flag value: {v!r}")
        return v


class SalesValidationError(Exception):
    """Raised when one or more rows fail validation.

    ``errors`` maps the offending row index (0-based) to a message.
    """

    def __init__(self, errors: dict[int, str]) -> None:
        self.errors = errors
        preview = "; ".join(f"row {i}: {msg}" for i, msg in list(errors.items())[:5])
        suffix = "" if len(errors) <= 5 else f" (+{len(errors) - 5} more)"
        super().__init__(f"{len(errors)} invalid row(s): {preview}{suffix}")


def validate_rows(rows: list[dict[str, Any]]) -> list[SalesRecord]:
    """Validate an iterable of raw row dicts into typed ``SalesRecord``s.

    Collects every failing row before raising so callers see all problems at
    once, with row indices, rather than failing on the first bad row.
    """
    records: list[SalesRecord] = []
    errors: dict[int, str] = {}
    for i, row in enumerate(rows):
        try:
            records.append(SalesRecord.model_validate(row))
        except ValidationError as exc:
            errors[i] = str(exc).replace("\n", " ")
    if errors:
        raise SalesValidationError(errors)
    return records
