# Deploying VyaparSense

Three deployables: the **web** (Next.js, static-friendly), the **API** (FastAPI),
and the **worker** (RQ) — the API and worker share one Docker image
([`apps/api/Dockerfile`](../apps/api/Dockerfile)). Backing services: **Postgres**
and **Redis**.

Reference targets (cost-first; ADR-003): web → Vercel, API + worker → Render /
Fly / Railway, DB → Neon / Supabase, Redis → the platform's managed Redis.

## 1. Provision backing services

- **Postgres** (Neon/Supabase) → gives a `DATABASE_URL`. Use the
  `postgresql+psycopg://…` driver prefix.
- **Redis** (managed) → gives a `REDIS_URL`.

## 2. Environment

Set these on the API and worker services (see [`.env.example`](../.env.example)):

| var | notes |
|---|---|
| `DATABASE_URL` | Postgres, `postgresql+psycopg://…` |
| `REDIS_URL` | managed Redis |
| `AUTH_SECRET` | **generate a strong random value** (e.g. `python -c "import secrets;print(secrets.token_urlsafe(48))"`) |
| `CORS_ALLOW_ORIGINS` | the deployed web origin(s), e.g. `https://vyaparsense.com` |
| `FORECAST_QUEUE` | `redis` (so jobs go to the worker, not in-process) |
| `API_ENV` | `production` |
| `LOG_LEVEL` | `INFO` |

On the **web** (Vercel): `NEXT_PUBLIC_API_BASE_URL` = the deployed API URL.

## 3. Build & run the API image

From the repo root:

```bash
docker build -f apps/api/Dockerfile -t vyaparsense-api .

# API
docker run -p 8000:8000 --env-file .env vyaparsense-api
# worker (same image, different command)
docker run --env-file .env vyaparsense-api rq worker forecasts --url "$REDIS_URL"
```

Run **migrations** as a release / pre-deploy step (not on every container start):

```bash
docker run --env-file .env vyaparsense-api alembic upgrade head
```

## 4. Example: Render (`render.yaml`)

A starting point — adapt to your platform. Secrets are set in the dashboard, not
committed.

```yaml
services:
  - type: web
    name: vyaparsense-api
    runtime: docker
    dockerfilePath: apps/api/Dockerfile
    dockerContext: .
    preDeployCommand: alembic upgrade head
    envVars:
      - key: FORECAST_QUEUE
        value: redis
      - key: API_ENV
        value: production
      # DATABASE_URL, REDIS_URL, AUTH_SECRET, CORS_ALLOW_ORIGINS set in dashboard

  - type: worker
    name: vyaparsense-worker
    runtime: docker
    dockerfilePath: apps/api/Dockerfile
    dockerContext: .
    dockerCommand: rq worker forecasts --url "$REDIS_URL"
    envVars:
      - key: FORECAST_QUEUE
        value: redis
```

## 5. Web (Vercel)

Point Vercel at `apps/web`, set `NEXT_PUBLIC_API_BASE_URL`, deploy. Set the API's
`CORS_ALLOW_ORIGINS` to the resulting web origin.

## Pre-launch checklist

- [ ] `AUTH_SECRET` is a strong, unique secret (never the dev default)
- [ ] `CORS_ALLOW_ORIGINS` is the real web origin (credentialed CORS — no wildcard)
- [ ] `FORECAST_QUEUE=redis` and the worker is running
- [ ] migrations applied (`alembic upgrade head`)
- [ ] cookies are `Secure` (the refresh cookie is already non-dev `Secure`)
- [ ] **auth security review done** — CSRF, rate limiting, RLS, secret handling
      (ADR-006); still has open items (CSRF, RLS, email verification)

> The Dockerfile is provided for deployment; build it in your CI/platform to
> verify against your base image and pinned wheels.
