"""Tests for refresh-token rotation + reuse detection and the auth dependency."""

from __future__ import annotations

from typing import Any

from app import security
from fastapi.testclient import TestClient

_CREDS = {"tenant_id": "acme", "email": "a@b.com", "password": "hunter2pw"}


def _signup(client: TestClient) -> dict[str, Any]:
    resp = client.post("/auth/signup", json=_CREDS)
    assert resp.status_code == 201, resp.text
    body: dict[str, Any] = resp.json()
    return body


# --- GET /auth/me -----------------------------------------------------------


def test_me_returns_current_user(client: TestClient) -> None:
    body = _signup(client)
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert resp.status_code == 200
    assert resp.json() == {
        "user_id": body["user_id"],
        "tenant_id": "acme",
        "email": "a@b.com",
    }


def test_me_without_token_unauthorized(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_me_with_garbage_token_unauthorized(client: TestClient) -> None:
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert resp.status_code == 401


def test_me_rejects_refresh_token_as_access(client: TestClient) -> None:
    _signup(client)
    refresh = client.cookies.get("vs_refresh")
    assert refresh is not None
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert resp.status_code == 401  # wrong token type


# --- POST /auth/refresh rotation -------------------------------------------


def test_refresh_rotates_tokens(client: TestClient) -> None:
    first = _signup(client)
    first_refresh = client.cookies.get("vs_refresh")

    resp = client.post("/auth/refresh")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # new access token, valid, same user
    assert body["access_token"] != first["access_token"]
    assert security.decode_token(body["access_token"], "access")["sub"] == str(first["user_id"])
    # refresh cookie rotated to a new value
    assert client.cookies.get("vs_refresh") != first_refresh


def test_reused_refresh_token_detected_and_revokes_family(client: TestClient) -> None:
    _signup(client)
    old_refresh = client.cookies.get("vs_refresh")

    # First rotation succeeds (cookie now holds the new refresh token).
    assert client.post("/auth/refresh").status_code == 200
    new_refresh = client.cookies.get("vs_refresh")
    assert new_refresh != old_refresh

    # Replay the OLD (now-revoked) refresh token -> reuse detected.
    reuse = client.post("/auth/refresh", cookies={"vs_refresh": old_refresh})
    assert reuse.status_code == 401
    assert "reuse" in reuse.json()["detail"]

    # Family revoked: even the previously-valid new token no longer works.
    after = client.post("/auth/refresh", cookies={"vs_refresh": new_refresh})
    assert after.status_code == 401


def test_refresh_without_cookie_unauthorized(client: TestClient) -> None:
    assert client.post("/auth/refresh").status_code == 401


def test_refresh_with_access_token_rejected(client: TestClient) -> None:
    body = _signup(client)
    # an access token presented as a refresh cookie -> wrong type -> 401
    resp = client.post("/auth/refresh", cookies={"vs_refresh": body["access_token"]})
    assert resp.status_code == 401


def test_unknown_signed_refresh_rejected(client: TestClient) -> None:
    _signup(client)
    # validly-signed refresh for a user, but its jti was never recorded
    forged = security.create_refresh_token("999999")
    resp = client.post("/auth/refresh", cookies={"vs_refresh": forged})
    assert resp.status_code == 401
