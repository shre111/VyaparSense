# Memory — current working state

> Living scratchpad of where the project actually is. Update at the end of each work session. Newest at top.

## Snapshot (2026-05-31)
- **Phase:** Pre-Phase-0. Planning complete; no code scaffolded yet.
- **Repo:** not yet a git repository. First task is `git init` + Phase 0 foundations.
- **Docs created:** CLAUDE.md, decisions.md, plan.md, README.md, memory.md.

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

## Next actions
1. `git init`; add `.gitignore`, issue/PR templates, Conventional Commits config.
2. Phase 0: monorepo scaffold + docker-compose + CI.
3. Source/seed a realistic sample sales dataset (`data/samples/`) — consider M5/Walmart-style or synthetic kirana data.
4. Create the first micro-issues for Phase 0 and Phase 1.

## Notes / gotchas
- MAPE is misleading on intermittent (zero-heavy) demand — never select models on it.
- Expect naive baselines to win for some SKUs; that's correct, keep them as permanent benchmark.
- M5 evidence: LightGBM global model beats deep learning on this data shape — don't reach for N-BEATS/TFT early.
