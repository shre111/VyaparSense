"""Tests for the reorder-suggestion and simulation-KPI endpoints."""

from __future__ import annotations

import datetime as dt
from typing import Any

from fastapi.testclient import TestClient

_HEADER = "date,store_id,sku_id,units_sold,price,promo_flag\n"


def _csv(content: str) -> dict[str, Any]:
    return {"file": ("sales.csv", content.encode("utf-8"), "text/csv")}


def _history_csv(days: int = 90, store: str = "S1", sku: str = "K1") -> str:
    start = dt.date(2024, 1, 1)
    weekly = [8, 9, 7, 10, 12, 20, 18]
    rows = [
        f"{(start + dt.timedelta(days=i)).isoformat()},{store},{sku},{weekly[i % 7]},10.0,0\n"
        for i in range(days)
    ]
    return _HEADER + "".join(rows)


# --- reorder suggestions ----------------------------------------------------


def test_reorder_suggestions_returns_rows(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    resp = client.get("/tenants/acme/reorder-suggestions?lead_time_days=7&service_level=0.95")
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["store_id"] == "S1"
    assert row["sku_id"] == "K1"
    assert row["service_level"] == 0.95
    assert row["lead_time_days"] == 7
    assert row["reorder_point"] >= 0.0
    assert row["safety_stock"] >= 0.0
    # on_hand defaults to 0 -> definitely below reorder point -> should reorder
    assert row["should_reorder"] is True
    assert row["order_quantity"] > 0.0


def test_reorder_higher_service_level_raises_reorder_point(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    low = client.get("/tenants/acme/reorder-suggestions?lead_time_days=7&service_level=0.80")
    high = client.get("/tenants/acme/reorder-suggestions?lead_time_days=7&service_level=0.99")
    assert low.json()[0]["reorder_point"] <= high.json()[0]["reorder_point"]


def test_reorder_on_hand_param_flips_should_reorder(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    huge = client.get("/tenants/acme/reorder-suggestions?lead_time_days=7&on_hand=100000")
    assert huge.json()[0]["should_reorder"] is False
    assert huge.json()[0]["order_quantity"] == 0.0


def test_reorder_skips_short_series(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv(days=5)))
    resp = client.get("/tenants/acme/reorder-suggestions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_reorder_invalid_params_rejected(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    assert client.get("/tenants/acme/reorder-suggestions?lead_time_days=0").status_code == 422
    assert client.get("/tenants/acme/reorder-suggestions?service_level=1.5").status_code == 422


def test_reorder_empty_tenant(client: TestClient) -> None:
    assert client.get("/tenants/nobody/reorder-suggestions").json() == []


# --- simulation KPIs --------------------------------------------------------


def test_simulation_kpis_forecast_beats_naive(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv(days=120)))
    resp = client.get("/tenants/acme/simulation-kpis?lead_time_days=7&service_level=0.95")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["series_simulated"] == 1
    # forecast-driven (with safety stock) should not lose more than naive
    assert body["forecast_units_lost"] <= body["naive_units_lost"]
    assert body["forecast_fill_rate"] >= body["naive_fill_rate"]
    assert 0.0 <= body["lost_sales_reduction_pct"] <= 1.0


def test_simulation_kpis_empty_tenant(client: TestClient) -> None:
    resp = client.get("/tenants/nobody/simulation-kpis")
    assert resp.status_code == 200
    body = resp.json()
    assert body["series_simulated"] == 0
    assert body["naive_fill_rate"] == 1.0  # no demand -> trivially filled
    assert body["lost_sales_reduction_pct"] == 0.0


def test_simulation_kpis_invalid_params_rejected(client: TestClient) -> None:
    client.post("/tenants/acme/uploads", files=_csv(_history_csv()))
    assert client.get("/tenants/acme/simulation-kpis?lead_time_days=0").status_code == 422
    assert client.get("/tenants/acme/simulation-kpis?service_level=0").status_code == 422
