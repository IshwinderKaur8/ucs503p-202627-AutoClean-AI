"""Derived-feature generation.

All features added here are additive: new columns are appended, existing
columns and rows are never modified or removed. That keeps this step
trivially safe from a data-loss perspective.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.core.audit import StepReport, run_step
from app.core.pipeline.profiling import profile_dataframe


def engineer_features(
    df: pd.DataFrame,
    *,
    datetime_parts: bool = True,
    text_length: bool = True,
) -> tuple[pd.DataFrame, StepReport]:
    profiles = profile_dataframe(df)

    def _fn(work: pd.DataFrame):
        details: dict[str, Any] = {"added_columns": []}
        warnings: list[str] = []

        for profile in profiles:
            col = profile.name
            if col not in work.columns:
                continue

            if datetime_parts and profile.kind == "datetime":
                series = pd.to_datetime(work[col], errors="coerce")
                new_cols = {
                    f"{col}__year": series.dt.year,
                    f"{col}__month": series.dt.month,
                    f"{col}__day": series.dt.day,
                    f"{col}__weekday": series.dt.weekday,
                }
                for new_name, values in new_cols.items():
                    work[new_name] = values.astype("Int64")
                    details["added_columns"].append(new_name)

            elif text_length and profile.kind == "text":
                work[f"{col}__length"] = work[col].astype(str).str.len().astype("Int64")
                work[f"{col}__word_count"] = work[col].astype(str).str.split().str.len().astype("Int64")
                details["added_columns"].extend([f"{col}__length", f"{col}__word_count"])

        if not details["added_columns"]:
            warnings.append("No eligible datetime/text columns found; no features added.")

        return work, details, warnings

    return run_step(df, "engineer_features", "Add derived features from datetime/text columns", _fn)
