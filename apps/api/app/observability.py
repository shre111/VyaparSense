"""Structured logging + per-request tracing for the API (observability).

One JSON line per request — method, path, status, duration, and a request id —
so logs are greppable and aggregatable in any host's log drain. Every response
carries an ``X-Request-ID`` (echoing an inbound one if present) to correlate a
client report with its server logs. Unhandled exceptions are logged with the
traceback before being re-raised to FastAPI's error handling.

Dependency-free (stdlib ``logging`` + ``json``). Error tracking (Sentry) and
metrics (Prometheus) are natural follow-ups that can plug into this same setup.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, Request, Response

_LOGGER_NAME = "vyaparsense"
_REQUEST_ID_HEADER = "X-Request-ID"


class JsonFormatter(logging.Formatter):
    """Render a log record as a single JSON object.

    Anything passed via ``extra={"context": {...}}`` is merged in at the top
    level, so request fields (id, path, status, ...) sit alongside the message.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": dt.datetime.fromtimestamp(record.created, tz=dt.UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload.update(context)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """Point the ``vyaparsense`` logger at a JSON stream handler (idempotent)."""
    logger = logging.getLogger(_LOGGER_NAME)
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False  # don't double-log through the root/uvicorn handlers


def get_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def install_observability(app: FastAPI, *, level: str = "INFO") -> None:
    """Configure structured logging and add the request-context middleware."""
    configure_logging(level)
    logger = get_logger()

    @app.middleware("http")
    async def _request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(_REQUEST_ID_HEADER) or uuid4().hex
        started = time.perf_counter()
        base = {"request_id": request_id, "method": request.method, "path": request.url.path}
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception(
                "request failed", extra={"context": {**base, "duration_ms": elapsed_ms}}
            )
            raise
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "request",
            extra={"context": {**base, "status": response.status_code, "duration_ms": elapsed_ms}},
        )
        response.headers[_REQUEST_ID_HEADER] = request_id
        return response
