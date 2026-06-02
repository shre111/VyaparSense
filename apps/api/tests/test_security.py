"""Tests for auth security primitives: Argon2id hashing and JWT tokens."""

from __future__ import annotations

import datetime as dt

import jwt
import pytest
from app import config, security
from app.config import Settings


def test_hash_is_argon2id_and_verifies() -> None:
    h = security.hash_password("correct horse battery staple")
    assert h.startswith("$argon2id$")
    assert security.verify_password("correct horse battery staple", h) is True


def test_verify_rejects_wrong_password() -> None:
    h = security.hash_password("secret")
    assert security.verify_password("nope", h) is False


def test_verify_handles_malformed_hash_without_raising() -> None:
    assert security.verify_password("secret", "not-a-hash") is False


def test_hash_is_salted_unique() -> None:
    a = security.hash_password("same")
    b = security.hash_password("same")
    assert a != b  # random salts -> different encoded hashes
    assert security.verify_password("same", a)
    assert security.verify_password("same", b)


def test_empty_password_rejected() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        security.hash_password("")


def test_access_token_round_trip() -> None:
    token = security.create_access_token("user-123")
    claims = security.decode_token(token, "access")
    assert claims["sub"] == "user-123"
    assert claims["type"] == "access"
    assert "jti" in claims and "exp" in claims and "iat" in claims


def test_refresh_token_round_trip() -> None:
    token = security.create_refresh_token("user-123")
    claims = security.decode_token(token, "refresh")
    assert claims["type"] == "refresh"


def test_token_type_mismatch_rejected() -> None:
    access = security.create_access_token("u1")
    with pytest.raises(security.TokenError, match="expected refresh"):
        security.decode_token(access, "refresh")
    refresh = security.create_refresh_token("u1")
    with pytest.raises(security.TokenError, match="expected access"):
        security.decode_token(refresh, "access")


def test_tokens_have_unique_jti() -> None:
    a = security.decode_token(security.create_access_token("u1"), "access")
    b = security.decode_token(security.create_access_token("u1"), "access")
    assert a["jti"] != b["jti"]


def test_tampered_token_rejected() -> None:
    token = security.create_access_token("u1")
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    with pytest.raises(security.TokenError):
        security.decode_token(tampered, "access")


def test_wrong_secret_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    token = security.create_access_token("u1")
    # Verify against a different secret -> invalid signature.
    monkeypatch.setattr(
        config, "get_settings", lambda: Settings(auth_secret="a-different-secret-value")
    )
    with pytest.raises(security.TokenError):
        security.decode_token(token, "access")


def test_expired_token_rejected() -> None:
    # Forge a token that expired in the past, signed with the real secret.
    settings = config.get_settings()
    now = dt.datetime.now(dt.UTC)
    payload = {
        "sub": "u1",
        "type": "access",
        "iat": now - dt.timedelta(hours=2),
        "exp": now - dt.timedelta(hours=1),
        "jti": "x",
    }
    token = jwt.encode(payload, settings.auth_secret, algorithm=settings.auth_jwt_algorithm)
    with pytest.raises(security.TokenError):
        security.decode_token(token, "access")


def test_production_requires_strong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        config,
        "get_settings",
        lambda: Settings(api_env="production", auth_secret="change-me-in-production"),
    )
    with pytest.raises(RuntimeError, match="auth_secret"):
        security.create_access_token("u1")
