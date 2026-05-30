# Memory — current working state

> Living scratchpad of where the project actually is. Update at the end of each work session. Newest at top.

## Snapshot (2026-05-31)
- **Phase:** Phase 0 COMPLETE. Phase 1 (data spine) IN PROGRESS — dataset, ML project, and canonical schema done.
- **Repo:** live at github.com/shre111/VyaparSense. `main` protected (requires 3 CI checks + up-to-date branch; no force-push/delete). PRs #6, #8, #10, #11, #13 merged; issues #1–5, #7, #9, #12 closed. No open issues.
- **GitHub identity:** push/PRs go through `gh` as **shre111** (repo-local credential helper `credential.https://github.com.helper = !gh auth git-credential`). git author = Shreya Dantani. Do NOT push to `main` directly — feature branch + PR only.
- **Shipped so far:**
  - PR #6 — Phase 0 scaffold (monorepo dirs, .gitignore/.gitattributes/.editorconfig, CONTRIBUTING, issue/PR templates, commitlint, pre-commit, Makefile, CI, docs/backlog.md).
  - PR #8 — synthetic dataset `data/samples/sales_history.csv` (2 stores × 8 SKUs × 730 days = 11,680 rows) + seeded stdlib generator `scripts/generate_sample_sales.py`. Verified 8/8 SKUs hit intended ADI/CV² quadrant.
  - PR #10 — `packages/ml` python project: `vyaparsense_ml` (src layout, py3.11–3.13), ruff + mypy(strict) + pytest; CI now runs them for real.
  - PR #13 — `vyaparsense_ml.schema`: canonical `SalesRecord` (pydantic v2, frozen, extra=forbid), `CANONICAL_COLUMNS`, `DemandPattern` StrEnum, `validate_rows()` (aggregates row errors). 23 tests. pydantic now a runtime dep.
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

## Next actions (Phase 1 — data spine, continued)
1. `feat(ml): CSV ingest + validation` (clear error messages), reads CSV → `validate_rows()` → list[SalesRecord], against data/samples.
2. `feat(ml): data cleaning` (dedupe, calendar gap-fill, negative/return handling).
3. `feat(ml): demand classification` (ADI/CV² → DemandPattern) — logic already proven in PR #8 verification; now wire to schema's `DemandPattern` enum.
4. `chore: docker-compose postgres + redis` (infra/); then Postgres schema + Alembic (append-only forecasts).

Done: branch protection ✅; sample dataset ✅; packages/ml python project ✅; canonical schema ✅.

## Notes / gotchas
- `python3` resolves to 3.14 on this machine — always use `python3.13` for the ML venv.
- Keep memory.md/doc-only edits in their own docs PR, not bundled with code PRs.
- MAPE is misleading on intermittent (zero-heavy) demand — never select models on it.
- Expect naive baselines to win for some SKUs; that's correct, keep them as permanent benchmark.
- M5 evidence: LightGBM global model beats deep learning on this data shape — don't reach for N-BEATS/TFT early.
