"""Feature engineering for the global ML model (Phase 4; ``CLAUDE.md`` §4 rung 4).

Turns clean per-series sales history into a tabular feature frame for a single
global model trained across all SKUs/stores (the M5-winning pattern). One row
per ``(store_id, sku_id, date)`` with:

* **calendar** — day-of-week, weekend flag, month, day-of-year, ISO week, plus
  cyclical sin/cos of day-of-week and month so a tree/linear model can use the
  wrap-around.
* **price / promo** — passed through; both are known at forecast time.
* **lags** — ``units_sold`` shifted by each lag (e.g. 1, 7, 14): demand N days
  ago.
* **rolling** — mean/std of the trailing window, computed leakage-safely
  (``shift(1)`` before ``rolling`` so the window ends at ``t-1`` and never sees
  the current row).

**No leakage:** every lag/rolling feature is built per series and uses only
*past* observations; windows never cross ``(store, sku)`` boundaries. The target
column ``units_sold`` is retained for training; early rows have NaN features
(insufficient history) and are dropped by :func:`build_features` unless
``dropna=False``.

Uses pandas (declared dependency).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from vyaparsense_ml.schema import (
    COL_DATE,
    COL_PRICE,
    COL_PROMO_FLAG,
    COL_SKU_ID,
    COL_STORE_ID,
    COL_UNITS_SOLD,
    SalesRecord,
)

DEFAULT_LAGS: tuple[int, ...] = (1, 7, 14)
DEFAULT_ROLL_WINDOWS: tuple[int, ...] = (7, 28)

_GROUP_KEYS = [COL_STORE_ID, COL_SKU_ID]

CALENDAR_FEATURES: tuple[str, ...] = (
    "dayofweek",
    "is_weekend",
    "month",
    "dayofyear",
    "weekofyear",
    "dow_sin",
    "dow_cos",
    "month_sin",
    "month_cos",
)


def feature_columns(
    lags: Sequence[int] = DEFAULT_LAGS,
    roll_windows: Sequence[int] = DEFAULT_ROLL_WINDOWS,
) -> list[str]:
    """The model-input columns produced by :func:`build_features`, in order.

    Calendar + price/promo + lag + rolling columns (excludes the keys
    ``date``/``store_id``/``sku_id`` and the ``units_sold`` target). Single
    source of truth so models and the feature builder cannot drift apart.
    """
    cols = [*CALENDAR_FEATURES, COL_PRICE, COL_PROMO_FLAG]
    cols += [f"lag_{lag}" for lag in lags]
    for w in roll_windows:
        cols += [f"roll_mean_{w}", f"roll_std_{w}"]
    return cols


def _records_to_frame(records: Sequence[SalesRecord]) -> pd.DataFrame:
    """Build a sorted long DataFrame from validated records."""
    if not records:
        raise ValueError("no records to build features from")
    df = pd.DataFrame(
        {
            COL_DATE: [r.date for r in records],
            COL_STORE_ID: [r.store_id for r in records],
            COL_SKU_ID: [r.sku_id for r in records],
            COL_UNITS_SOLD: [r.units_sold for r in records],
            COL_PRICE: [r.price for r in records],
            COL_PROMO_FLAG: [int(r.promo_flag) for r in records],
        }
    )
    df[COL_DATE] = pd.to_datetime(df[COL_DATE])
    return df.sort_values([*_GROUP_KEYS, COL_DATE]).reset_index(drop=True)


def _add_calendar(df: pd.DataFrame) -> None:
    d = df[COL_DATE].dt
    df["dayofweek"] = d.dayofweek.astype("int64")
    df["is_weekend"] = (d.dayofweek >= 5).astype("int64")
    df["month"] = d.month.astype("int64")
    df["dayofyear"] = d.dayofyear.astype("int64")
    df["weekofyear"] = d.isocalendar().week.astype("int64").to_numpy()
    # cyclical encodings so wrap-around (Sun->Mon, Dec->Jan) is continuous
    df["dow_sin"] = np.sin(2 * np.pi * df["dayofweek"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dayofweek"] / 7)
    df["month_sin"] = np.sin(2 * np.pi * (df["month"] - 1) / 12)
    df["month_cos"] = np.cos(2 * np.pi * (df["month"] - 1) / 12)


def _add_lags_and_rolling(
    df: pd.DataFrame, lags: Sequence[int], roll_windows: Sequence[int]
) -> None:
    grouped = df.groupby(_GROUP_KEYS, sort=False)[COL_UNITS_SOLD]
    for lag in lags:
        df[f"lag_{lag}"] = grouped.shift(lag)
    for w in roll_windows:
        # shift(1) first => window ends at t-1 (no leakage of the current value)
        df[f"roll_mean_{w}"] = grouped.transform(lambda s, w=w: s.shift(1).rolling(w).mean())
        df[f"roll_std_{w}"] = grouped.transform(lambda s, w=w: s.shift(1).rolling(w).std())


def build_features(
    records: Sequence[SalesRecord],
    *,
    lags: Sequence[int] = DEFAULT_LAGS,
    roll_windows: Sequence[int] = DEFAULT_ROLL_WINDOWS,
    dropna: bool = True,
) -> pd.DataFrame:
    """Build the global-model feature frame from clean sales records.

    Args:
        records: validated, cleaned records (see ``cleaning.clean_sales``).
        lags: demand lags to add (days). Must be positive.
        roll_windows: trailing-window sizes for rolling mean/std. Must be positive.
        dropna: drop rows whose lag/rolling features are NaN (insufficient
            history). Keep them with ``dropna=False`` for inference scaffolding.

    Returns:
        A DataFrame sorted by ``(store_id, sku_id, date)`` with calendar,
        price/promo, lag, and rolling features plus the ``units_sold`` target.
    """
    if any(v < 1 for v in lags):
        raise ValueError(f"lags must be positive, got {tuple(lags)}")
    if any(v < 1 for v in roll_windows):
        raise ValueError(f"roll_windows must be positive, got {tuple(roll_windows)}")

    df = _records_to_frame(records)
    _add_calendar(df)
    _add_lags_and_rolling(df, lags, roll_windows)

    if dropna:
        feature_cols = [f"lag_{lag}" for lag in lags]
        feature_cols += [f"roll_mean_{w}" for w in roll_windows]
        feature_cols += [f"roll_std_{w}" for w in roll_windows]
        df = df.dropna(subset=feature_cols).reset_index(drop=True)
    return df
