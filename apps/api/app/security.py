"""Auth security primitives (ADR-006): Argon2id hashing + JWT tokens.

The cryptographic core of the custom auth, kept pure and dependency-light so it
can be unit-tested in isolation before any User model / endpoints exist:

* :func:`hash_password` / :func:`verify_password` — Argon2id (argon2-cffi), the
  recommended memory-hard password hash. :func:`needs_rehash` lets the login
  flow transparently upgrade hashes when parameters change.
* :func:`create_access_token` / :func:`create_refresh_token` — short-lived
  access + longer-lived refresh JWTs. Each carries ``sub`` (user id), ``type``
  (``access``/``refresh``), ``exp``/``iat``, and a ``jti`` (unique token id) so
  refresh-token rotation + reuse detection can hang off it later.
* :func:`decode_token` — verify signature, expiry, and expected ``type``.

> ⚠️ Security-sensitive. Per CLAUDE.md this needs an extra reviewer and a full
> security review before launch. This module is the primitives only — rate
> limiting, cookie flags, CSRF, and refresh-reuse storage come in later PRs.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app import config

TokenType = Literal["access", "refresh"]

# Argon2id with library defaults (sensible memory/time cost). Centralised so
# parameters can be tuned in one place; needs_rehash picks up changes.
_hasher = PasswordHasher()

_MIN_SECRET_LEN = 32


class TokenError(Exception):
    """Raised when a token is invalid: bad signature, expired, or wrong type."""


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2id. Returns the encoded hash."""
    if not password:
        raise ValueError("password must not be empty")
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Return True iff ``password`` matches ``hashed``; False otherwise.

    Never raises on a wrong password or malformed hash — returns False so
    callers can treat all failures uniformly (and avoid leaking which failed).
    """
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def needs_rehash(hashed: str) -> bool:
    """True if ``hashed`` was made with out-of-date parameters and should be
    re-hashed on next successful login."""
    try:
        return _hasher.check_needs_rehash(hashed)
    except (InvalidHashError, ValueError):
        return True


def _secret() -> str:
    secret = config.get_settings().auth_secret
    if config.get_settings().api_env != "development" and (
        secret == "change-me-in-production" or len(secret) < _MIN_SECRET_LEN
    ):
        raise RuntimeError(
            "auth_secret must be overridden with a strong (>=32 char) value outside development"
        )
    return secret


def _create_token(subject: str, token_type: TokenType, expires_delta: dt.timedelta) -> str:
    now = dt.datetime.now(dt.UTC)
    settings = config.get_settings()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, _secret(), algorithm=settings.auth_jwt_algorithm)


def create_access_token(subject: str) -> str:
    """Mint a short-lived access token for ``subject`` (a user id)."""
    minutes = config.get_settings().access_token_ttl_minutes
    return _create_token(subject, "access", dt.timedelta(minutes=minutes))


def create_refresh_token(subject: str) -> str:
    """Mint a longer-lived refresh token for ``subject``."""
    days = config.get_settings().refresh_token_ttl_days
    return _create_token(subject, "refresh", dt.timedelta(days=days))


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    """Decode + validate a token; return its claims.

    Verifies the signature and expiry, and that the token's ``type`` matches
    ``expected_type`` (so an access token can't be used where a refresh token is
    required, or vice versa).

    Raises:
        TokenError: invalid signature, expired, or wrong type.
    """
    settings = config.get_settings()
    try:
        claims: dict[str, Any] = jwt.decode(
            token, _secret(), algorithms=[settings.auth_jwt_algorithm]
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if claims.get("type") != expected_type:
        raise TokenError(f"expected {expected_type} token, got {claims.get('type')!r}")
    return claims
