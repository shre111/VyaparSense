<h1 align="center">VyaparSense <sub><sup>(codename: kirana-demand)</sup></sub></h1>

<p align="center">
  <b>Demand-sensing & auto-replenishment for SMB retailers and D2C brands.</b><br>
  Upload your sales history → get per-SKU demand forecasts and reorder suggestions → watch accuracy improve every week.
</p>

---

## The problem

SMB retailers and D2C brands guess inventory. The result is the worst of both worlds at once: **dead stock** (cash frozen on shelves) **and stockouts** (lost sales). India alone has ~13M kirana stores, and the global SMB story is identical.

## The idea

Every real sale is a free training label. So this product **starts with honest, dumb baselines and gets measurably smarter over time** — the forecast error (WAPE/MAPE) drops week over week. That improving-accuracy curve is both the customer's ROI and the most legible proof that the ML is actually working.

```
naive → classical time-series → intermittent/probabilistic → global ML (LightGBM)
      → hierarchical → transfer-learning cold-start → reorder optimization
```

## What it does (MVP)

- 📤 Upload sales history (CSV)
- 🧹 Auto-clean, validate, and classify demand patterns (smooth / intermittent / erratic / lumpy)
- 🔮 Per-SKU demand forecasts with confidence bands
- 📦 Reorder suggestions: reorder point, safety stock, order quantity, days of cover
- 📈 **Accuracy-over-time chart** — see the model get smarter

## Tech stack

| | |
|---|---|
| **Frontend** | Next.js (App Router) · TypeScript · Tailwind · shadcn/ui |
| **Backend** | Python · FastAPI · PostgreSQL · Redis · custom auth (Argon2id + JWT) |
| **ML** | pandas · Nixtla `statsforecast` · LightGBM · scikit-learn |
| **Infra** | Vercel (web) · Render/Railway/Fly (api) · Neon/Supabase (db) · S3/R2 |

## Repository layout

```
apps/web      # Next.js + TypeScript frontend
apps/api      # FastAPI backend
packages/ml   # forecasting + replenishment library (unit-tested)
infra/        # docker-compose, migrations, IaC
docs/         # ADRs, model cards, diagrams
data/samples/ # sample datasets
```

## Getting started

> ⚠️ Early development — scaffolding in progress. Commands below are the target.

```bash
git clone <repo> && cd kirana-demand
docker compose up            # full stack

# or individually:
cd apps/web && npm run dev                       # frontend
cd apps/api && uvicorn app.main:app --reload     # backend
cd packages/ml && pytest -q                       # ML tests
```

## Project docs

- 📋 [plan.md](plan.md) — technical roadmap, business case, profitability, GTM
- 🧭 [decisions.md](decisions.md) — architecture decision records
- 🤖 [CLAUDE.md](CLAUDE.md) — guide for AI agents / contributors
- 🧠 [memory.md](memory.md) — current working state

## Status

🚧 Pre-alpha. Building in public — follow the accuracy chart drop.

## License

TBD.
