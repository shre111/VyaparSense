"""Auth endpoints: signup, login, refresh, and current-user (custom auth, ADR-006).

Uses the `app.security` primitives (Argon2id + JWT). The refresh token is set as
an httpOnly, secure, SameSite cookie; the short-lived access token is returned in
the response body for the SPA to hold in memory.

Refresh tokens rotate: each `/auth/refresh` revokes the presented token and
issues a new one. Presenting an already-revoked refresh jti is treated as theft
— every outstanding refresh token for that user is revoked (forced re-login).

Login/signup are rate-limited per IP (``app.ratelimit``) to blunt brute force.

> ⚠️ Security-sensitive. CSRF protection for the refresh cookie and Postgres RLS
> are still follow-up PRs. Needs a full security review before launch.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app import repository, security
from app.config import get_settings
from app.deps import CurrentUser, SessionDep
from app.ratelimit import rate_limit_auth
from app.schemas import AuthResponse, LoginRequest, SignupRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

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


def _issue_tokens(
    response: Response, session: Session, user_id: int, tenant_id: str, email: str
) -> AuthResponse:
    """Mint an access + refresh token, persist the refresh jti, set the cookie."""
    subject = str(user_id)
    refresh = security.create_refresh_token(subject)
    jti = security.decode_token(refresh, "refresh")["jti"]
    repository.record_refresh_jti(session, user_id=user_id, jti=jti)
    _set_refresh_cookie(response, refresh)
    return AuthResponse(
        access_token=security.create_access_token(subject),
        user_id=user_id,
        tenant_id=tenant_id,
        email=email,
    )


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
)
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
    return _issue_tokens(response, session, user.id, user.tenant_id, user.email)


@router.post("/login", response_model=AuthResponse, dependencies=[Depends(rate_limit_auth)])
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
    return _issue_tokens(response, session, user.id, user.tenant_id, user.email)


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    session: SessionDep,
    response: Response,
    vs_refresh: Annotated[str | None, Cookie()] = None,
) -> AuthResponse:
    """Rotate the refresh token and return a fresh access + refresh pair.

    Reads the refresh token from the httpOnly ``vs_refresh`` cookie, validates it,
    and rotates: the presented jti is revoked and a new pair issued. If the
    presented jti was already revoked (replay/theft), every outstanding refresh
    token for the user is revoked and the request is rejected.
    """
    if vs_refresh is None:
        raise HTTPException(status_code=401, detail="missing refresh token")
    try:
        claims = security.decode_token(vs_refresh, "refresh")
    except security.TokenError as exc:
        raise HTTPException(status_code=401, detail="invalid or expired refresh token") from exc

    jti = claims["jti"]
    stored = repository.get_refresh_token(session, jti)
    user_id = int(claims["sub"])
    if stored is None:
        # Validly-signed but unknown jti -> treat as compromised; revoke all.
        repository.revoke_all_user_refresh(session, user_id)
        raise HTTPException(status_code=401, detail="unrecognized refresh token")
    if stored.revoked:
        # Reuse of an already-rotated token -> revoke the whole family.
        repository.revoke_all_user_refresh(session, user_id)
        raise HTTPException(status_code=401, detail="refresh token reuse detected")

    user = repository.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="user no longer exists")

    repository.revoke_refresh_jti(session, jti)
    return _issue_tokens(response, session, user.id, user.tenant_id, user.email)


@router.get("/me", response_model=UserResponse)
def me(current: CurrentUser) -> UserResponse:
    """Return the current authenticated user (from the Bearer access token)."""
    return UserResponse(user_id=current.id, tenant_id=current.tenant_id, email=current.email)
