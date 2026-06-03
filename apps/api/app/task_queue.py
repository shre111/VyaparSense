"""RQ wiring for async forecast jobs (ADR-007 / ADR-011).

Two sides of one queue:

* **producer** — :func:`enqueue_forecast_job` is called from the request path
  (sync, no event loop — that's why RQ over Arq) to hand a job id to Redis.
* **consumer** — :func:`run_forecast_job_task` is the callable the ``rq worker``
  process runs; it opens its own DB session and delegates to the transport-
  agnostic runner in :mod:`app.jobs`.

The inline fallback (FastAPI ``BackgroundTasks``) lives in the route and does not
touch this module, so dev/CI need no Redis.

Run a worker (deploys; needs Redis):

    cd apps/api && rq worker forecasts --url "$REDIS_URL"
"""

from __future__ import annotations

from redis import Redis
from rq import Queue

from app.config import get_settings
from app.db import SessionLocal
from app.jobs import run_forecast_job

#: Single named queue for forecast jobs; the worker listens on this name.
FORECAST_QUEUE = "forecasts"


def get_queue() -> Queue:
    """The RQ queue bound to a Redis connection from settings."""
    return Queue(FORECAST_QUEUE, connection=Redis.from_url(get_settings().redis_url))


def enqueue_forecast_job(job_id: int) -> None:
    """Hand a forecast job off to the worker (producer side)."""
    get_queue().enqueue(run_forecast_job_task, job_id)


def run_forecast_job_task(job_id: int) -> None:
    """Worker entrypoint: run the job with a fresh session (consumer side)."""
    run_forecast_job(SessionLocal, job_id)
