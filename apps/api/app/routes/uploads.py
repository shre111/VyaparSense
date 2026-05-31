"""Upload endpoints: ingest a sales CSV -> clean -> classify -> persist."""

from __future__ import annotations

import csv
import io
from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from vyaparsense_ml.classification import classify_series
from vyaparsense_ml.cleaning import clean_sales, to_series
from vyaparsense_ml.schema import CANONICAL_COLUMNS, SalesValidationError, validate_rows

from app import repository
from app.db import get_session
from app.schemas import UploadListItem, UploadSummary

router = APIRouter(tags=["uploads"])

#: Session dependency. Annotated form avoids a call expression in argument
#: defaults (ruff B008), the FastAPI-recommended pattern.
SessionDep = Annotated[Session, Depends(get_session)]


def _parse_csv_bytes(raw: bytes) -> list[dict[str, str]]:
    text = raw.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    try:
        header = [h.strip() for h in next(reader)]
    except StopIteration:
        raise HTTPException(status_code=422, detail="file is empty") from None
    missing = set(CANONICAL_COLUMNS) - set(header)
    extra = set(header) - set(CANONICAL_COLUMNS)
    if missing:
        raise HTTPException(status_code=422, detail=f"missing column(s): {sorted(missing)}")
    if extra:
        raise HTTPException(status_code=422, detail=f"unexpected column(s): {sorted(extra)}")
    return [dict(zip(header, values, strict=False)) for values in reader]


@router.post("/tenants/{tenant_id}/uploads", response_model=UploadSummary)
async def create_upload(
    tenant_id: str,
    file: UploadFile,
    session: SessionDep,
) -> UploadSummary:
    raw = await file.read()
    rows = _parse_csv_bytes(raw)
    try:
        records = validate_rows(rows)
    except SalesValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    cleaned = clean_sales(records)
    series = to_series(cleaned)
    stats = classify_series(series)
    patterns = Counter(s.pattern.value for s in stats.values())

    upload = repository.store_upload(
        session,
        tenant_id=tenant_id,
        filename=file.filename or "upload.csv",
        records=cleaned,
        series_count=len(series),
    )
    return UploadSummary(
        upload_id=upload.id,
        tenant_id=tenant_id,
        filename=upload.filename,
        row_count=upload.row_count,
        series_count=upload.series_count,
        patterns=dict(patterns),
    )


@router.get("/tenants/{tenant_id}/uploads", response_model=list[UploadListItem])
def get_uploads(
    tenant_id: str,
    session: SessionDep,
) -> list[UploadListItem]:
    return [
        UploadListItem(
            upload_id=u.id,
            filename=u.filename,
            row_count=u.row_count,
            series_count=u.series_count,
            status=u.status,
        )
        for u in repository.list_uploads(session, tenant_id)
    ]
