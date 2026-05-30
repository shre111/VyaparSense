# Decisions (ADRs)

Architecture Decision Records. Each entry: context → decision → consequences. Newest decisions appended; supersede rather than delete. Status: `Proposed` | `Accepted` | `Superseded`.

---

## ADR-001 — Product name & positioning
**Status:** Accepted
**Context:** Need a brand that works for both Indian kirana retail and global SMB/D2C.
**Decision:** Brand is **VyaparSense** (व्यापार *vyapar* = business/trade + *Sense* = demand-sensing). Domain **vyaparsense.com**. Repo codename remains `kirana-demand`. Keep core ML/`packages` code brand-neutral; brand lives in `apps/web` and marketing.
**Consequences:** India-rooted but globally pronounceable; "Sense" signals the AI/forecasting value. Use VyaparSense in all user-facing copy.

## ADR-002 — Monorepo vs. polyrepo
**Status:** Accepted
**Context:** TS frontend + Python backend + Python ML lib. Want atomic cross-cutting changes and one CI.
**Decision:** Single monorepo. `apps/web` (Next.js), `apps/api` (FastAPI), `packages/ml` (Python lib). Use npm/pnpm workspaces for JS and a `uv`/`poetry` project for Python; keep Python and JS dependency trees separate. No heavyweight monorepo tool (Nx/Turbo) until it earns its place.
**Consequences:** Simple now; revisit Turborepo if web build caching becomes a pain.

## ADR-003 — Service boundary: Next.js never touches ML data DB directly
**Status:** Accepted
**Context:** Tempting to use Next.js server actions for everything.
**Decision:** All forecasting/inventory/data logic lives behind FastAPI. Next.js handles UI, session, and calls the API. Python owns the data + ML domain.
**Consequences:** Clean separation, independently deployable, ML reusable headless. Slight cost: two services to run/deploy.

## ADR-004 — ML library strategy: classical baselines + Nixtla + LightGBM
**Status:** Accepted
**Context:** Need credible, fast, well-supported forecasting; M5 evidence favors gradient boosting + global models; intermittent demand needs specialized methods.
**Decision:**
- Baselines & classical/intermittent: Nixtla `statsforecast` (naive, seasonal naive, ETS, ARIMA, Croston, SBA, TSB, ADIDA).
- Primary ML: LightGBM global model (recursive multi-step) with calendar/price/promo/lag features.
- Hierarchical reconciliation: Nixtla `hierarchicalforecast`.
- Avoid heavy deep-learning (N-BEATS/TFT) until tabular GBM is exhausted — M5 showed GBM wins on this data shape and it's far cheaper to run.
**Consequences:** Cheap, fast, strong baselines; the "ladder" is real and each rung is library-supported. Deep learning remains a later, optional flex.

## ADR-005 — Metrics: WAPE primary, MASE for intermittent, MAPE for display only
**Status:** Accepted
**Context:** MAPE is intuitive but explodes on zero/near-zero demand, which dominates retail SKUs.
**Decision:** WAPE is the primary optimization/reporting metric. MASE/RMSSE for intermittent series. MAPE shown to users (with safe handling) because it's intuitive, never used as the sole selection criterion. Always track bias.
**Consequences:** Honest accuracy story; the public "getting smarter" chart uses rolling WAPE.

## ADR-006 — Auth & multi-tenancy
**Status:** Accepted
**Context:** SaaS needs per-tenant isolation from day one. User wants a **custom auth solution**, no third-party (no Clerk/Auth0/Auth.js).
**Decision:** Build custom auth in FastAPI: email+password with **Argon2id** hashing, short-lived **JWT access tokens** + rotating **refresh tokens** stored as httpOnly secure cookies, refresh-token rotation + reuse detection, email verification + password reset flows. `tenant_id` scoping enforced in API middleware + Postgres (row-level isolation). Plan for 2FA (TOTP) and OAuth social login as later, optional additions.
**Consequences:** More code & security responsibility on us — must be careful (rate limiting, secure cookie flags, CSRF protection for cookie auth, secret rotation). Full control, no vendor lock-in, no per-MAU cost. Every table carries `tenant_id`; every query tenant-scoped. Security review required before launch.

## ADR-007 — Async forecast jobs, not request-time
**Status:** Accepted
**Context:** Backtests/training over many SKUs are too slow for an HTTP request.
**Decision:** Upload → enqueue job (Redis + worker) → poll/websocket for status → store results. Forecasts and backtests are jobs; reads are fast API calls against stored results.
**Consequences:** Need a worker process and job-status UX. Scales cleanly.

## ADR-008 — Data model is append-only & auditable for the flywheel
**Status:** Accepted
**Context:** The "getting smarter" story requires reconstructing historical forecast-vs-actual.
**Decision:** Persist every forecast (model, params, horizon, timestamp) and later join to realized actuals. Never overwrite past forecasts. Store model cards per training run.
**Consequences:** Slightly more storage; enables trustworthy accuracy-over-time charts and debugging.

## ADR-009 — Git/PR conventions
**Status:** Accepted
**Context:** User is a thorough planner wanting micro-issues/PRs and clean conventions.
**Decision:** Conventional Commits; typed branches (`feat/`,`fix/`,`chore/`,`docs/`,`refactor/`); micro-issues each linked to a micro-PR (`Closes #N`); CI gates (lint+typecheck+test). **Commit messages are single-line only — no body, no `Co-Authored-By`, no generated-by trailers.**
**Consequences:** Clean, reviewable history that doubles as portfolio evidence of engineering discipline.

## ADR-010 — Pricing & GTM shape
**Status:** Proposed
**Context:** Two segments (India kirana vs. global D2C/SMB) have very different willingness-to-pay.
**Decision (leaning):** Freemium + tiered SaaS. Free: 1 store, N SKUs, weekly forecasts. Paid: more SKUs/stores, daily forecasts, reorder automation, integrations. India entry pricing low (₹-friendly); global SMB priced in USD against Zoho/inFlow ($29–$299/mo band). See [plan.md](plan.md) business section.
**Consequences:** Land-and-expand; the free tier *is* the data moat (more series → better cold-start).
