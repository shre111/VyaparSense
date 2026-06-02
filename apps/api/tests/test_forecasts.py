"""Forecast endpoint tests: generation, read-back, filtering, tenant isolation."""

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


def test_generate_forecasts_creates_rows(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    resp = client.post("/tenants/acme/forecasts?horizon=7")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tenant_id"] == "acme"
    assert body["horizon"] == 7
    assert body["series_forecast"] == 1
    assert body["forecasts_created"] == 7  # 1 series x 7 days


def test_generated_forecasts_read_back(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    client.post("/tenants/acme/forecasts?horizon=7")
    resp = client.get("/tenants/acme/forecasts")
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


def test_horizon_param_controls_count(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    resp = client.post("/tenants/acme/forecasts?horizon=14")
    assert resp.json()["forecasts_created"] == 14


def test_short_series_are_skipped(client: TestClient) -> None:
    # only 10 days of history -> too short for a backtest fold -> no forecasts
    client.post("/tenants/acme/uploads", files=_csv(_history_csv(days=10)))
    resp = client.post("/tenants/acme/forecasts?horizon=7")
    assert resp.status_code == 200
    assert resp.json()["forecasts_created"] == 0


def test_no_sales_yields_no_forecasts(client: TestClient) -> None:
    resp = client.post("/tenants/empty/forecasts")
    assert resp.status_code == 200
    assert resp.json()["forecasts_created"] == 0
    assert client.get("/tenants/empty/forecasts").json() == []


def test_filter_by_series(client: TestClient) -> None:
    csv_two = _history_csv(store="S1", sku="K1") + _history_csv(store="S1", sku="K2").replace(
        _HEADER, ""
    )
    client.post("/tenants/acme/uploads", files=_csv(csv_two))
    client.post("/tenants/acme/forecasts?horizon=7")
    resp = client.get("/tenants/acme/forecasts?store_id=S1&sku_id=K2")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 7
    assert all(i["sku_id"] == "K2" for i in items)


def test_invalid_horizon_rejected(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    assert client.post("/tenants/acme/forecasts?horizon=0").status_code == 422
    assert client.post("/tenants/acme/forecasts?horizon=999").status_code == 422


def test_forecast_tenant_isolation(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    client.post("/tenants/acme/forecasts?horizon=7")
    # another tenant has no forecasts
    assert client.get("/tenants/other/forecasts").json() == []


def test_as_of_dates_forecasts_from_cutoff(client: TestClient) -> None:
    # history spans 2024-01-01 .. 2024-02-29 (60 days). Forecast as of 2024-02-10
    # (keeps 41 days >= min_train 28 + horizon 7) -> horizon dates 2024-02-11..17,
    # all of which already have actuals.
    client.post("/tenants/acme/uploads", files=_csv(_history_csv(days=60)))
    resp = client.post("/tenants/acme/forecasts?horizon=7&as_of=2024-02-10")
    assert resp.status_code == 200, resp.text
    assert resp.json()["forecasts_created"] == 7
    items = client.get("/tenants/acme/forecasts").json()
    dates = sorted(i["horizon_date"] for i in items)
    assert dates[0] == "2024-02-11"
    assert dates[-1] == "2024-02-17"


def test_as_of_backfill_populates_accuracy(client: TestClient) -> None:
    # generating forecasts at a past cutoff yields horizon dates with realised
    # actuals, so the accuracy endpoint reports a non-empty curve.
    client.post("/tenants/acme/uploads", files=_csv(_history_csv(days=60)))
    client.post("/tenants/acme/forecasts?horizon=7&as_of=2024-02-10")
    acc = client.get("/tenants/acme/accuracy").json()
    assert len(acc) >= 1
    assert all(pt["n"] >= 1 for pt in acc)


def test_invalid_as_of_rejected(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    assert client.post("/tenants/acme/forecasts?as_of=not-a-date").status_code == 422
