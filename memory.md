# Memory — current working state

> Living scratchpad of where the project actually is. Update at the end of each work session. Newest at top.

## Snapshot (2026-05-31)
- **Phase:** Phase 0 ✅ and Phase 1 (data spine) ✅ COMPLETE — all code verified on main. Phase 2 (dumb baselines) is next.
- **Repo:** github.com/shre111/VyaparSense. `main` protected (3 CI checks + up-to-date branch; no force-push/delete). 0 open PRs, 0 open issues. main push-CI green. Only `main` branch remains on remote.
- **End-to-end pipeline (verified green on main):** CSV → `read_sales_csv` → `clean_sales` (dedupe + calendar gap-fill) → `to_series` → `classify_series` (ADI/CV²) → persisted per-tenant via `POST /tenants/{id}/uploads`. **ML lib 53 tests, API 7 tests** — ruff + ruff-format + mypy(strict) + pytest all pass in CI.
- **GitHub identity:** push/PRs via `gh` as **shre111** (repo-local helper `credential.https://github.com.helper = !gh auth git-credential`). git author = Shreya Dantani. Never push to `main` directly — feature branch + PR + squash-merge.

## Shipped (Phase 0 + 1)
- PR #6 — Phase 0 scaffold (monorepo dirs, gitignore/attributes/editorconfig, CONTRIBUTING, issue/PR templates, commitlint, pre-commit, Makefile, CI, docs/backlog.md).
- PR #8 — synthetic dataset `data/samples/sales_history.csv` (2 stores × 8 SKUs × 730 days = 11,680 rows) + seeded stdlib generator `scripts/generate_sample_sales.py`. 8/8 SKUs hit intended ADI/CV² quadrant.
- PR #10 — `packages/ml` python project (`vyaparsense_ml`, src layout, py3.11–3.13), ruff + mypy + pytest in CI.
- PR #13 — `schema.py`: `SalesRecord` (pydantic v2, frozen, extra=forbid), `CANONICAL_COLUMNS`, `DemandPattern`, `validate_rows()`.
- PR #16 — `ingest.py`: `read_sales_csv()` + `IngestError` (file/header checks, BOM-tolerant).
- PR #18 — `cleaning.py`: `clean_sales()` (dedupe, calendar gap-fill, price carry-forward), `to_series()`. Idempotent.
- PR #20 — `classification.py`: `classify_demand()`/`classify_series()` → `DemandStats` (ADI/CV², Syntetos-Boylan). Reproduces 8/8 sample quadrants end-to-end.
- PR #22 — `infra/docker-compose.yml` (postgres:16 + redis:7) + `.env.example`.
- PR #24 — `apps/api`: FastAPI + SQLAlchemy 2.0 + Alembic. Tables tenants/uploads/sales_records/forecasts (all `tenant_id`; forecasts append-only per ADR-008). Endpoints `/health`, `POST/GET /tenants/{id}/uploads`. SQLite+TestClient tests; Postgres/Alembic = prod source of truth. CI job `Python (ml + api)` lints/types/tests both packages.
- Docs PRs #11, #14, #25, #26, #27 — memory/progress updates.

## Decided
- **Brand: VyaparSense** (vyaparsense.com). Repo codename `kirana-demand`. (ADR-001)
- **Auth: custom** — FastAPI Argon2id + JWT access + rotating refresh cookies. No third-party. (ADR-006)
- Stack: Next.js/TS + FastAPI + Postgres/Redis + (statsforecast, LightGBM).
- Monorepo `apps/web`,`apps/api`,`packages/ml` (ADR-002). Next.js never touches ML DB directly (ADR-003).
- ML ladder: naive → classical → intermittent → global LightGBM → hierarchical → transfer-learning → reorder opt.
- Metrics: WAPE primary, MASE for intermittent, MAPE display-only (ADR-005).
- Forecasts append-only for the "getting smarter" chart (ADR-008).
- Commits: single-line Conventional Commits, NO body, NO Co-Authored-By (ADR-009).

## Open questions (user input)
- ADR-010 pricing tiers per market (later). License (user unsure; default proprietary). Wedge (default D2C-first, generic ingestion).

## Next actions (Phase 2 — dumb baselines)
1. `feat(ml): naive, moving-average, seasonal-naive models` — permanent honest benchmark.
2. `feat(ml): backtesting harness` (rolling-origin / expanding window).
3. `feat(ml): metrics` (WAPE, MASE, RMSE, bias, MAPE-display-only).
4. `feat(ml): per-series model selection by backtest`.
Then `POST /tenants/{id}/forecasts` job persisting into append-only `forecasts` table → enables the accuracy chart.

## Local dev quickstart
- ML: `cd packages/ml && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest`
- API: `cd apps/api && python3.13 -m venv .venv && .venv/bin/pip install -e ../../packages/ml && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest`
- DB: `make up`; migrations `cd apps/api && alembic upgrade head`

## Notes / gotchas (hard-learned in Phase 1)
- **One PR at a time.** Cut each branch from FRESH `origin/main`. Don't start the next branch before the previous PR has merged.
- **Verify the EXACT tree you push.** The venv install auto-backgrounds and can silently fail on PyPI timeouts; build it as a deliberate background task, WAIT, confirm `.venv/bin/ruff` exists. Run `ruff format .` (not just `--check`). Ensure `git status` is clean (dirty=0) before pushing — uncommitted working-tree fixes that pass locally but aren't in the commit = green local / red CI.
- **After `gh pr merge`, confirm it merged** (check the file is on `origin/main`); a red PR returns merge_rc=1 and does NOT merge. Never let docs claim completion before code is confirmed on main.
- `python3` = 3.14 here (breaks venv / too new for ML wheels) — always `python3.13`.
- MAPE misleads on intermittent demand; keep naive baselines as permanent benchmark; M5 → LightGBM beats DL on this data shape.
