"""Tests for the accuracy-over-time service and endpoint."""

from __future__ import annotations

import datetime as dt
import math

from app.accuracy import accuracy_over_time
from app.models import Forecast, SalesRecordRow, Tenant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

# --- pure service tests -----------------------------------------------------


def test_accuracy_over_time_pools_wape_per_week() -> None:
    wk1 = dt.datetime(2024, 1, 3)  # ISO 2024-W01
    wk2 = dt.datetime(2024, 1, 10)  # ISO 2024-W02
    pairs = [
        # week 1: actuals [10, 20], preds [12, 18] -> |err| 2+2=4, sum|y|=30 -> 0.1333
        (wk1, 12.0, 10.0),
        (wk1, 18.0, 20.0),
        # week 2: perfect
        (wk2, 5.0, 5.0),
    ]
    points = accuracy_over_time(pairs)
    assert [p.period for p in points] == ["2024-W01", "2024-W02"]
    assert points[0].n == 2
    assert points[0].wape == 0.4 / 3  # 4/30
    assert points[1].wape == 0.0


def test_accuracy_over_time_sorted_chronologically() -> None:
    early = dt.datetime(2024, 1, 3)
    late = dt.datetime(2024, 2, 14)
    pairs = [(late, 5.0, 4.0), (early, 5.0, 4.0)]
    periods = [p.period for p in accuracy_over_time(pairs)]
    assert periods == sorted(periods)


def test_accuracy_over_time_zero_actuals_is_inf() -> None:
    pairs = [(dt.datetime(2024, 1, 3), 3.0, 0.0)]  # actual 0, pred 3 -> inf
    pt = accuracy_over_time(pairs)[0]
    assert math.isinf(pt.wape)


def test_accuracy_over_time_empty() -> None:
    assert accuracy_over_time([]) == []


# --- endpoint tests ---------------------------------------------------------


def _seed(
    session_factory: sessionmaker[Session],
    *,
    tenant: str,
    forecasts: list[tuple[dt.datetime, dt.date, float]],
    actuals: list[tuple[dt.date, int]],
    store: str = "S1",
    sku: str = "K1",
) -> None:
    s = session_factory()
    try:
        s.add(Tenant(id=tenant, name=tenant))
        for created_at, horizon_date, pred in forecasts:
            s.add(
                Forecast(
                    tenant_id=tenant,
                    store_id=store,
                    sku_id=sku,
                    model="naive",
                    horizon_date=horizon_date,
                    predicted_units=pred,
                    quantile=None,
                    created_at=created_at,
                )
            )
        for date, units in actuals:
            s.add(
                SalesRecordRow(
                    tenant_id=tenant,
                    upload_id=1,
                    date=date,
                    store_id=store,
                    sku_id=sku,
                    units_sold=units,
                    price=10.0,
                    promo_flag=False,
                )
            )
        s.commit()
    finally:
        s.close()


def test_accuracy_endpoint_joins_forecasts_to_actuals(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    d = dt.date(2024, 1, 8)
    _seed(
        session_factory,
        tenant="acme",
        forecasts=[(dt.datetime(2024, 1, 1), d, 12.0)],  # predicted 12 for Jan 8
        actuals=[(d, 10)],  # realised 10
    )
    resp = client.get("/tenants/acme/accuracy")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["n"] == 1
    assert body[0]["wape"] == 0.2  # |12-10|/10


def test_accuracy_endpoint_skips_unrealised_forecasts(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # forecast for a date with no matching actual -> not counted
    _seed(
        session_factory,
        tenant="acme",
        forecasts=[(dt.datetime(2024, 1, 1), dt.date(2024, 1, 8), 12.0)],
        actuals=[(dt.date(2024, 1, 9), 10)],  # different date
    )
    resp = client.get("/tenants/acme/accuracy")
    assert resp.status_code == 200
    assert resp.json() == []


def test_accuracy_endpoint_zero_actual_returns_null_wape(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    d = dt.date(2024, 1, 8)
    _seed(
        session_factory,
        tenant="acme",
        forecasts=[(dt.datetime(2024, 1, 1), d, 3.0)],
        actuals=[(d, 0)],  # zero actual -> WAPE undefined -> null
    )
    body = client.get("/tenants/acme/accuracy").json()
    assert len(body) == 1
    assert body[0]["wape"] is None


def test_accuracy_endpoint_empty_for_new_tenant(client: TestClient) -> None:
    assert client.get("/tenants/nobody/accuracy").json() == []
