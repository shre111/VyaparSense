# Case study — demand sensing & auto-replenishment

How VyaparSense turns two years of a retailer's sales history into per-SKU
forecasts and reorder decisions — and, just as important, how it reports its
own accuracy **honestly**, keeping the dumb baselines as the permanent benchmark
and letting the fancy models earn their place only when a backtest says so.

> All numbers below were measured on the bundled sample dataset
> (`data/samples/sales_history.csv`) and are reproducible (see the end). Where a
> result depends on policy parameters, the parameters are stated.

---

## The problem

SMB retailers and D2C brands guess inventory, and the guess fails in both
directions at once: **dead stock** (cash frozen on shelves) *and* **stockouts**
(lost sales, unhappy customers). The fix isn't a fancier spreadsheet — it's
turning every actual sale into a label and forecasting demand per SKU, then
translating those forecasts into concrete reorder quantities at a target service
level.

## The dataset

- **16 series** (store × SKU), **~730 days** (2 years) of daily sales.
- Demand is mostly **intermittent / lumpy** — long runs of zero demand punctuated
  by spikes. This matters: it's exactly the regime where naive percentage errors
  mislead and where intermittent-aware models (Croston/SBA/TSB) belong.

## The approach: a model "depth ladder"

Each rung must beat the previous one on the **same rolling-origin backtest**
before it's used. A naive model winning for a given SKU is a valid, expected
outcome — and we keep the baselines forever as the benchmark.

1. **Baselines** — naive, moving-average, seasonal-naive.
2. **Classical** — ETS, AutoARIMA (`statsforecast`).
3. **Intermittent & probabilistic** — Croston, SBA, TSB; empirical quantiles.
4. **Global model** — one LightGBM trained across every SKU/store (the M5 pattern).
5. **Hierarchical reconciliation** — store/SKU forecasts made coherent.
6. **Transfer-learning cold-start** — new SKUs borrow a shape from similar series.

Per series, the model is **chosen by backtest, not by vibe.** Accuracy is WAPE
(robust to the many zeros here), pooled over a fixed holdout — the same pooling
at every level so numbers are comparable.

## Results — reported honestly

### Forecast accuracy: global model vs per-series champions

On a 90-day window across all 16 series, pooled WAPE:

| approach | WAPE |
|---|---|
| per-series champions (full ladder) | **0.4261** |
| global LightGBM | 0.4332 |

The per-series champions **edge out** the global model on this window — mostly
`croston_sba`, which fits the intermittent demand well. So the system keeps the
champions here. The global model is competitive and tends to gain with more
history; the point is the job picks **whichever actually wins**, and reports both.

### Replenishment impact: fewer stockouts, not more dead stock

Feeding the forecasts into a day-by-day `(s, S)` policy simulation (lead time 7
days, 95% service level) versus a naive lead-time-demand policy, pooled over all
16 series:

| metric | naive policy | forecast-driven |
|---|---|---|
| fill rate | 91.0% | **97.5%** |
| units lost | 13,009 | **3,569** |

That's a **~73% reduction in lost units** at this service level. The figure moves
with the policy parameters (lead time, service level) — it's a simulation result,
not a customer outcome — but the direction is robust: forecast-driven reordering
cuts stockouts substantially without piling on dead stock.

### An honest negative: transfer-learning cold-start

We built cold-start (a new SKU borrows a normalized weekly shape from donor
series) and **backtested it** by treating each series as "new" (first 7 days
only) and forecasting the next 7:

| approach | WAPE |
|---|---|
| flat mean of the target's own history | **0.4487** |
| cold-start (borrowed shape) | 0.6950 |

**Cold-start loses — and we report it rather than hide it.** On this intermittent,
heterogeneous-level data there's little transferable weekly structure, so a
borrowed shape just adds variance. Cold-start ships as a backtest-gated primitive
(not a default); the global model already provides the cross-series transfer that
helps here. This is the whole point of the project's credibility: **the honest
result is the result.**

## The flywheel: getting measurably smarter

Every forecast is persisted (append-only) and later joined to what actually
happened, so **rolling accuracy is reconstructable** and can be charted week over
week. As more sales arrive, more labels train better models, and the public
"accuracy improving" story is backed by real stored data — not a marketing claim.

## Architecture (one paragraph)

A monorepo: a Next.js frontend, a FastAPI backend, and a pure-Python ML library.
Heavy forecasting runs as **async jobs** (Redis/RQ, with an in-process fallback)
so the full ladder — including LightGBM — never blocks a request; the UI enqueues
a job and polls it to completion. Multi-tenant from day one (custom Argon2id +
JWT auth, per-tenant data scoping). Every model run records a reproducible model
card.

## Limitations & what's next

- The hierarchy is `total → store → SKU` (no category metadata yet); reconciliation
  is a library primitive not yet wired into the serving path.
- Cold-start needs tighter donor similarity (category, profile clustering) to help
  on heterogeneous catalogs.
- Before launch: CSRF + Postgres RLS + email verification, and a full security
  review of the custom auth.

## Reproduce it

```bash
cd packages/ml && pytest -q          # 240 ML tests
cd apps/api    && pytest -q          # 94 API tests
# global-vs-champions and cold-start numbers come from generate_forecasts_full
# and cold_start_forecast on data/samples/sales_history.csv; the policy KPIs from
# app.replenishment.policy_kpis (lead_time_days=7, service_level=0.95).
```
