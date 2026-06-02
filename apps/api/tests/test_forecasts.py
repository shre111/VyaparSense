"""Forecast endpoint tests. Endpoints are tenant-scoped via the access token."""

from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi.testclient import TestClient

_HEADER = "date,store_id,sku_id,units_sold,price,promo_flag\n"


def _csv(content: str) -> dict[str, Any]:
    return {"file": ("sales.csv", content.encode("utf-8"), "text/csv")}


def _history_csv(days: int = 60, store: str = "S1", sku: str = "K1") -> str:
    """A single series with a clear weekly pattern, long enough to forecast."""
    start = dt.date(2024, 1, 1)
    weekly = [8, 9, 7, 10, 12, 20, 18]
    rows = []
    for i in range(days):
        d = start + dt.timedelta(days=i)
        rows.append(f"{d.isoformat()},{store},{sku},{weekly[i % 7]},10.0,0\n")
    return _HEADER + "".join(rows)


def test_generate_forecasts_creates_rows(auth_client: TestClient) -> None:
    auth_client.post("/uploads", files=_csv(_history_csv()))
    resp = auth_client.post("/forecasts?horizon=7")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tenant_id"] == "acme"
    assert body["horizon"] == 7
    assert body["series_forecast"] == 1
    assert body["forecasts_created"] == 7  # 1 series x 7 days


def test_generated_forecasts_read_back(auth_client: TestClient) -> None:
    auth_client.post("/uploads", files=_csv(_history_csv()))
    auth_client.post("/forecasts?horizon=7")
    resp = auth_client.get("/forecasts")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 7
    first = items[0]
    assert first["store_id"] == "S1"
    assert first["sku_id"] == "K1"
    assert first["predicted_units"] >= 0.0
    assert first["model"] in {"naive", "moving_average_7", "seasonal_naive_7"}
    # horizon dates are the 7 days after the last history date (2024-01-01 + 59 days)
    last_history = dt.date(2024, 1, 1) + dt.timedelta(days=59)
    dates = sorted(i["horizon_date"] for i in items)
    assert dates[0] == (last_history + dt.timedelta(days=1)).isoformat()
    assert dates[-1] == (last_history + dt.timedelta(days=7)).isoformat()


def test_horizon_param_controls_count(auth_client: TestClient) -> None:
    auth_client.post("/uploads", files=_csv(_history_csv()))
    resp = auth_client.post("/forecasts?horizon=14")
    assert resp.json()["forecasts_created"] == 14


def test_short_series_are_skipped(auth_client: TestClient) -> None:
    # only 10 days of history -> too short for a backtest fold -> no forecasts
    auth_client.post("/uploads", files=_csv(_history_csv(days=10)))
    resp = auth_client.post("/forecasts?horizon=7")
    assert resp.status_code == 200
    assert resp.json()["forecasts_created"] == 0


def test_no_sales_yields_no_forecasts(auth_client: TestClient) -> None:
    resp = auth_client.post("/forecasts")
    assert resp.status_code == 200
    assert resp.json()["forecasts_created"] == 0
    assert auth_client.get("/forecasts").json() == []


def test_filter_by_series(auth_client: TestClient) -> None:
    csv_two = _history_csv(store="S1", sku="K1") + _history_csv(store="S1", sku="K2").replace(
        _HEADER, ""
    )
    auth_client.post("/uploads", files=_csv(csv_two))
    auth_client.post("/forecasts?horizon=7")
    resp = auth_client.get("/forecasts?store_id=S1&sku_id=K2")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 7
    assert all(i["sku_id"] == "K2" for i in items)


def test_invalid_horizon_rejected(auth_client: TestClient) -> None:
    auth_client.post("/uploads", files=_csv(_history_csv()))
    assert auth_client.post("/forecasts?horizon=0").status_code == 422
    assert auth_client.post("/forecasts?horizon=999").status_code == 422


def test_forecasts_require_auth(client: TestClient) -> None:
    assert client.post("/forecasts").status_code == 401
    assert client.get("/forecasts").status_code == 401
    assert client.get("/accuracy").status_code == 401


def test_as_of_dates_forecasts_from_cutoff(auth_client: TestClient) -> None:
    # history spans 2024-01-01 .. 2024-02-29 (60 days). Forecast as of 2024-02-10
    # (keeps 41 days >= min_train 28 + horizon 7) -> horizon dates 2024-02-11..17,
    # all of which already have actuals.
    auth_client.post("/uploads", files=_csv(_history_csv(days=60)))
    resp = auth_client.post("/forecasts?horizon=7&as_of=2024-02-10")
    assert resp.status_code == 200, resp.text
    assert resp.json()["forecasts_created"] == 7
    items = auth_client.get("/forecasts").json()
    dates = sorted(i["horizon_date"] for i in items)
    assert dates[0] == "2024-02-11"
    assert dates[-1] == "2024-02-17"


def test_as_of_backfill_populates_accuracy(auth_client: TestClient) -> None:
    # generating forecasts at a past cutoff yields horizon dates with realised
    # actuals, so the accuracy endpoint reports a non-empty curve.
    auth_client.post("/uploads", files=_csv(_history_csv(days=60)))
    auth_client.post("/forecasts?horizon=7&as_of=2024-02-10")
    acc = auth_client.get("/accuracy").json()
    assert len(acc) >= 1
    assert all(pt["n"] >= 1 for pt in acc)


def test_invalid_as_of_rejected(auth_client: TestClient) -> None:
    auth_client.post("/uploads", files=_csv(_history_csv()))
    assert auth_client.post("/forecasts?as_of=not-a-date").status_code == 422
