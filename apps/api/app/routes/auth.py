"""Auth endpoints: signup and login (custom auth, ADR-006).

Uses the `app.security` primitives (Argon2id + JWT). The refresh token is set as
an httpOnly, secure, SameSite cookie; the short-lived access token is returned in
the response body for the SPA to hold in memory.

> ⚠️ Security-sensitive. Refresh-token rotation + reuse detection, CSRF
> protection for the cookie, rate limiting, and `tenant_id` isolation middleware
> are follow-up PRs. Needs a full security review before launch.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import repository, security
from app.config import get_settings
from app.db import get_session
from app.schemas import AuthResponse, LoginRequest, SignupRequest

router = APIRouter(prefix="/auth", tags=["auth"])

SessionDep = Annotated[Session, Depends(get_session)]

_REFRESH_COOKIE = "vs_refresh"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.api_env != "development",
        samesite="lax",
        max_age=settings.refresh_token_ttl_days * 24 * 3600,
        path="/auth",
    )


def _auth_response(response: Response, user_id: int, tenant_id: str, email: str) -> AuthResponse:
    subject = str(user_id)
    _set_refresh_cookie(response, security.create_refresh_token(subject))
    return AuthResponse(
        access_token=security.create_access_token(subject),
        user_id=user_id,
        tenant_id=tenant_id,
        email=email,
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, session: SessionDep, response: Response) -> AuthResponse:
    """Register a new user under a tenant and return access + refresh tokens."""
    if "@" not in body.email:
        raise HTTPException(status_code=422, detail="invalid email")
    if repository.get_user_by_email(session, body.email) is not None:
        raise HTTPException(status_code=409, detail="email already registered")
    user = repository.create_user(
        session,
        tenant_id=body.tenant_id,
        email=body.email,
        password_hash=security.hash_password(body.password),
    )
    return _auth_response(response, user.id, user.tenant_id, user.email)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, session: SessionDep, response: Response) -> AuthResponse:
    """Verify credentials and return access + refresh tokens.

    Returns a uniform 401 for both unknown email and wrong password (no
    user-enumeration leak). Transparently upgrades the stored hash if the
    Argon2id parameters have changed.
    """
    user = repository.get_user_by_email(session, body.email)
    if user is None or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")
    if security.needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(body.password)
        session.commit()
    return _auth_response(response, user.id, user.tenant_id, user.email)
