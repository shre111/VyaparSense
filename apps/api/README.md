# apps/api — VyaparSense backend

Python + FastAPI. Owns the data + ML domain: ingest, jobs, forecasts, replenishment, custom auth, multi-tenancy.

Imports the `packages/ml` library for forecasting/replenishment logic. Persists to Postgres; queues forecast/backtest jobs via Redis (see [ADR-007](../../decisions.md)).

Custom auth: Argon2id + JWT access + rotating refresh cookies (see [ADR-006](../../decisions.md)).

## Layout
```
app/
  main.py          # FastAPI app + /health
  config.py        # settings (env / .env)
  db.py            # engine, session, Base
  models.py        # SQLAlchemy models (tenant_id everywhere; forecasts append-only)
  repository.py    # tenant-scoped persistence
  schemas.py       # API request/response models
  routes/uploads.py# CSV upload -> ingest/clean/classify -> persist
migrations/        # Alembic (Postgres source of truth)
tests/             # SQLite + TestClient
```

## Develop
```bash
docker compose -f ../../infra/docker-compose.yml up -d   # postgres + redis
pip install -e ../../packages/ml && pip install -e ".[dev]"
alembic upgrade head                                     # apply migrations (Postgres)
uvicorn app.main:app --reload
pytest                                                   # tests use in-memory SQLite
```

## Notes
- Tests run on SQLite for speed; **Alembic migrations against Postgres are the production source of truth**. Models use portable column types so the two stay equivalent.
- Forecasts table exists now (ADR-008) but is populated in later phases.
