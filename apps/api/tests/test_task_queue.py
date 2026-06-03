"""RQ wiring tests (ADR-011) — exercised without a live Redis.

The producer/consumer wiring and the route's redis-vs-inline branch are tested by
stubbing the queue, so CI needs no Redis. The default ``inline`` transport is
covered by ``test_forecast_jobs.py``.
"""

from __future__ import annotations

import pytest
from app import task_queue
from app.db import SessionLocal
from fastapi.testclient import TestClient


def test_redis_mode_enqueues_instead_of_running(
    auth_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[int] = []
    monkeypatch.setenv("FORECAST_QUEUE", "redis")
    monkeypatch.setattr(
        "app.routes.forecasts.enqueue_forecast_job", lambda job_id: captured.append(job_id)
    )

    resp = auth_client.post("/forecast-jobs")
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # the job was handed to the queue, not run in-process
    assert captured == [job_id]
    # with no worker running it stays queued (proves it did NOT run inline)
    assert auth_client.get(f"/forecast-jobs/{job_id}").json()["status"] == "queued"


def test_enqueue_forecast_job_uses_the_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    enqueued: list[tuple[object, tuple[object, ...]]] = []

    class FakeQueue:
        def enqueue(self, func: object, *args: object) -> None:
            enqueued.append((func, args))

    monkeypatch.setattr(task_queue, "get_queue", lambda: FakeQueue())
    task_queue.enqueue_forecast_job(7)
    assert enqueued == [(task_queue.run_forecast_job_task, (7,))]


def test_worker_task_runs_job_with_fresh_session(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[object, int]] = []
    monkeypatch.setattr(
        task_queue, "run_forecast_job", lambda factory, job_id: calls.append((factory, job_id))
    )
    task_queue.run_forecast_job_task(42)
    # the worker entrypoint runs the job against the real session factory
    assert calls == [(SessionLocal, 42)]
