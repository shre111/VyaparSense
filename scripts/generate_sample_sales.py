"""Generate a deterministic synthetic sales-history dataset for VyaparSense.

Pure standard library (no numpy/pandas) so it runs without the ML env installed.
Output covers all four demand patterns used in intermittent-demand literature
(classified by ADI = avg inter-demand interval, and CV2 = squared coeff. of
variation of non-zero demand sizes):

    smooth        ADI < 1.32, CV2 < 0.49   -> fast-moving staples
    erratic       ADI < 1.32, CV2 >= 0.49  -> frequent but variable sizes
    intermittent  ADI >= 1.32, CV2 < 0.49  -> slow movers, steady size
    lumpy         ADI >= 1.32, CV2 >= 0.49 -> sparse and variable (hardest)

Canonical columns: date, store_id, sku_id, units_sold, price, promo_flag

Usage:
    python packages/ml/scripts/generate_sample_sales.py \
        --out data/samples/sales_history.csv --start 2024-01-01 --days 730 --seed 42
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta

# --- Indian festival dates (approx) that lift FMCG/retail demand, 2024-2026 ---
FESTIVAL_DATES = {
    # Diwali windows + a few major ones; spikes applied +/- a couple days.
    date(2024, 3, 25),   # Holi
    date(2024, 8, 19),   # Raksha Bandhan
    date(2024, 10, 31),  # Diwali 2024
    date(2024, 11, 1),
    date(2025, 3, 14),   # Holi 2025
    date(2025, 8, 9),    # Raksha Bandhan 2025
    date(2025, 10, 20),  # Diwali 2025
    date(2025, 10, 21),
    date(2026, 3, 4),    # Holi 2026
}


def _festival_multiplier(day: date) -> float:
    """Return a demand multiplier near festivals (peak on the day, taper +/-3d)."""
    best = 1.0
    for f in FESTIVAL_DATES:
        delta = abs((day - f).days)
        if delta <= 3:
            best = max(best, 1.0 + (1.6 * (1.0 - delta / 4.0)))
    return best


def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth's algorithm — Poisson draw with stdlib only."""
    if lam <= 0:
        return 0
    if lam > 30:  # normal approximation for large lambda (cheaper, stable)
        return max(0, round(rng.gauss(lam, math.sqrt(lam))))
    el = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= el:
            return k - 1


@dataclass(frozen=True)
class SkuSpec:
    sku_id: str
    pattern: str          # smooth | erratic | intermittent | lumpy
    base_daily: float     # baseline expected units on a demand day
    price: float
    p_demand: float       # probability a given day has any demand
    size_cv: float        # variability of non-zero demand size
    weekly_amp: float     # weekend/weekday seasonality amplitude
    annual_amp: float     # annual seasonality amplitude
    trend_per_year: float # multiplicative trend over a year (e.g. 0.15 = +15%/yr)
    promo_prob: float     # chance of a promo on any day
    promo_lift: float     # demand multiplier when on promo


# A spread of SKUs across two stores' worth of catalog, all four patterns.
SKU_SPECS: list[SkuSpec] = [
    # smooth — staples
    SkuSpec("SKU-MILK-1L",   "smooth",       42.0, 28.0, 0.99, 0.20, 0.10, 0.15,  0.08, 0.04, 1.25),
    SkuSpec("SKU-BREAD-400", "smooth",       30.0, 35.0, 0.97, 0.25, 0.18, 0.12,  0.05, 0.05, 1.30),
    # erratic — frequent but variable sizes
    SkuSpec("SKU-RICE-5KG",  "erratic",      12.0, 320.0, 0.90, 0.75, 0.15, 0.20, 0.10, 0.08, 1.50),
    SkuSpec("SKU-OIL-1L",    "erratic",       9.0, 160.0, 0.85, 0.85, 0.12, 0.25, 0.06, 0.10, 1.60),
    # intermittent — slow but steady when sold
    SkuSpec("SKU-SHAMPOO-S", "intermittent",  4.0, 3.0, 0.45, 0.30, 0.08, 0.15,  0.04, 0.06, 1.40),
    SkuSpec("SKU-BATTERY-AA", "intermittent", 3.0, 90.0, 0.35, 0.35, 0.05, 0.10, 0.02, 0.05, 1.35),
    # lumpy — sparse AND variable (the hard case)
    SkuSpec("SKU-PRESSURE-CK", "lumpy",       2.0, 1850.0, 0.12, 1.10, 0.05, 0.30, 0.03, 0.12, 1.80),
    SkuSpec("SKU-GIFT-BOX",   "lumpy",        3.0, 450.0, 0.10, 1.30, 0.05, 0.60, 0.05, 0.15, 2.20),
]

STORES = ["STORE-DEL-01", "STORE-BLR-02"]
# Per-store demand scaling so stores differ but share structure (helps later
# transfer-learning / hierarchical work look realistic).
STORE_SCALE = {"STORE-DEL-01": 1.0, "STORE-BLR-02": 0.7}


def _weekly_factor(day: date, amp: float) -> float:
    # Saturday/Sunday lift for retail.
    wd = day.weekday()  # Mon=0..Sun=6
    weekend = 1.0 if wd >= 5 else 0.0
    return 1.0 + amp * (weekend - 0.25)


def _annual_factor(day: date, amp: float) -> float:
    doy = day.timetuple().tm_yday
    return 1.0 + amp * math.sin(2.0 * math.pi * doy / 365.0)


def generate(start: date, days: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    rows: list[dict] = []
    for store in STORES:
        scale = STORE_SCALE[store]
        for spec in SKU_SPECS:
            # Independent stockout windows per (store, sku): a few zero-demand runs.
            stockout_days: set[int] = set()
            n_outages = rng.randint(0, 3)
            for _ in range(n_outages):
                start_idx = rng.randint(0, max(0, days - 1))
                length = rng.randint(2, 7)
                stockout_days.update(range(start_idx, min(days, start_idx + length)))

            for i in range(days):
                day = start + timedelta(days=i)
                if i in stockout_days:
                    units = 0
                    promo = 0
                else:
                    promo = 1 if rng.random() < spec.promo_prob else 0
                    has_demand = rng.random() < spec.p_demand
                    if not has_demand:
                        units = 0
                    else:
                        trend = 1.0 + spec.trend_per_year * (i / 365.0)
                        lam = (
                            spec.base_daily
                            * scale
                            * trend
                            * _weekly_factor(day, spec.weekly_amp)
                            * _annual_factor(day, spec.annual_amp)
                            * _festival_multiplier(day)
                            * (spec.promo_lift if promo else 1.0)
                        )
                        # size variability via lognormal-ish multiplier
                        noise = math.exp(rng.gauss(0.0, spec.size_cv))
                        units = _poisson(rng, max(0.0, lam * noise))
                rows.append(
                    {
                        "date": day.isoformat(),
                        "store_id": store,
                        "sku_id": spec.sku_id,
                        "units_sold": units,
                        "price": f"{spec.price:.2f}",
                        "promo_flag": promo,
                    }
                )
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True)
    p.add_argument("--start", default="2024-01-01")
    p.add_argument("--days", type=int, default=730)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    start = date.fromisoformat(args.start)
    rows = generate(start, args.days, args.seed)

    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["date", "store_id", "sku_id", "units_sold", "price", "promo_flag"]
        )
        writer.writeheader()
        writer.writerows(rows)

    print(
        f"wrote {len(rows)} rows -> {args.out} "
        f"({len(STORES)} stores x {len(SKU_SPECS)} SKUs x {args.days} days, seed={args.seed})"
    )


if __name__ == "__main__":
    main()
