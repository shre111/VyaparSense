# infra — local & deployment

- `docker-compose.yml` — local Postgres + Redis (+ api/web later).
- Migrations live with the API (Alembic).
- Deployment targets: Vercel (web), Render/Railway/Fly (api + worker), Neon/Supabase (db), S3/R2 (storage).

Added in Phase 0/1.
