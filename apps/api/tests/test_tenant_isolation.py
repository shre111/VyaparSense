"""Cross-tenant isolation: an authed user only ever sees their own tenant's data.

This is the security core of the multi-tenant model (ADR-006) — business data is
scoped to the tenant on the access token, not a URL parameter, so one tenant can
never read another's uploads/forecasts.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

_HEADER = "date,store_id,sku_id,units_sold,price,promo_flag\n"
_ROWS = "2024-01-01,S1,K1,5,10.0,0\n2024-01-02,S1,K1,7,10.0,0\n"


def _csv(content: str) -> dict[str, Any]:
    return {"file": ("sales.csv", content.encode("utf-8"), "text/csv")}


def _token(client: TestClient, tenant_id: str, email: str) -> str:
    resp = client.post(
        "/auth/signup",
        json={"tenant_id": tenant_id, "email": email, "password": "hunter2pw"},
    )
    assert resp.status_code == 201, resp.text
    token: str = resp.json()["access_token"]
    return token


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_uploads_are_isolated_by_tenant(client: TestClient) -> None:
    acme = _token(client, "acme", "a@acme.com")
    globex = _token(client, "globex", "b@globex.com")

    # acme uploads; globex uploads nothing
    r = client.post("/uploads", files=_csv(_HEADER + _ROWS), headers=_bearer(acme))
    assert r.status_code == 200, r.text

    # acme sees its upload; globex sees none — same endpoint, different token
    assert len(client.get("/uploads", headers=_bearer(acme)).json()) == 1
    assert client.get("/uploads", headers=_bearer(globex)).json() == []


def test_one_tenant_cannot_see_anothers_forecasts(client: TestClient) -> None:
    acme = _token(client, "acme", "a@acme.com")
    globex = _token(client, "globex", "b@globex.com")

    # Build enough history for acme to forecast, then generate.
    rows = "".join(
        f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d},S1,K1,{5 + i % 7},10.0,0\n" for i in range(40)
    )
    client.post("/uploads", files=_csv(_HEADER + rows), headers=_bearer(acme))
    client.post("/forecasts?horizon=7", headers=_bearer(acme))

    assert len(client.get("/forecasts", headers=_bearer(acme)).json()) > 0
    # globex must not see acme's forecasts
    assert client.get("/forecasts", headers=_bearer(globex)).json() == []
