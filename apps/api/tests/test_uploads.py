"""Upload endpoint tests. Endpoints are tenant-scoped via the access token."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

_HEADER = "date,store_id,sku_id,units_sold,price,promo_flag\n"
_ROWS = (
    "2024-01-01,S1,K1,5,10.0,1\n"
    "2024-01-03,S1,K1,3,10.0,0\n"  # gap on 01-02 -> filled with zero by cleaning
    "2024-01-01,S1,K2,0,50.0,0\n"
)


def _csv(content: str) -> dict[str, Any]:
    return {"file": ("sales.csv", content.encode("utf-8"), "text/csv")}


def test_upload_stores_records(auth_client: TestClient) -> None:
    resp = auth_client.post("/uploads", files=_csv(_HEADER + _ROWS))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tenant_id"] == "acme"
    assert body["series_count"] == 2  # (S1,K1) and (S1,K2)
    # K1 series spans 01-01..01-03 = 3 days after gap-fill; K2 = 1 day -> 4 rows
    assert body["row_count"] == 4
    assert sum(body["patterns"].values()) == 2


def test_upload_lists_back(auth_client: TestClient) -> None:
    auth_client.post("/uploads", files=_csv(_HEADER + _ROWS))
    resp = auth_client.get("/uploads")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["row_count"] == 4


def test_empty_file_rejected(auth_client: TestClient) -> None:
    resp = auth_client.post("/uploads", files=_csv(""))
    assert resp.status_code == 422


def test_missing_column_rejected(auth_client: TestClient) -> None:
    bad = "date,store_id,sku_id,units_sold,price\n2024-01-01,S1,K1,5,10.0\n"
    resp = auth_client.post("/uploads", files=_csv(bad))
    assert resp.status_code == 422


def test_bad_row_rejected(auth_client: TestClient) -> None:
    bad = _HEADER + "2024-01-01,S1,K1,-5,10.0,0\n"
    resp = auth_client.post("/uploads", files=_csv(bad))
    assert resp.status_code == 422


def test_upload_requires_auth(client: TestClient) -> None:
    # no Authorization header -> 401
    resp = client.post("/uploads", files=_csv(_HEADER + _ROWS))
    assert resp.status_code == 401
    assert client.get("/uploads").status_code == 401
