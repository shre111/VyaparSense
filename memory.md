# Memory — current working state

> Living scratchpad of where the project actually is. Update at the end of each work session. Newest at top.

## Snapshot (2026-05-31)
- **Phase:** Phase 0 ✅ and Phase 1 (data spine) ✅ COMPLETE. Phase 2 (dumb baselines) is next.
- **Repo:** live at github.com/shre111/VyaparSense. `main` protected (requires 3 CI checks + up-to-date branch; no force-push/delete). PRs #6,#8,#10,#11,#13,#16,#18,#20,#22,#24 merged. No open issues.
- **End-to-end pipeline works:** CSV → `read_sales_csv` → `clean_sales` (dedupe + calendar gap-fill) → `to_series` → `classify_series` (ADI/CV²) → persisted per-tenant via `POST /tenants/{id}/uploads`. ML lib has 53 tests; API has 7 (incl. tenant isolation). CI `Python (ml + api)` job tests both.
- **GitHub identity:** push/PRs go through `gh` as **shre111** (repo-local credential helper `credential.https://github.com.helper = !gh auth git-credential`). git author = Shreya Dantani. Do NOT push to `main` directly — feature branch + PR only.
- **Shipped so far:**
  - PR #6 — Phase 0 scaffold (monorepo dirs, .gitignore/.gitattributes/.editorconfig, CONTRIBUTING, issue/PR templates, commitlint, pre-commit, Makefile, CI, docs/backlog.md).
  - PR #8 — synthetic dataset `data/samples/sales_history.csv` (2 stores × 8 SKUs × 730 days = 11,680 rows) + seeded stdlib generator `scripts/generate_sample_sales.py`. Verified 8/8 SKUs hit intended ADI/CV² quadrant.
  - PR #10 — `packages/ml` python project: `vyaparsense_ml` (src layout, py3.11–3.13), ruff + mypy(strict) + pytest; CI now runs them for real.
  - PR #13 — `vyaparsense_ml.schema`: canonical `SalesRecord` (pydantic v2, frozen, extra=forbid), `CANONICAL_COLUMNS`, `DemandPattern` StrEnum, `validate_rows()` (aggregates row errors). pydantic now a runtime dep.
  - PR #16 — `vyaparsense_ml.ingest`: `read_sales_csv()` + `IngestError` (file/header checks, BOM-tolerant).
  - PR #18 — `vyaparsense_ml.cleaning`: `clean_sales()` (dedupe same-day, calendar gap-fill with zero-demand days, price carry-forward), `to_series()`. Idempotent.
  - PR #20 — `vyaparsense_ml.classification`: `classify_demand()`/`classify_series()` → `DemandStats` (ADI/CV², Syntetos-Boylan). Reproduces 8/8 sample quadrants end-to-end.
  - PR #22 — `infra/docker-compose.yml` (postgres:16 + redis:7) + `.env.example`.
  - PR #24 — `apps/api`: FastAPI + SQLAlchemy 2.0 + Alembic. Models tenants/uploads/sales_records/forecasts (all `tenant_id`; forecasts append-only per ADR-008). Endpoints `/health`, `POST/GET /tenants/{id}/uploads`. Tests on SQLite+TestClient; Postgres/Alembic = prod source of truth. CI extended to lint/type/test apps/api.
- **Toolchain:** git 2.50, node 22, python 3.13 (`python3.13`; NOT 3.14 — too new for ML wheels), docker 28, gh 2.89. No `uv`. Local dev venv: `packages/ml/.venv` (gitignored).

## Decided
- **Brand: VyaparSense** (vyaparsense.com). Repo codename `kirana-demand`. (ADR-001)
- **Auth: custom** — FastAPI Argon2id + JWT access + rotating refresh cookies. No third-party. (ADR-006)
- Stack: Next.js/TS + FastAPI + Postgres/Redis + (statsforecast, LightGBM). See [decisions.md](decisions.md).
- Monorepo: `apps/web`, `apps/api`, `packages/ml` (ADR-002).
- Next.js never touches ML DB directly (ADR-003).
- ML ladder: naive → classical → intermittent → global LightGBM → hierarchical → transfer-learning → reorder opt (CLAUDE.md §4).
- Metrics: WAPE primary, MASE for intermittent, MAPE display-only (ADR-005).
- Forecasts stored append-only for the "getting smarter" flywheel chart (ADR-008).
- Commit style: single-line Conventional Commits, NO body, NO Co-Authored-By (ADR-009 / CLAUDE.md §6).

## Open questions (need user input)
- ADR-010: exact pricing tiers per market (refine later).
- License choice — user unsure. Default recommendation: keep private/proprietary now; revisit (MIT if open-sourcing the ML lib for portfolio).
- Wedge — user unsure. Default: build D2C-first (clean Shopify/CSV data) while keeping ingestion generic so kirana/multi-store works too.

## Next actions (Phase 2 — dumb baselines)
1. `feat(ml): naive, moving-average, seasonal-naive models` — the permanent honest benchmark.
2. `feat(ml): backtesting harness` (rolling-origin / expanding window).
3. `feat(ml): metrics` (WAPE primary, MASE, RMSE, bias, MAPE-display-only).
4. `feat(ml): per-series model selection by backtest`.
Then wire a `POST /tenants/{id}/forecasts` job that persists into the append-only `forecasts` table → enables the "getting smarter" chart later.

Phase 0 ✅ + Phase 1 ✅ done. Pipeline ingest→clean→classify→persist is live.

## Local dev quickstart (verified)
- ML: `cd packages/ml && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest`
- API: `cd apps/api && python3.13 -m venv .venv && .venv/bin/pip install -e ../../packages/ml && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest`
- DB: `make up` (compose postgres+redis); API migrations: `cd apps/api && alembic upgrade head`

## Notes / gotchas
- `python3` resolves to 3.14 on this machine — always use `python3.13` for the ML venv.
- Keep memory.md/doc-only edits in their own docs PR, not bundled with code PRs.
- MAPE is misleading on intermittent (zero-heavy) demand — never select models on it.
- Expect naive baselines to win for some SKUs; that's correct, keep them as permanent benchmark.
- M5 evidence: LightGBM global model beats deep learning on this data shape — don't reach for N-BEATS/TFT early.
