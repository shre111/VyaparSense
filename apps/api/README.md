# apps/api — VyaparSense backend

Python + FastAPI. Owns the data + ML domain: ingest, jobs, forecasts, replenishment, custom auth, multi-tenancy.

Imports the `packages/ml` library for forecasting/replenishment logic. Persists to Postgres; queues forecast/backtest jobs via Redis (see [ADR-007](../../decisions.md)).

Custom auth: Argon2id + JWT access + rotating refresh cookies (see [ADR-006](../../decisions.md)).

Scaffolded in Phase 1. Until then this is a placeholder.
