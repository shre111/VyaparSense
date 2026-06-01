# Memory — current working state

> Living scratchpad of where the project actually is. Update at the end of each work session. Newest at top.

## Snapshot (2026-06-02)
- **Phase:** Phase 0 ✅, Phase 1 ✅, Phase 2 ✅ COMPLETE. Phase 3 (classical & intermittent) IN PROGRESS — ETS/AutoARIMA (#36) and Croston/SBA/TSB (#38) done; only quantile/probabilistic forecasts remain. All code verified on `main`.
- **Repo:** github.com/shre111/VyaparSense. `main` protected (3 CI checks + up-to-date branch; no force-push/delete). main push-CI green. Only `main` branch remains on remote.
- **End-to-end pipeline (verified green on main):** CSV → `read_sales_csv` → `clean_sales` (dedupe + calendar gap-fill) → `to_series` → `classify_series` (ADI/CV²) → persisted per-tenant via `POST /tenants/{id}/uploads`. Forecasting: `select_per_series` runs an expanding-window backtest of all candidate models (baselines + classical + intermittent) and picks the lowest pooled-WAPE per series. **ML lib 124 tests, API 7 tests** — ruff + ruff-format + mypy(strict) + pytest all pass in CI.
- **Tooling pinned (PR #30):** `ruff==0.15.15`, `mypy==1.13.0` in both pyproject dev extras, so local == CI. Root-cause fix for Phase 1's green-local/red-CI thrash (unpinned tools let CI pull newer ruff that flagged B008 `Depends()`-in-defaults; API uses `SessionDep = Annotated[...]`). API landed cleanly in PR #31.
- **GitHub identity:** push/PRs via `gh` as **shre111** (gh keyring auth, token scopes incl. repo/workflow). Repo-local git author = `shre111 <155060758+shre111@users.noreply.github.com>` to match existing history. Never push to `main` directly — feature branch + PR + squash-merge.

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
- Docs PRs #11, #14, #25, #26, #27, #32 — memory/progress updates.

## Shipped (Phase 2)
- PR #33 — `vyaparsense_ml.forecasting` subpackage (pure stdlib, no new deps):
  - `models.py` — `Naive`, `MovingAverage`, `SeasonalNaive` behind a `Baseline` protocol.
  - `metrics.py` — `wape` (primary), `mase`, `rmse`, `bias`, `mape` (display-only, skips zero actuals) + `ForecastMetrics`/`compute_metrics`. Error ratios are fractions; display layer ×100. Per ADR-005.
  - `backtest.py` — expanding-window rolling-origin harness; pools every fold into one WAPE (the flywheel metric).
  - `selection.py` — `select_model`/`select_per_series` pick lowest pooled-WAPE model per series.
  - +42 tests (47→89). **Honest sample-data backtest** (16 series, 52 folds/series, h=7, step=7, 365-day warmup): `moving_average_7` wins 14/16; `naive` wins 1 (SKU-BATTERY-AA @ BLR), `seasonal_naive_7` wins 1 (SKU-GIFT-BOX @ BLR). Lumpy/intermittent SKUs (GIFT-BOX, PRESSURE-CK, BATTERY-AA, SHAMPOO-S) sit at WAPE > 1.0 → the gap Phase 3 targets.

## Shipped (Phase 3, in progress)
- PR #36 — `forecasting/classical.py`: `AutoETS` and `AutoARIMA` thin adapters over Nixtla `statsforecast` (ADR-004), conforming to the `Baseline` protocol so the Phase 2 harness drives them unchanged. First heavy deps added to `packages/ml` (`statsforecast>=2.0`, `numpy>=1.26`). Guards: require ≥2*season_length obs; clamp negative outputs to 0; fall back to seasonal-naive on non-finite optimizer output. +12 tests (89→101). **Backtest vs baselines** (same protocol): a classical model beats the best Phase 2 baseline on **14/16** series (ARIMA wins 10, ETS 4, naive 1, MA7 1). The 2 losses are the intermittent SKUs SKU-BATTERY-AA & SKU-SHAMPOO-S → exactly what Croston/SBA/TSB (next item) targets.
  - Process note: first PR (#35) failed commitlint `subject-case` (had `AutoETS`/`AutoARIMA` capitalized — subjects must be lower-case); closed and re-landed as #36 with `add auto-ets and auto-arima models`.
- PR #38 — `forecasting/intermittent.py`: `Croston`, `CrostonSBA`, `TSB` thin adapters over `statsforecast`, same `Baseline`-protocol pattern; flat forecasts. Guards: reject empty history/bad horizon/out-of-range alpha; clamp negatives; fall back to flat `Naive` on non-finite. +23 tests (101→124). **Backtest vs full 8-model pool** (same protocol): SBA wins 5/16; ARIMA still 8; naive/MA7/ETS 1 each; **Croston & TSB win nothing**. SBA modestly lowers best WAPE on the hardest SKUs vs #36 (GIFT-BOX@BLR 1.719→1.663, BATTERY-AA@DEL 1.426→1.424, SHAMPOO-S@DEL 1.197→1.196) but does NOT sweep the lumpy SKUs — ARIMA keeps PRESSURE-CK (both) & GIFT-BOX@DEL. Honest outcome: SBA earns a pool slot; Croston/TSB retained as benchmarks only.

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

## Next actions (Phase 3 — remaining)
1. ✅ `feat(ml): ETS + AutoARIMA via statsforecast` (#36, done).
2. ✅ `feat(ml): Croston / SBA / TSB for intermittent SKUs` (#38, done).
3. `feat(ml): probabilistic/quantile forecasts` — NEXT, last Phase 3 item. Feeds service-level-aware reorder points (Phase 5). statsforecast models expose prediction intervals via `level=[...]`/`forecast(..., level=)`; will likely need the metrics/backtest harness extended to score quantiles (e.g. pinball/quantile loss) — currently they only handle point forecasts. Design this carefully; may warrant 2 micro-PRs (quantile-capable model output, then quantile metrics + backtest).
- Each rung must beat the prior models on the same per-series backtest, or document why not.
- After Phase 3: wire selection into `POST /tenants/{id}/forecasts` persisting into append-only `forecasts` → enables the accuracy-over-time chart.

## Local dev quickstart
- ML (Linux/Mac): `cd packages/ml && python3.13 -m venv .venv && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest`
- API (Linux/Mac): `cd apps/api && python3.13 -m venv .venv && .venv/bin/pip install -e ../../packages/ml && .venv/bin/pip install -e ".[dev]" && .venv/bin/pytest`
- DB: `make up`; migrations `cd apps/api && alembic upgrade head`
- **Windows (this machine):** no system Python and no `py` launcher — build venvs with conda base 3.13 (`C:\Users\91890\miniconda3\python.exe`). Venv tools live in `.venv\Scripts\` (e.g. `packages\ml\.venv\Scripts\pytest.exe`), not `.venv/bin/`. Docker 27 + Node 20 present. `.venv`s are gitignored.

## Notes / gotchas (hard-learned)
- **One PR at a time.** Cut each branch from FRESH `origin/main`. Don't start the next branch before the previous PR has merged.
- **Verify the EXACT tree you push.** Build the venv deliberately, WAIT, confirm the tool exists. Run `ruff format .` (not just `--check`). Ensure `git status` is clean before pushing — uncommitted working-tree fixes = green local / red CI.
- **After `gh pr merge`, confirm it merged** (check the file is on `origin/main`). Never let docs claim completion before code is confirmed on main.
- **`git push` hangs on this machine** (times out, exit 124) because the SYSTEM gitconfig (`C:/Program Files/Git/etc/gitconfig`) sets `credential.helper=manager` (Git Credential Manager). Git runs `manager` FIRST for github; once its cached token expires it blocks on an interactive prompt that never appears. A repo-local host helper alone does NOT fix it — git tries `manager` before reaching it. **Fix (persisted in this clone's `.git/config`):** reset the helper list then add gh, both host-scoped:
  `git config --local --add credential.https://github.com.helper ""` then `... --add credential.https://github.com.helper "!gh auth git-credential"`. The empty value clears `manager`; gh (authenticated) then serves the token non-interactively. Verify with `git push --dry-run` (returns instantly). One-off alternative: `git -c credential.helper= -c "credential.helper=!gh auth git-credential" push ...`. Re-apply on fresh clones.
- **commitlint requires lower-case subjects** (`subject-case` = lower-case, `header-max-length` 72). Camel-case identifiers in the subject (e.g. `AutoETS`) fail CI even though Python/Web pass — write `auto-ets`/`auto-arima`. Other rules pass cleanly on the standard single-line format.
- **`gh pr merge` quoting on PowerShell:** pass `--subject "..."` only; do NOT pass `--body ""` (the empty arg gets dropped and gh errors "flag needs an argument: --body"). Squash merge needs no body.
- `python3` may be 3.14 (too new for ML wheels) — use 3.13. ML targets 3.11–3.13.
- MAPE misleads on intermittent demand; **keep naive baselines as the permanent benchmark** (never delete); select per-series **by backtest**, not by vibe — a naive/seasonal model winning is valid. M5 → LightGBM beats DL on this data shape.
- Concrete model instances collected in a list infer as `list[object]` unless annotated — annotate `list[Baseline]` (the Protocol is structural; the classes share no nominal base), or mypy(strict) errors at the call site.
