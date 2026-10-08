"""In-memory store for uploaded/derived datasets, keyed by dataset id.

Simple by design: this is a single-process demo/dev server, not a
multi-worker production deployment. Swapping this for a Redis- or
disk-backed store later only touches this file.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock

import pandas as pd

from app.core.audit import AuditTrail


@dataclass
class DatasetRecord:
    id: str
    name: str
    dataframe: pd.DataFrame
    created_at: datetime
    parent_id: str | None = None
    audit_trail: AuditTrail | None = None
    extra_warnings: list[str] = field(default_factory=list)


class SessionStore:
    def __init__(self) -> None:
        self._datasets: dict[str, DatasetRecord] = {}
        self._lock = Lock()

    def add(
        self,
        df: pd.DataFrame,
        name: str,
        *,
        parent_id: str | None = None,
        audit_trail: AuditTrail | None = None,
        warnings: list[str] | None = None,
    ) -> DatasetRecord:
        record = DatasetRecord(
            id=str(uuid.uuid4()),
            name=name,
            dataframe=df,
            created_at=datetime.now(timezone.utc),
            parent_id=parent_id,
            audit_trail=audit_trail,
            extra_warnings=warnings or [],
        )
        with self._lock:
            self._datasets[record.id] = record
        return record

    def get(self, dataset_id: str) -> DatasetRecord:
        with self._lock:
            record = self._datasets.get(dataset_id)
        if record is None:
            raise KeyError(f"No dataset found with id '{dataset_id}'.")
        return record

    def list(self) -> list[DatasetRecord]:
        with self._lock:
            return list(self._datasets.values())


store = SessionStore()
