from __future__ import annotations

import io
import json

import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.core.pipeline.ingestion import IngestionError, UnsupportedFileType, ingest
from app.core.pipeline.profiling import profile_dataframe
from app.services.session_store import store

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


def _dataset_summary(record) -> dict:
    return {
        "dataset_id": record.id,
        "name": record.name,
        "rows": len(record.dataframe),
        "columns": len(record.dataframe.columns),
        "column_names": list(record.dataframe.columns),
        "parent_id": record.parent_id,
        "created_at": record.created_at.isoformat(),
        "warnings": record.extra_warnings,
    }


def _df_to_json_records(df: pd.DataFrame) -> list[dict]:
    # pandas' own JSON encoder correctly handles NaN/NaT/Timestamps/numpy
    # scalar types; Python's json.dumps or naive .to_dict() do not.
    return json.loads(df.to_json(orient="records", date_format="iso"))


@router.post("/upload")
async def upload_datasets(files: list[UploadFile]) -> list[dict]:
    if not files:
        raise HTTPException(400, "No files provided.")
    results = []
    for file in files:
        raw = await file.read()
        try:
            ingest_result = ingest(file.filename or "upload", raw)
        except UnsupportedFileType as e:
            raise HTTPException(400, str(e)) from e
        except IngestionError as e:
            raise HTTPException(422, str(e)) from e

        record = store.add(
            ingest_result.dataframe,
            name=file.filename or "upload",
            warnings=ingest_result.warnings,
        )
        summary = _dataset_summary(record)
        summary["source_format"] = ingest_result.source_format
        summary["encoding_used"] = ingest_result.encoding_used
        summary["delimiter_used"] = ingest_result.delimiter_used
        summary["sheet_used"] = ingest_result.sheet_used
        results.append(summary)
    return results


@router.get("")
def list_datasets() -> list[dict]:
    return [_dataset_summary(r) for r in store.list()]


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str) -> dict:
    try:
        record = store.get(dataset_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    return _dataset_summary(record)


@router.get("/{dataset_id}/profile")
def profile_dataset(dataset_id: str) -> list[dict]:
    try:
        record = store.get(dataset_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    return [p.to_dict() for p in profile_dataframe(record.dataframe)]


@router.get("/{dataset_id}/preview")
def preview_dataset(dataset_id: str, limit: int = 50) -> dict:
    try:
        record = store.get(dataset_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    df = record.dataframe
    return {
        "columns": list(df.columns),
        "rows": _df_to_json_records(df.head(limit)),
        "total_rows": len(df),
        "returned_rows": min(limit, len(df)),
    }


@router.get("/{dataset_id}/audit")
def get_audit_trail(dataset_id: str) -> dict:
    try:
        record = store.get(dataset_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    if record.audit_trail is None:
        raise HTTPException(404, "This dataset has no audit trail (it was not produced by a pipeline run).")
    return record.audit_trail.to_dict()


@router.get("/{dataset_id}/download")
def download_dataset(dataset_id: str, format: str = "csv") -> StreamingResponse:
    try:
        record = store.get(dataset_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    df = record.dataframe
    base_name = record.name.rsplit(".", 1)[0] or "dataset"

    if format == "csv":
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        content = buf.getvalue().encode("utf-8")
        media_type = "text/csv"
        filename = f"{base_name}_cleaned.csv"
    elif format == "json":
        content = df.to_json(orient="records", date_format="iso").encode("utf-8")
        media_type = "application/json"
        filename = f"{base_name}_cleaned.json"
    elif format == "xlsx":
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        content = buf.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"{base_name}_cleaned.xlsx"
    else:
        raise HTTPException(400, f"Unsupported format '{format}'. Use csv, json, or xlsx.")

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
