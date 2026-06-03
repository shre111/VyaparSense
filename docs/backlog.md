# Backlog — micro-issues

Each item is one micro-issue → one micro-PR. Ordered by phase (see [plan.md](../plan.md)). Check off as issues are created/closed. This is the source for `gh issue create`.

## Phase 0 — Foundations ✅
- [x] `chore: scaffold monorepo structure (apps/web, apps/api, packages/ml)` (#6)
- [x] `chore: add .gitignore, .gitattributes, .editorconfig` (#6)
- [x] `chore: add issue + PR templates` (#6)
- [x] `chore: add CONTRIBUTING with branch/commit conventions` (#6)
- [x] `chore: add commitlint + pre-commit config` (#6)
- [x] `chore: add CI workflow (commitlint, python lint/test, web build)` (#6)
- [x] `chore: add docker-compose for postgres + redis` (#22)
- [x] `chore: add sample sales dataset under data/samples` (#8)
- [x] `chore: set up packages/ml python project (ruff/mypy/pytest)` (#10)
- [ ] `docs: add LICENSE` (decision pending — user unsure; default proprietary)

## Phase 1 — Data spine ✅
- [x] `feat(ml): define canonical sales-history schema + pydantic models` (#13)
- [x] `feat(ml): CSV ingest with validation + helpful error messages` (#16)
- [x] `feat(ml): data cleaning (dedupe, calendar gap-fill, negative/return handling)` (#18)
- [x] `feat(ml): demand classification (ADI & CV² → smooth/intermittent/erratic/lumpy)` (#20)
- [x] `feat(api): Postgres schema + Alembic migrations (append-only forecasts)` (#24)
- [x] `feat(api): upload endpoint → store raw + parsed series` (#24)

## Phase 2 — Dumb baselines ✅
- [x] `feat(ml): naive, moving-average, seasonal-naive models` (#33)
- [x] `feat(ml): backtesting harness (rolling-origin / expanding window)` (#33)
- [x] `feat(ml): metrics (WAPE, MASE, RMSE, bias, MAPE-display)` (#33)
- [x] `feat(ml): per-series model selection by backtest` (#33)

## Phase 3 — Classical & intermittent ✅
- [x] `feat(ml): ETS + AutoARIMA via statsforecast` (#36)
- [x] `feat(ml): Croston / SBA / TSB for intermittent SKUs` (#38)
- [x] `feat(ml): probabilistic/quantile forecasts` (#40 metrics, #41 forecaster + backtest)

## Phase 4 — Global ML model ✅
- [x] `feat(ml): feature engineering (calendar, price, promo, lags, rolling)` (#43)
- [x] `feat(ml): LightGBM global model (recursive multi-step)` (#45)
- [x] `feat(ml): model card generation per training run` (#47)

## Phase 5 — Replenishment ✅
- [x] `feat(ml): safety stock + reorder point + EOQ + days-of-cover` (#49)
- [x] `feat(ml): service-level targets → reorder suggestions` (#51)
- [x] `feat(ml): simulated stockout / dead-stock KPIs` (#53)

## Cross-cutting — API integration (wire packages/ml into apps/api)
> Bridges the ML library into the FastAPI service so the frontend has real data.
- [x] `feat(api): forecast generation + read endpoints (baselines, sync)` (#55)
- [x] `feat(api): accuracy-over-time endpoint (rolling WAPE: past forecasts vs actuals)` (#57)
- [x] `feat(api): reorder-suggestion + simulation-KPI endpoints` (#59)
- [x] `feat(api): as-of forecast cutoff + accuracy bucketed by horizon week (enables the hero chart)` (#69)
- Async forecast jobs (ADR-007), sliced:
  - [x] `feat(api): async forecast jobs with status polling` (#83; job model + `POST /forecast-jobs` + `GET /forecast-jobs/{id}`, interim `BackgroundTasks` transport)
  - [x] `feat(api): redis-backed worker (RQ) for forecast jobs` (#85; `forecast_queue` setting → RQ worker or inline `BackgroundTasks`; RQ chosen per ADR-011)
  - [x] `feat(api): run classical + intermittent ladder in jobs` (#87; `FULL_LADDER_MODELS` selected per-series by backtest)
  - [ ] `feat(api): add the global LightGBM to the job ladder` (rung 4; needs a SalesRecord loader + pooled per-series-vs-global compare)
  - [ ] `feat(web): forecast job-status UX (enqueue + poll)`

## Phase 6 — Frontend ✅
- [x] `feat(web): scaffold Next.js app + Tailwind + shadcn/ui` (#61)
- [x] `feat(web): CSV upload + job-status UX` (#63; sync upload — job-status UX follows the async worker)
- [x] `feat(web): per-SKU forecast chart` (#65; point line — confidence band follows a quantile read endpoint)
- [x] `feat(web): reorder suggestions table` (#67)
- [x] `feat(web): accuracy-over-time hero chart (rolling WAPE)` (#71; + KPI cards, backfill via as-of)
- [x] `feat(web): auth flow — login/signup, authenticated API client, route guard` (#81)

## Phase 7 — Multi-tenant SaaS (custom auth)
> ⚠️ Security-sensitive — needs a full security review before launch (CLAUDE.md, ADR-006).
- [x] `feat(api): custom auth — signup/login (Argon2id), JWT access + refresh cookies` (#73 primitives, #75 endpoints)
  - [x] security primitives: Argon2id hash/verify + JWT access/refresh helpers (#73)
  - [x] User model + Alembic migration, signup/login endpoints, refresh cookies (#75)
- [x] `feat(api): refresh-token rotation + reuse detection` (#77; + `GET /auth/me` + access-token dependency)
- [ ] `feat(api): email verification + password reset`
- [x] `feat(api): tenant_id isolation — business endpoints scoped to authed tenant` (#79; Postgres RLS still TODO as defense-in-depth)
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
