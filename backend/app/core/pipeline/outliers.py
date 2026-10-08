"""Outlier detection and handling for numeric columns.

Default action is "flag" (add a boolean indicator column, touch nothing
else) because silently clipping or deleting values is itself a form of
data loss. "clip" and "remove" are opt-in per column.
"""
from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from app.core.audit import StepReport, run_step
from app.core.pipeline.profiling import profile_dataframe

OutlierStrategy = Literal["flag", "clip", "remove", "skip"]


def _iqr_bounds(series: pd.Series) -> tuple[float, float] | None:
    clean = series.dropna()
    if len(clean) < 4:
        return None
    q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return None
    return float(q1 - 1.5 * iqr), float(q3 + 1.5 * iqr)


def handle_outliers(
    df: pd.DataFrame,
    *,
    default_strategy: OutlierStrategy = "flag",
    overrides: dict[str, OutlierStrategy] | None = None,
    columns: list[str] | None = None,
) -> tuple[pd.DataFrame, StepReport]:
    """Detect IQR-based outliers in numeric columns and apply a strategy.

    `columns` restricts detection to specific numeric columns (default: all
    numeric columns found by profiling). `overrides` sets a per-column
    strategy that takes precedence over `default_strategy`.
    """
    overrides = overrides or {}
    profiles = profile_dataframe(df)
    numeric_cols = [p.name for p in profiles if p.kind == "numeric"]
    if columns is not None:
        numeric_cols = [c for c in numeric_cols if c in columns]

    def _fn(work: pd.DataFrame):
        details: dict[str, Any] = {"columns": []}
        warnings: list[str] = []
        rows_removed_total = 0
        combined_remove_mask = pd.Series(False, index=work.index)

        for col in numeric_cols:
            strategy = overrides.get(col, default_strategy)
            if strategy == "skip":
                continue
            bounds = _iqr_bounds(work[col])
            if bounds is None:
                continue
            lower, upper = bounds
            outlier_mask = ((work[col] < lower) | (work[col] > upper)).fillna(False)
            outlier_count = int(outlier_mask.sum())
            if outlier_count == 0:
                continue

            col_detail: dict[str, Any] = {
                "column": col, "strategy": strategy, "outlier_count": outlier_count,
                "lower_bound": lower, "upper_bound": upper,
            }

            if strategy == "flag":
                flag_col = f"{col}__is_outlier"
                work[flag_col] = outlier_mask
                col_detail["flag_column"] = flag_col
            elif strategy == "clip":
                work[col] = work[col].clip(lower=lower, upper=upper)
                col_detail["clipped_count"] = outlier_count
            elif strategy == "remove":
                combined_remove_mask = combined_remove_mask | outlier_mask
                col_detail["marked_for_removal"] = outlier_count
            else:
                warnings.append(f"Column '{col}': unknown outlier strategy '{strategy}'; skipped.")
                continue

            details["columns"].append(col_detail)

        if combined_remove_mask.any():
            rows_removed_total = int(combined_remove_mask.sum())
            work = work.loc[~combined_remove_mask].reset_index(drop=True)
            details["rows_removed"] = rows_removed_total
            warnings.append(
                f"{rows_removed_total} row(s) removed for containing an outlier "
                "in a column configured with strategy='remove'."
            )

        return work, details, warnings

    return run_step(
        df, "handle_outliers",
        "Detect IQR-based outliers in numeric columns and flag/clip/remove per configuration",
        _fn,
    )
