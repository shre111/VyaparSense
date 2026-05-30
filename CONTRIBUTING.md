# Contributing to VyaparSense

This project values **thorough planning, small reviewable units, and clean history**. Read this before opening an issue or PR.

## Workflow at a glance

1. **Micro-issue** → 2. **branch** → 3. **micro-PR** (`Closes #N`) → 4. **green CI + review** → 5. **squash merge**.

Keep each issue and PR to a single concern. Smaller is better.

## Branch naming

| Prefix | Use for |
|---|---|
| `feat/` | new functionality |
| `fix/` | bug fixes |
| `chore/` | tooling, config, deps, scaffolding |
| `docs/` | documentation only |
| `refactor/` | behavior-preserving changes |
| `test/` | tests only |

Format: `feat/<area>-<short-slug>` — e.g. `feat/ml-naive-baselines`, `fix/api-csv-validation`.

## Commits — Conventional Commits

```
<type>(<optional-scope>): <short imperative summary>
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`.

**Rules (strict):**
- **Single line only. No commit body/description.**
- **No `Co-Authored-By` trailers. No "Generated with" lines.**
- Imperative mood, lowercase summary, no trailing period.

Examples: `feat(ml): add seasonal-naive baseline`, `fix(api): guard MAPE against zero demand`, `chore: scaffold monorepo and CI`.

## Pull requests

- Link the issue (`Closes #N`).
- Fill in the PR template: what & why, test evidence, checklist.
- Keep diffs small; split large work into stacked PRs.
- CI must be green (lint + typecheck + tests) before merge.
- Squash-merge so the PR maps to one clean Conventional Commit.

## ML changes — extra rules

- No accuracy claim without a **backtest on a fixed holdout** — paste the metric move (WAPE/MASE) in the PR.
- Select models **per-SKU by backtest**, not by intuition. A naive model winning is a valid result.
- Never optimize on MAPE for intermittent demand (zeros break it). WAPE is primary; MASE for intermittent.
- Record a **model card** under `docs/model-cards/` for each training run (data hash, features, params, metrics).

## Local checks before pushing

```bash
make lint     # ruff + eslint
make typecheck
make test
```

## Security

Never commit secrets, `.env`, or real customer data. Sample data only under `data/samples/`. Auth/security-sensitive code needs an extra reviewer.
