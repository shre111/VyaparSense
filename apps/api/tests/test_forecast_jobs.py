"""Async forecast-job endpoint tests (ADR-007).

The test client runs FastAPI ``BackgroundTasks`` synchronously before returning
the response, so a ``POST`` reports ``queued`` and an immediately-following poll
reports the terminal state.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest
from app.forecasting import FULL_LADDER_MODELS
from fastapi.testclient import TestClient

_HEADER = "date,store_id,sku_id,units_sold,price,promo_flag\n"


def _csv(content: str) -> dict[str, Any]:
    return {"file": ("sales.csv", content.encode("utf-8"), "text/csv")}


def _history_csv(days: int = 60, store: str = "S1", sku: str = "K1") -> str:
    start = dt.date(2024, 1, 1)
    weekly = [8, 9, 7, 10, 12, 20, 18]
    rows = [
        f"{(start + dt.timedelta(days=i)).isoformat()},{store},{sku},{weekly[i % 7]},10.0,0\n"
        for i in range(days)
    ]
    return _HEADER + "".join(rows)


def _intermittent_csv(days: int = 60, store: str = "S1", sku: str = "LUMPY") -> str:
    """A sparse/lumpy series: demand only every 10th day — Croston/TSB territory."""
    start = dt.date(2024, 1, 1)
    rows = []
    for i in range(days):
        d = (start + dt.timedelta(days=i)).isoformat()
        units = 15 if i % 10 == 0 else 0
        rows.append(f"{d},{store},{sku},{units},10.0,0\n")
    return _HEADER + "".join(rows)


def test_job_runs_and_completes(auth_client: TestClient) -> None:
    auth_client.post("/uploads", files=_csv(_history_csv()))
    resp = auth_client.post("/forecast-jobs?horizon=7")
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "queued"  # response built before the task runs
    job_id = body["job_id"]
    assert body["horizon"] == 7

    poll = auth_client.get(f"/forecast-jobs/{job_id}")
    assert poll.status_code == 200
    done = poll.json()
    assert done["status"] == "completed"
    assert done["series_forecast"] == 1
    assert done["forecasts_created"] == 7
    assert done["error"] is None

    # the forecasts the job produced are readable on the normal endpoint
    assert len(auth_client.get("/forecasts").json()) == 7


def test_job_with_no_sales_completes_empty(auth_client: TestClient) -> None:
    resp = auth_client.post("/forecast-jobs")
    job_id = resp.json()["job_id"]
    done = auth_client.get(f"/forecast-jobs/{job_id}").json()
    assert done["status"] == "completed"
    assert done["forecasts_created"] == 0


def test_job_as_of_is_recorded(auth_client: TestClient) -> None:
    auth_client.post("/uploads", files=_csv(_history_csv(days=60)))
    resp = auth_client.post("/forecast-jobs?horizon=7&as_of=2024-02-10")
    assert resp.json()["as_of"] == "2024-02-10"
    job_id = resp.json()["job_id"]
    done = auth_client.get(f"/forecast-jobs/{job_id}").json()
    assert done["status"] == "completed"
    assert done["forecasts_created"] == 7


def test_job_records_failure(auth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise RuntimeError("forecasting blew up")

    # the background task runs during the POST call, so patching here takes effect
    monkeypatch.setattr("app.jobs.generate_forecasts", boom)
    auth_client.post("/uploads", files=_csv(_history_csv()))
    job_id = auth_client.post("/forecast-jobs").json()["job_id"]
    done = auth_client.get(f"/forecast-jobs/{job_id}").json()
    assert done["status"] == "failed"
    assert "forecasting blew up" in done["error"]


def test_job_unknown_id_404(auth_client: TestClient) -> None:
    assert auth_client.get("/forecast-jobs/999999").status_code == 404


def test_job_tenant_isolation(auth_client: TestClient, client: TestClient) -> None:
    # acme creates a job
    auth_client.post("/uploads", files=_csv(_history_csv()))
    job_id = auth_client.post("/forecast-jobs").json()["job_id"]

    # a user of another tenant cannot read it
    other = client.post(
        "/auth/signup",
        json={"tenant_id": "globex", "email": "owner@globex.com", "password": "hunter2pw"},
    )
    token = other.json()["access_token"]
    resp = client.get(f"/forecast-jobs/{job_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_job_requires_auth(client: TestClient) -> None:
    assert client.post("/forecast-jobs").status_code == 401
    assert client.get("/forecast-jobs/1").status_code == 401


def test_full_ladder_includes_classical_and_intermittent() -> None:
    # the job path runs more than baselines (CLAUDE.md §4 rungs 1-3)
    names = {m.name for m in FULL_LADDER_MODELS}
    assert {"naive", "moving_average_7", "seasonal_naive_7"} <= names  # baselines kept
    assert {"auto_ets_7", "auto_arima_7"} <= names  # classical
    assert {"croston", "croston_sba", "tsb"} <= names  # intermittent


def test_job_runs_full_ladder_over_mixed_series(auth_client: TestClient) -> None:
    # a smooth and a lumpy series: exercises classical + intermittent models in
    # the runner without crashing, and each series picks a ladder model.
    csv = _history_csv(days=60, sku="SMOOTH") + _intermittent_csv(days=60, sku="LUMPY").replace(
        _HEADER, ""
    )
    auth_client.post("/uploads", files=_csv(csv))
    job_id = auth_client.post("/forecast-jobs?horizon=7").json()["job_id"]

    done = auth_client.get(f"/forecast-jobs/{job_id}").json()
    assert done["status"] == "completed", done
    assert done["series_forecast"] == 2
    assert done["forecasts_created"] == 14  # 2 series x 7 days

    ladder_names = {m.name for m in FULL_LADDER_MODELS}
    models_used = {f["model"] for f in auth_client.get("/forecasts").json()}
    assert models_used <= ladder_names
