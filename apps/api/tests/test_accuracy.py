"""Tests for the accuracy-over-time service and endpoint.

Accuracy is bucketed by the ISO week of each forecast's *horizon date* (the day
being predicted), joined to realised actuals on the same (store, sku, date).
"""

from __future__ import annotations

import datetime as dt
import math

from app.accuracy import accuracy_over_time
from app.models import Forecast, SalesRecordRow, Tenant
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

# --- pure service tests -----------------------------------------------------


def test_accuracy_over_time_pools_wape_per_week() -> None:
    wk1a = dt.date(2024, 1, 2)  # ISO 2024-W01
    wk1b = dt.date(2024, 1, 3)  # ISO 2024-W01
    wk2 = dt.date(2024, 1, 10)  # ISO 2024-W02
    pairs = [
        # week 1: actuals [10, 20], preds [12, 18] -> |err| 2+2=4, sum|y|=30 -> 0.1333
        (wk1a, 12.0, 10.0),
        (wk1b, 18.0, 20.0),
        # week 2: perfect
        (wk2, 5.0, 5.0),
    ]
    points = accuracy_over_time(pairs)
    assert [p.period for p in points] == ["2024-W01", "2024-W02"]
    assert points[0].n == 2
    assert points[0].wape == 0.4 / 3  # 4/30
    assert points[1].wape == 0.0


def test_accuracy_over_time_sorted_chronologically() -> None:
    early = dt.date(2024, 1, 3)
    late = dt.date(2024, 2, 14)
    pairs = [(late, 5.0, 4.0), (early, 5.0, 4.0)]
    periods = [p.period for p in accuracy_over_time(pairs)]
    assert periods == sorted(periods)


def test_accuracy_over_time_zero_actuals_is_inf() -> None:
    pairs = [(dt.date(2024, 1, 3), 3.0, 0.0)]  # actual 0, pred 3 -> inf
    pt = accuracy_over_time(pairs)[0]
    assert math.isinf(pt.wape)


def test_accuracy_over_time_empty() -> None:
    assert accuracy_over_time([]) == []


# --- endpoint tests ---------------------------------------------------------


def _seed(
    session_factory: sessionmaker[Session],
    *,
    tenant: str,
    forecasts: list[tuple[dt.date, float]],  # (horizon_date, predicted)
    actuals: list[tuple[dt.date, int]],
    store: str = "S1",
    sku: str = "K1",
) -> None:
    s = session_factory()
    try:
        if s.get(Tenant, tenant) is None:
            s.add(Tenant(id=tenant, name=tenant))
        for horizon_date, pred in forecasts:
            s.add(
                Forecast(
                    tenant_id=tenant,
                    store_id=store,
                    sku_id=sku,
                    model="naive",
                    horizon_date=horizon_date,
                    predicted_units=pred,
                    quantile=None,
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
    auth_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    d = dt.date(2024, 1, 8)
    _seed(
        session_factory,
        tenant="acme",  # matches the auth_client's tenant
        forecasts=[(d, 12.0)],  # predicted 12 for Jan 8
        actuals=[(d, 10)],  # realised 10
    )
    resp = auth_client.get("/accuracy")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["n"] == 1
    assert body[0]["wape"] == 0.2  # |12-10|/10


def test_accuracy_endpoint_skips_unrealised_forecasts(
    auth_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    # forecast for a date with no matching actual -> not counted
    _seed(
        session_factory,
        tenant="acme",
        forecasts=[(dt.date(2024, 1, 8), 12.0)],
        actuals=[(dt.date(2024, 1, 9), 10)],  # different date
    )
    resp = auth_client.get("/accuracy")
    assert resp.status_code == 200
    assert resp.json() == []


def test_accuracy_endpoint_zero_actual_returns_null_wape(
    auth_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    d = dt.date(2024, 1, 8)
    _seed(
        session_factory,
        tenant="acme",
        forecasts=[(d, 3.0)],
        actuals=[(d, 0)],  # zero actual -> WAPE undefined -> null
    )
    body = auth_client.get("/accuracy").json()
    assert len(body) == 1
    assert body[0]["wape"] is None


def test_accuracy_endpoint_empty_for_new_tenant(auth_client: TestClient) -> None:
    assert auth_client.get("/accuracy").json() == []
