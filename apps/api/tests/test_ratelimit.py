"""Auth rate-limiting tests (ADR-006): brute-force protection on credentials."""

from __future__ import annotations

from app.config import get_settings
from fastapi.testclient import TestClient


def _bad_login(client: TestClient) -> int:
    resp = client.post("/auth/login", json={"email": "nobody@acme.com", "password": "wrongpass"})
    return int(resp.status_code)


def test_login_rate_limited_after_cap(client: TestClient) -> None:
    limit = get_settings().auth_rate_limit_per_minute
    # the first `limit` attempts are processed normally (wrong creds -> 401)
    for _ in range(limit):
        assert _bad_login(client) == 401
    # the next attempt is blocked by the limiter
    resp = client.post("/auth/login", json={"email": "nobody@acme.com", "password": "wrongpass"})
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


def test_signup_shares_the_credential_limit(client: TestClient) -> None:
    limit = get_settings().auth_rate_limit_per_minute
    # exhaust the window with failed logins...
    for _ in range(limit):
        _bad_login(client)
    # ...and signup (same per-IP credential bucket) is now blocked too
    resp = client.post(
        "/auth/signup",
        json={"tenant_id": "acme", "email": "owner@acme.com", "password": "hunter2pw"},
    )
    assert resp.status_code == 429


def test_limit_resets_between_tests(client: TestClient) -> None:
    # the autouse fixture cleared the limiter, so a fresh signup succeeds here
    resp = client.post(
        "/auth/signup",
        json={"tenant_id": "acme", "email": "owner@acme.com", "password": "hunter2pw"},
    )
    assert resp.status_code == 201
