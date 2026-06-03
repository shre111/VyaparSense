"""Forecast endpoints: generate per-series forecasts and read them back.

``POST /forecasts`` runs baseline selection over the tenant's stored sales and
appends the resulting forecasts (ADR-008, insert-only), synchronously, using the
fast stdlib baselines. ``GET`` reads them back, newest first, optionally filtered
to one ``(store, sku)`` series.

``POST /forecast-jobs`` is the async path (ADR-007): it enqueues the same work as
a background job and returns immediately with a job id to poll via
``GET /forecast-jobs/{id}``. This is where heavier models (classical / global
LightGBM) will run without blocking the request; today it runs the baselines via
``BackgroundTasks`` (the Redis-backed worker swaps in next).
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app import repository
from app.accuracy import accuracy_over_time
from app.config import get_settings
from app.deps import CurrentTenant, SessionDep, SessionFactoryDep
from app.forecasting import generate_forecasts
from app.jobs import run_forecast_job
from app.models import ForecastJob
from app.schemas import (
    AccuracyPointItem,
    ForecastItem,
    ForecastJobStatus,
    ForecastRunSummary,
)
from app.task_queue import enqueue_forecast_job

router = APIRouter(tags=["forecasts"])


def _job_status(job: ForecastJob) -> ForecastJobStatus:
    return ForecastJobStatus(
        job_id=job.id,
        status=job.status,
        horizon=job.horizon,
        as_of=job.as_of,
        series_forecast=job.series_forecast,
        forecasts_created=job.forecasts_created,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/forecasts", response_model=ForecastRunSummary)
def create_forecasts(
    session: SessionDep,
    tenant_id: CurrentTenant,
    horizon: Annotated[int, Query(ge=1, le=90)] = 7,
    as_of: Annotated[dt.date | None, Query()] = None,
) -> ForecastRunSummary:
    """Generate and persist ``horizon``-day forecasts for the tenant's series.

    With ``as_of`` (a past date), each series is truncated to that cutoff and
    forecasts run forward from it — so their horizon dates fall on days that
    already have realised actuals. Generating across several ``as_of`` cutoffs
    backfills the accuracy-over-time history.
    """
    series = repository.load_series(session, tenant_id)
    rows = generate_forecasts(series, horizon=horizon, as_of=as_of)
    created = repository.store_forecasts(session, tenant_id, rows)
    series_forecast = len({(r.store_id, r.sku_id) for r in rows})
    return ForecastRunSummary(
        tenant_id=tenant_id,
        horizon=horizon,
        series_forecast=series_forecast,
        forecasts_created=created,
    )


@router.post("/forecast-jobs", response_model=ForecastJobStatus, status_code=202)
def create_forecast_job(
    session: SessionDep,
    session_factory: SessionFactoryDep,
    tenant_id: CurrentTenant,
    background_tasks: BackgroundTasks,
    horizon: Annotated[int, Query(ge=1, le=90)] = 7,
    as_of: Annotated[dt.date | None, Query()] = None,
) -> ForecastJobStatus:
    """Enqueue an async forecast job (ADR-007) and return it as ``queued``.

    The work runs in the background; poll ``GET /forecast-jobs/{id}`` until the
    status is ``completed`` (then read ``GET /forecasts``) or ``failed``.

    Transport is chosen by the ``forecast_queue`` setting (ADR-011): ``redis``
    hands the job to an RQ worker; ``inline`` (default) runs it in-process via
    ``BackgroundTasks`` so dev/CI need no Redis.
    """
    job = repository.create_forecast_job(session, tenant_id=tenant_id, horizon=horizon, as_of=as_of)
    if get_settings().forecast_queue == "redis":
        enqueue_forecast_job(job.id)
    else:
        background_tasks.add_task(run_forecast_job, session_factory, job.id)
    return _job_status(job)


@router.get("/forecast-jobs/{job_id}", response_model=ForecastJobStatus)
def get_forecast_job(
    session: SessionDep,
    tenant_id: CurrentTenant,
    job_id: int,
) -> ForecastJobStatus:
    """Poll one async forecast job's status (scoped to the authenticated tenant)."""
    job = repository.get_forecast_job(session, tenant_id, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="forecast job not found")
    return _job_status(job)


@router.get("/forecasts", response_model=list[ForecastItem])
def get_forecasts(
    session: SessionDep,
    tenant_id: CurrentTenant,
    store_id: Annotated[str | None, Query()] = None,
    sku_id: Annotated[str | None, Query()] = None,
) -> list[ForecastItem]:
    """List the tenant's forecasts, newest first, optionally filtered by series."""
    return [
        ForecastItem(
            store_id=f.store_id,
            sku_id=f.sku_id,
            model=f.model,
            horizon_date=f.horizon_date,
            predicted_units=f.predicted_units,
        )
        for f in repository.list_forecasts(session, tenant_id, store_id=store_id, sku_id=sku_id)
    ]


@router.get("/accuracy", response_model=list[AccuracyPointItem])
def get_accuracy(session: SessionDep, tenant_id: CurrentTenant) -> list[AccuracyPointItem]:
    """Rolling WAPE by forecast-run week — the "getting smarter" chart data.

    Joins the tenant's past point forecasts to realised actuals and pools WAPE
    per ISO week the forecast was made, oldest first. Undefined WAPE (a period
    with zero actual demand) is returned as ``null``.
    """
    pairs = repository.forecast_actual_pairs(session, tenant_id)
    return [
        AccuracyPointItem(
            period=pt.period,
            n=pt.n,
            wape=None if math.isinf(pt.wape) else pt.wape,
        )
        for pt in accuracy_over_time(pairs)
    ]
