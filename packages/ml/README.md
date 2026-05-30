# packages/ml — forecasting & replenishment library

Pure, unit-tested Python library. No web/DB concerns — importable headless.

```
forecasting/     # models, backtesting, metrics
replenishment/   # reorder point, safety stock, EOQ, service levels
pipelines/       # ingest → clean → classify → feature → forecast → store
```

Model ladder (see [CLAUDE.md](../../CLAUDE.md) §4): naive → classical → intermittent → global LightGBM → hierarchical → transfer-learning → reorder optimization.

**Target Python:** 3.11–3.13 (LightGBM/statsforecast wheels). Local default 3.13.

Built starting Phase 1.
