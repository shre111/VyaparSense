# Backlog — micro-issues

Each item is one micro-issue → one micro-PR. Ordered by phase (see [plan.md](../plan.md)). Check off as issues are created/closed. This is the source for `gh issue create`.

## Phase 0 — Foundations
- [ ] `chore: scaffold monorepo structure (apps/web, apps/api, packages/ml)`
- [ ] `chore: add .gitignore, .gitattributes, .editorconfig`
- [ ] `chore: add issue + PR templates`
- [ ] `chore: add CONTRIBUTING with branch/commit conventions`
- [ ] `chore: add commitlint + pre-commit config`
- [ ] `chore: add CI workflow (commitlint, python lint/test, web build)`
- [ ] `chore: add docker-compose for postgres + redis`
- [ ] `chore: add sample sales dataset under data/samples`
- [ ] `docs: add LICENSE` (decision pending)

## Phase 1 — Data spine
- [ ] `feat(ml): define canonical sales-history schema + pydantic models`
- [ ] `feat(ml): CSV ingest with validation + helpful error messages`
- [ ] `feat(ml): data cleaning (dedupe, calendar gap-fill, negative/return handling)`
- [ ] `feat(ml): demand classification (ADI & CV² → smooth/intermittent/erratic/lumpy)`
- [ ] `feat(api): Postgres schema + Alembic migrations (append-only forecasts)`
- [ ] `feat(api): upload endpoint → store raw + parsed series`

## Phase 2 — Dumb baselines
- [ ] `feat(ml): naive, moving-average, seasonal-naive models`
- [ ] `feat(ml): backtesting harness (rolling-origin / expanding window)`
- [ ] `feat(ml): metrics (WAPE, MASE, RMSE, bias, MAPE-display)`
- [ ] `feat(ml): per-series model selection by backtest`

## Phase 3 — Classical & intermittent
- [ ] `feat(ml): ETS + AutoARIMA via statsforecast`
- [ ] `feat(ml): Croston / SBA / TSB for intermittent SKUs`
- [ ] `feat(ml): probabilistic/quantile forecasts`

## Phase 4 — Global ML model
- [ ] `feat(ml): feature engineering (calendar, price, promo, lags, rolling)`
- [ ] `feat(ml): LightGBM global model (recursive multi-step)`
- [ ] `feat(ml): model card generation per training run`

## Phase 5 — Replenishment
- [ ] `feat(ml): safety stock + reorder point + EOQ + days-of-cover`
- [ ] `feat(ml): service-level targets → reorder suggestions`
- [ ] `feat(ml): simulated stockout / dead-stock KPIs`

## Phase 6 — Frontend
- [ ] `feat(web): scaffold Next.js app + Tailwind + shadcn/ui`
- [ ] `feat(web): CSV upload + job-status UX`
- [ ] `feat(web): per-SKU forecast chart with confidence band`
- [ ] `feat(web): reorder suggestions table`
- [ ] `feat(web): accuracy-over-time hero chart (rolling WAPE)`

## Phase 7 — Multi-tenant SaaS (custom auth)
- [ ] `feat(api): custom auth — signup/login (Argon2id), JWT access + refresh cookies`
- [ ] `feat(api): refresh-token rotation + reuse detection`
- [ ] `feat(api): email verification + password reset`
- [ ] `feat(api): tenant_id isolation middleware + RLS`
- [ ] `feat(api): rate limiting + CSRF protection for cookie auth`
- [ ] `feat: billing (Razorpay/Stripe) + free-tier limits`
- [ ] `feat: integrations (Shopify / WooCommerce / CSV scheduler)`
- [ ] `feat: reorder alerts (email / WhatsApp)`

## Phase 8 — Moat
- [ ] `feat(ml): hierarchical reconciliation (store→category→SKU)`
- [ ] `feat(ml): transfer-learning cold-start for new store/SKU`

## Phase 9 — Polish & launch
- [ ] `feat(web): landing page + public "MAPE dropping" demo`
- [ ] `chore: observability (logging, error tracking, metrics)`
- [ ] `docs: onboarding + model cards + case study`
