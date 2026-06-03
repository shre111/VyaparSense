"""Shared FastAPI dependencies — auth/session wiring used across routers.

Lives outside ``routes/`` so business routers depend on it without importing
another route module. ``get_current_user`` resolves the Bearer access token to a
``User``; ``CurrentUser`` / ``CurrentTenant`` are the annotated forms routes use
to scope every request to the authenticated user's tenant (ADR-006).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from app import repository, security
from app.db import get_session, get_session_factory
from app.models import User

SessionDep = Annotated[Session, Depends(get_session)]

#: The session factory, for scheduling background work that outlives the request.
SessionFactoryDep = Annotated[sessionmaker[Session], Depends(get_session_factory)]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Resolve the current user from a Bearer access token. 401 if missing/invalid."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    try:
        claims = security.decode_token(credentials.credentials, "access")
    except security.TokenError as exc:
        raise HTTPException(status_code=401, detail="invalid or expired token") from exc
    user = repository.get_user(session, int(claims["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="user no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_tenant(user: CurrentUser) -> str:
    """The authenticated user's tenant id — the scope for all business data."""
    return user.tenant_id


CurrentTenant = Annotated[str, Depends(get_current_tenant)]
