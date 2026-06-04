"""CORS tests: the SPA's origin is allowed with credentials; others are not.

The app is configured with the default dev origin (http://localhost:3000).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

_WEB = "http://localhost:3000"


def test_allowed_origin_gets_cors_headers(client: TestClient) -> None:
    resp = client.get("/health", headers={"Origin": _WEB})
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == _WEB
    # credentials must be allowed for the cookie-based refresh flow
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_preflight_is_answered(client: TestClient) -> None:
    resp = client.options(
        "/auth/login",
        headers={
            "Origin": _WEB,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == _WEB
    assert "POST" in resp.headers.get("access-control-allow-methods", "")


def test_request_id_header_is_exposed(client: TestClient) -> None:
    resp = client.get("/health", headers={"Origin": _WEB})
    assert "X-Request-ID" in resp.headers.get("access-control-expose-headers", "")


def test_unknown_origin_is_not_allowed(client: TestClient) -> None:
    resp = client.get("/health", headers={"Origin": "https://evil.example"})
    # request still completes, but the browser gets no allow-origin for that host
    assert resp.headers.get("access-control-allow-origin") != "https://evil.example"
