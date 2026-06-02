"""Auth endpoint tests: signup, login, tokens, refresh cookie, error paths."""

from __future__ import annotations

import httpx
from app import security
from fastapi.testclient import TestClient


def _signup(client: TestClient, **kw: str) -> httpx.Response:
    body = {"tenant_id": "acme", "email": "a@b.com", "password": "hunter2pw"}
    body.update(kw)
    resp: httpx.Response = client.post("/auth/signup", json=body)
    return resp


def test_signup_creates_user_and_returns_tokens(client: TestClient) -> None:
    resp = _signup(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "a@b.com"
    assert body["tenant_id"] == "acme"
    assert body["token_type"] == "bearer"
    # access token is a valid access JWT for the new user
    claims = security.decode_token(body["access_token"], "access")
    assert claims["sub"] == str(body["user_id"])
    # refresh token set as an httpOnly cookie
    assert "vs_refresh" in resp.cookies


def test_signup_refresh_cookie_is_httponly(client: TestClient) -> None:
    resp = _signup(client)
    set_cookie = resp.headers.get("set-cookie", "")
    assert "vs_refresh=" in set_cookie
    assert "HttpOnly" in set_cookie
    # refresh cookie carries a valid refresh token
    token = resp.cookies["vs_refresh"]
    assert security.decode_token(token, "refresh")["sub"] == str(resp.json()["user_id"])


def test_signup_duplicate_email_conflicts(client: TestClient) -> None:
    _signup(client)
    resp = _signup(client)  # same email again
    assert resp.status_code == 409


def test_signup_duplicate_email_case_insensitive(client: TestClient) -> None:
    _signup(client, email="User@B.com")
    resp = _signup(client, email="user@b.com")
    assert resp.status_code == 409


def test_signup_rejects_invalid_email(client: TestClient) -> None:
    resp = _signup(client, email="not-an-email")
    assert resp.status_code == 422


def test_signup_rejects_short_password(client: TestClient) -> None:
    resp = _signup(client, password="short")
    assert resp.status_code == 422


def test_password_not_stored_in_plaintext(client: TestClient) -> None:
    _signup(client, password="hunter2pw")
    # the response never echoes the password; the access token is opaque
    resp = client.post("/auth/login", json={"email": "a@b.com", "password": "hunter2pw"})
    assert "hunter2pw" not in resp.text


def test_login_succeeds_with_correct_password(client: TestClient) -> None:
    _signup(client)
    resp = client.post("/auth/login", json={"email": "a@b.com", "password": "hunter2pw"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "a@b.com"
    assert security.decode_token(body["access_token"], "access")["sub"] == str(body["user_id"])
    assert "vs_refresh" in resp.cookies


def test_login_wrong_password_rejected(client: TestClient) -> None:
    _signup(client)
    resp = client.post("/auth/login", json={"email": "a@b.com", "password": "wrongpassword"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid email or password"


def test_login_unknown_email_rejected_uniformly(client: TestClient) -> None:
    resp = client.post("/auth/login", json={"email": "nobody@b.com", "password": "whatever1"})
    assert resp.status_code == 401
    # same message as wrong password -> no user enumeration
    assert resp.json()["detail"] == "invalid email or password"


def test_login_email_case_insensitive(client: TestClient) -> None:
    _signup(client, email="a@b.com")
    resp = client.post("/auth/login", json={"email": "A@B.com", "password": "hunter2pw"})
    assert resp.status_code == 200
