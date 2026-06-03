"""Async forecast-job runner (ADR-007).

A forecast job loads a tenant's stored sales, generates forecasts, persists them
(append-only, ADR-008), and records progress on the ``forecast_jobs`` row so the
client can poll for status. This is the *task body*; the transport that calls it
is pluggable:

* now — FastAPI ``BackgroundTasks`` (runs in-process after the response). Keeps
  the async API contract without a Redis dependency yet.
* next — a Redis-backed worker process (arq/RQ) calls this same function.

Because the task outlives the request, it opens its own session from the passed
factory rather than reusing the request's (already-closed) session.
"""

from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app import repository
from app.forecasting import generate_forecasts


def run_forecast_job(session_factory: sessionmaker[Session], job_id: int) -> None:
    """Run the forecast job ``job_id`` to completion (or record its failure).

    Marks the job ``running``, generates + stores forecasts for its tenant, then
    marks it ``completed`` with the produced counts. Any error is caught and
    recorded on the job as ``failed`` so a poller always sees a terminal state.
    """
    session = session_factory()
    try:
        job = repository.get_forecast_job_by_id(session, job_id)
        if job is None:
            return
        repository.mark_forecast_job_running(session, job)
        try:
            series = repository.load_series(session, job.tenant_id)
            rows = generate_forecasts(series, horizon=job.horizon, as_of=job.as_of)
            created = repository.store_forecasts(session, job.tenant_id, rows)
            series_forecast = len({(r.store_id, r.sku_id) for r in rows})
            repository.complete_forecast_job(
                session, job, series_forecast=series_forecast, forecasts_created=created
            )
        except Exception as exc:  # record any failure as terminal job state
            session.rollback()
            repository.fail_forecast_job(session, job, str(exc))
    finally:
        session.close()
