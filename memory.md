# Memory — current working state

> Living scratchpad of where the project actually is. Update at the end of each work session. Newest at top.

## Snapshot (2026-05-31)
- **Phase:** Phase 0 COMPLETE. Phase 1 (data spine) is next.
- **Repo:** live at github.com/shre111/VyaparSense. `main` seeded; PR #6 (scaffold) merged; issues #1–5 closed.
- **GitHub identity:** push/PRs go through `gh` as **shre111** (repo-local credential helper `credential.https://github.com.helper = !gh auth git-credential`). git author = Shreya Dantani. Do NOT push to `main` directly — feature branch + PR only.
- **Docs created:** CLAUDE.md, decisions.md, plan.md, README.md, memory.md.
- **Scaffold landed:** monorepo dirs, .gitignore/.gitattributes/.editorconfig, CONTRIBUTING, issue/PR templates, commitlint, pre-commit, Makefile, CI (commitlint+python+web, all green), docs/backlog.md.
- **Toolchain:** git 2.50, node 22, python 3.13 (NOT 3.14 — too new for ML wheels), docker 28, gh 2.89. No `uv`.

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

## Next actions (Phase 1 — data spine)
1. `feat(ml): define canonical sales-history schema + pydantic models` (cols: date, store_id, sku_id, units_sold, price, promo_flag).
2. `chore: add docker-compose for postgres + redis` (infra/).
3. `chore: add sample sales dataset under data/samples` — synthetic kirana/D2C with smooth/intermittent/erratic/lumpy SKUs.
4. `feat(ml): CSV ingest + validation`, then cleaning, then demand classification (ADI/CV²).
5. Set up Python env pinned to 3.13 in packages/ml (pyproject + ruff/mypy/pytest).
6. Consider branch protection on `main` (require PR + CI) — ask user.

## Notes / gotchas
- MAPE is misleading on intermittent (zero-heavy) demand — never select models on it.
- Expect naive baselines to win for some SKUs; that's correct, keep them as permanent benchmark.
- M5 evidence: LightGBM global model beats deep learning on this data shape — don't reach for N-BEATS/TFT early.
