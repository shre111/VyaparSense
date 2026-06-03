# infra — local & deployment

- `docker-compose.yml` — local Postgres + Redis (+ api/web later).
- Migrations live with the API (Alembic).
- Deployment targets: Vercel (web), Render/Railway/Fly (api + worker), Neon/Supabase (db), S3/R2 (storage).

Added in Phase 0/1.

## Async forecast jobs (ADR-007 / ADR-011)

Forecasting is an async job. The transport is chosen by the `forecast_queue` setting:

- `inline` (default) — runs in-process via FastAPI `BackgroundTasks`. No Redis
  needed; used for local dev and CI.
- `redis` — enqueues to an **RQ** worker over Redis (deployments).

To run the worker locally against the compose Redis (Linux/WSL — RQ workers fork,
so not native Windows):

```bash
docker compose -f infra/docker-compose.yml up -d redis
cd apps/api
export FORECAST_QUEUE=redis            # so the API enqueues instead of running inline
rq worker forecasts --url redis://localhost:6379/0
```

The worker runs `app.task_queue.run_forecast_job_task`; deploy it as a separate
process alongside the API (same image/deps).
