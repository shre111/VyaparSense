# data/samples

Small, curated, **non-sensitive** sample datasets for development, tests, and demos. Everything else under `data/` is gitignored.

Planned: a synthetic kirana/D2C sales history (multiple SKUs spanning smooth, intermittent, erratic, and lumpy demand patterns) so the forecasting ladder can be exercised end-to-end without real customer data.

Canonical sales-history columns (Phase 1): `date, store_id, sku_id, units_sold, price, promo_flag`.
