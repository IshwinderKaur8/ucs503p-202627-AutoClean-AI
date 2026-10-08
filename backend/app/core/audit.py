"""Audit trail primitives shared by every pipeline step.

Every transformation in the pipeline must report a StepReport so that the
full history of what happened to the data is reconstructable after the
fact. Nothing changes the dataframe without leaving a record here.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ColumnSnapshot:
    rows: int
    columns: int
    null_counts: dict[str, int]
    dtypes: dict[str, str]

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> "ColumnSnapshot":
        return cls(
            rows=len(df),
            columns=len(df.columns),
            null_counts={col: int(df[col].isna().sum()) for col in df.columns},
            dtypes={col: str(df[col].dtype) for col in df.columns},
        )


@dataclass
class StepReport:
    """Record of a single pipeline step's effect on the dataset."""

    step_name: str
    description: str
    before: ColumnSnapshot
    after: ColumnSnapshot
    details: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def rows_changed(self) -> int:
        return self.after.rows - self.before.rows

    @property
    def columns_changed(self) -> int:
        return self.after.columns - self.before.columns

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_name": self.step_name,
            "description": self.description,
            "rows_before": self.before.rows,
            "rows_after": self.after.rows,
            "rows_changed": self.rows_changed,
            "columns_before": self.before.columns,
            "columns_after": self.after.columns,
            "columns_changed": self.columns_changed,
            "nulls_before": sum(self.before.null_counts.values()),
            "nulls_after": sum(self.after.null_counts.values()),
            "details": self.details,
            "warnings": self.warnings,
            "duration_ms": round(self.duration_ms, 3),
        }


class DataLossError(RuntimeError):
    """Raised when a pipeline step violates a no-data-loss invariant."""


class AuditTrail:
    """Accumulates StepReports for a full pipeline run."""

    def __init__(self, original: pd.DataFrame):
        self.original_snapshot = ColumnSnapshot.from_dataframe(original)
        self.steps: list[StepReport] = []

    def record(self, step: StepReport) -> None:
        self.steps.append(step)

    def to_dict(self) -> dict[str, Any]:
        return {
            "original": {
                "rows": self.original_snapshot.rows,
                "columns": self.original_snapshot.columns,
                "nulls": sum(self.original_snapshot.null_counts.values()),
            },
            "steps": [s.to_dict() for s in self.steps],
            "step_count": len(self.steps),
        }


def run_step(
    df: pd.DataFrame,
    step_name: str,
    description: str,
    fn,
    *,
    details: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, StepReport]:
    """Run `fn(df.copy()) -> (new_df, extra_details, warnings)` and wrap it in a StepReport.

    Every step gets a defensive copy of the input so a step can never mutate
    a dataframe another part of the pipeline still holds a reference to.
    """
    before = ColumnSnapshot.from_dataframe(df)
    start = time.perf_counter()
    new_df, extra_details, warnings = fn(df.copy(deep=True))
    duration_ms = (time.perf_counter() - start) * 1000
    after = ColumnSnapshot.from_dataframe(new_df)
    merged_details = {**(details or {}), **(extra_details or {})}
    report = StepReport(
        step_name=step_name,
        description=description,
        before=before,
        after=after,
        details=merged_details,
        warnings=warnings or [],
        duration_ms=duration_ms,
    )
    return new_df, report
