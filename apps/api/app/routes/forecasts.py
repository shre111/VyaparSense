"""Forecast endpoints: generate per-series forecasts and read them back.

``POST`` runs baseline selection over the tenant's stored sales and appends the
resulting forecasts (ADR-008, insert-only). ``GET`` reads them back, newest
first, optionally filtered to one ``(store, sku)`` series.

Generation runs synchronously here using the fast stdlib baselines. Heavier
models (classical / global LightGBM) move to the async worker per ADR-007.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Annotated

from fastapi import APIRouter, Query

from app import repository
from app.accuracy import accuracy_over_time
from app.deps import CurrentTenant, SessionDep
from app.forecasting import generate_forecasts
from app.schemas import AccuracyPointItem, ForecastItem, ForecastRunSummary

router = APIRouter(tags=["forecasts"])


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
