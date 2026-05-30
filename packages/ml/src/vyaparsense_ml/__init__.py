"""VyaparSense forecasting & replenishment library.

Subpackages (added across Phase 1-8):
    forecasting/    models, backtesting, metrics
    replenishment/  reorder point, safety stock, EOQ, service levels
    pipelines/      ingest -> clean -> classify -> feature -> forecast -> store
"""

from __future__ import annotations

from vyaparsense_ml.cleaning import clean_sales, to_series
from vyaparsense_ml.ingest import IngestError, read_sales_csv
from vyaparsense_ml.schema import (
    CANONICAL_COLUMNS,
    DemandPattern,
    SalesRecord,
    SalesValidationError,
    validate_rows,
)

__version__ = "0.1.0"

__all__ = [
    "CANONICAL_COLUMNS",
    "DemandPattern",
    "IngestError",
    "SalesRecord",
    "SalesValidationError",
    "__version__",
    "clean_sales",
    "read_sales_csv",
    "to_series",
    "validate_rows",
]
