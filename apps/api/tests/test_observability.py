"""Observability tests: JSON log formatting + per-request tracing header."""

from __future__ import annotations

import json
import logging

from app.observability import JsonFormatter
from fastapi.testclient import TestClient


def test_json_formatter_emits_parseable_json_with_context() -> None:
    record = logging.LogRecord(
        name="vyaparsense",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request",
        args=None,
        exc_info=None,
    )
    record.__dict__["context"] = {"request_id": "abc", "status": 200, "path": "/health"}

    out = json.loads(JsonFormatter().format(record))
    assert out["level"] == "INFO"
    assert out["logger"] == "vyaparsense"
    assert out["msg"] == "request"
    assert out["request_id"] == "abc"
    assert out["status"] == 200
    assert out["path"] == "/health"
    assert "ts" in out


def test_response_carries_request_id_header(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID")  # generated when none supplied


def test_request_id_is_echoed_when_supplied(client: TestClient) -> None:
    resp = client.get("/health", headers={"X-Request-ID": "trace-123"})
    assert resp.headers.get("X-Request-ID") == "trace-123"
