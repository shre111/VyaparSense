"""Test fixtures: in-memory SQLite + FastAPI TestClient with overridden session.

Tests run against SQLite for speed/isolation. Postgres (via Alembic migrations)
is the production source of truth; models use portable column types so the
schema is equivalent for these tests.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from app.db import Base, get_session, get_session_factory
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    def _override() -> Iterator[Session]:
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = _override
    # Background forecast jobs (ADR-007) open their own session from the factory;
    # point it at the same in-memory DB so they share this test's data.
    app.dependency_overrides[get_session_factory] = lambda: session_factory
    yield TestClient(app)
    app.dependency_overrides.clear()


def _auth(client: TestClient, tenant_id: str, email: str) -> TestClient:
    """Sign up a user and attach its access token to the client's headers."""
    resp = client.post(
        "/auth/signup",
        json={"tenant_id": tenant_id, "email": email, "password": "hunter2pw"},
    )
    assert resp.status_code == 201, resp.text
    client.headers["Authorization"] = f"Bearer {resp.json()['access_token']}"
    return client


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    """A TestClient authenticated as a user of tenant ``acme``.

    Business endpoints derive the tenant from the access token, so tests use this
    instead of putting a tenant id in the URL.
    """
    return _auth(client, "acme", "owner@acme.com")
