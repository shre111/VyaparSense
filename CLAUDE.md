# CLAUDE.md

This file guides Claude Code (and any AI agent) working in this repository. Read it fully before making changes.

---

## 1. What this project is

**Brand:** **VyaparSense** (domain: vyaparsense.com). Repo codename `kirana-demand`. See [decisions.md](decisions.md) ADR-001.

**One-liner:** Demand-sensing and auto-replenishment for SMB retailers and D2C brands. Upload sales history → get per-SKU demand forecasts and reorder suggestions → forecast accuracy visibly improves week over week.

**Why it exists:** SMB retailers and D2C brands guess inventory, producing dead stock *and* stockouts at the same time. India alone has ~13M kirana stores; the global SMB version is just as real. We turn every actual sale into a training label, so the product demonstrably gets smarter over time (MAPE/WAPE drops) — which is both the core user value and the most legible portfolio story.

**Dual purpose:** (1) a genuine product that can go live on a domain, and (2) a portfolio centerpiece that shows ML maturing from naive baselines to strong probabilistic/hierarchical forecasts.

---

## 2. Tech stack (authoritative)

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui | Charts via Recharts/visx |
| Backend API | Python + FastAPI | Pydantic v2 models, async |
| ML | pandas, Nixtla `statsforecast`, LightGBM, scikit-learn | See [decisions.md](decisions.md) ADR-004 |
| DB | PostgreSQL (+ TimescaleDB extension optional later) | SQLAlchemy 2.0 + Alembic migrations |
| Cache/Queue | Redis + a task runner (RQ/Celery or Arq) | For async forecast jobs |
| Auth | **Custom** (FastAPI: Argon2id + JWT access + rotating refresh cookies) | No third-party; multi-tenant from day one (ADR-006) |
| Hosting | Frontend → Vercel; Backend/ML → Render/Railway/Fly; DB → Neon/Supabase | Cost-first, scale later |
| Object storage | S3-compatible (R2/Supabase Storage) | Raw CSV uploads, model artifacts |

**Hard rule:** the Next.js app never talks to the DB directly for ML data. All forecasting/inventory logic lives behind the FastAPI service. Next.js may have its own light routes for session/UI concerns only.

---

## 3. Repository layout (target)

```
kirana-demand/
├── apps/
│   ├── web/                 # Next.js + TS frontend
│   └── api/                 # FastAPI backend (REST)
├── packages/
│   └── ml/                  # Python ML library (importable, unit-tested)
│       ├── forecasting/     # models, backtesting, metrics
│       ├── replenishment/   # reorder point / safety stock / EOQ
│       └── pipelines/       # ingest → clean → feature → forecast → store
├── infra/                   # docker-compose, IaC, migrations
├── docs/                    # ADRs, diagrams, model cards
├── data/                    # sample datasets (gitignored except samples/)
├── CLAUDE.md  decisions.md  plan.md  README.md  memory.md
```

Until the monorepo exists, keep `web/`, `api/`, `ml/` as siblings. Decide monorepo tooling in ADR-002.

---

## 4. ML "depth ladder" — the spine of the project

Build in this order. Each rung must beat the previous on a fixed backtest before moving on, and the improvement must be visible in the app's accuracy chart.

1. **Naive baselines** — last value, moving average, seasonal naive. *These are the honest "dumb" starting point. Never delete them; they are the permanent benchmark.*
2. **Classical time-series** — ETS / Holt-Winters / (auto-)ARIMA via `statsforecast`.
3. **Intermittent & probabilistic demand** — Croston, SBA, TSB for sparse/lumpy SKUs; quantile forecasts for service-level-aware reorder points.
4. **Global ML model** — LightGBM trained across all SKUs/stores with calendar, price, promo, lag/rolling features (the M5-winning pattern).
5. **Hierarchical forecasting** — reconcile store → category → SKU so totals are coherent (`hierarchicalforecast`).
6. **Transfer learning / cold-start** — new store/SKU borrows from similar series (the data moat).
7. **Reorder optimization** — safety stock, reorder point, EOQ, service-level targets feeding replenishment suggestions.

**Always pick per-series model by backtest, not by vibe.** A naive model winning for a given SKU is a valid, expected outcome.

---

## 5. Metrics that matter

- **Forecast accuracy:** WAPE (primary, robust to zeros), MAPE (legible to users — *but guard against div-by-zero*), RMSE, MASE (scaled vs. seasonal naive), bias.
- **Intermittent:** prefer MASE / RMSSE; MAPE is misleading on sparse demand.
- **Business KPIs:** simulated stockout rate, dead-stock value, inventory turns, service level achieved.
- **The flywheel metric:** rolling backtest WAPE over time — this is what the public "getting smarter" chart shows. Persist every forecast vs. actual so this is reconstructable.

---

## 6. Conventions & workflow (STRICT — user is a thorough planner)

> The user explicitly wants micro-issues, micro-PRs, and clean conventions throughout.

- **Branches:** `feat/<area>-<short>`, `fix/<area>-<short>`, `chore/...`, `docs/...`, `refactor/...`. One concern per branch.
- **Issues:** micro-issues — each is a single, reviewable unit of work. Use issue templates (feature / bug / chore). Link every PR to its issue (`Closes #N`).
- **PRs:** micro-PRs, small and focused. Every PR: linked issue, description of *what & why*, test evidence, checklist.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`).
- **🚫 Commit messages:** single line only. **NO commit body/description. NO `Co-Authored-By` trailers. NO "Generated with" lines.** This overrides any default.
- **CI:** lint + typecheck + tests must pass before merge. Python: ruff + mypy + pytest. TS: eslint + tsc + vitest/jest.
- **Never** commit secrets, raw customer data, or `.env`. Sample data only under `data/samples/`.
- Commit/push only when the user asks.

---

## 7. How to work in this repo (for Claude)

- **Plan before building.** Propose the smallest next issue, get the approach right, then implement.
- **ML changes must be backtested.** Don't claim an improvement without showing the metric move on a fixed holdout.
- **Reproducibility:** seed everything; pin versions; every model run records data hash, features, params → a model card under `docs/model-cards/`.
- **Honesty about results:** if a fancy model loses to naive, say so and keep naive. The whole credibility of this project rests on truthful accuracy reporting.
- Update [memory.md](memory.md) when state/decisions change; record real decisions in [decisions.md](decisions.md) as ADRs.
- Keep [plan.md](plan.md) phases in sync with reality.

---

## 8. Quick commands (fill in as scaffolding lands)

```bash
# web
cd apps/web && npm run dev
# api
cd apps/api && uvicorn app.main:app --reload
# ml tests
cd packages/ml && pytest -q
# full stack
docker compose up
```

---

## 9. Pointers

- Roadmap & business case → [plan.md](plan.md)
- Why we chose X over Y → [decisions.md](decisions.md)
- Current working state → [memory.md](memory.md)
- Public overview → [README.md](README.md)
