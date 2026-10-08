"""Type coercion, missing-value imputation, and duplicate handling.

Guiding rule for this whole module: prefer preserving information over
discarding it. Values that fail conversion become NaN (and are reported),
not dropped rows. Missing values are imputed by default, not deleted.
Duplicate removal is opt-in and always reported even when disabled, so the
user knows duplicates exist even if they choose to keep them.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from app.core.audit import StepReport, run_step
from app.core.pipeline.profiling import ColumnProfile, profile_column, profile_dataframe

_BOOL_MAP = {
    "true": True, "t": True, "yes": True, "y": True, "1": True,
    "false": False, "f": False, "no": False, "n": False, "0": False,
}

DEFAULT_NUMERIC_STRATEGY = "median"
DEFAULT_CATEGORICAL_STRATEGY = "mode"
DEFAULT_DATETIME_STRATEGY = "ffill_bfill"


def coerce_types(
    df: pd.DataFrame, profiles: list[ColumnProfile] | None = None
) -> tuple[pd.DataFrame, StepReport]:
    """Convert columns to their inferred semantic type (numeric/boolean/datetime).

    Cells that fail conversion become NaN and are reported as warnings —
    they are never silently discarded as rows.
    """
    profiles = profiles or profile_dataframe(df)
    profile_by_col = {p.name: p for p in profiles}

    def _fn(work: pd.DataFrame):
        details: dict[str, Any] = {"conversions": []}
        warnings: list[str] = []
        for col in work.columns:
            profile = profile_by_col.get(col)
            if profile is None:
                continue
            original = work[col]
            if profile.kind == "numeric":
                converted = pd.to_numeric(original, errors="coerce")
                failed = int(((original.notna()) & (converted.isna())).sum())
                work[col] = converted
                details["conversions"].append({"column": col, "to": "numeric", "failed_count": failed})
                if failed:
                    warnings.append(
                        f"Column '{col}': {failed} value(s) could not convert to numeric; "
                        "set to missing (will be imputed in the next step), not dropped."
                    )
            elif profile.kind == "boolean":
                mapped = original.astype(str).str.strip().str.lower().map(_BOOL_MAP)
                failed = int(((original.notna()) & (mapped.isna())).sum())
                work[col] = mapped
                details["conversions"].append({"column": col, "to": "boolean", "failed_count": failed})
                if failed:
                    warnings.append(f"Column '{col}': {failed} value(s) did not match a boolean pattern; set to missing.")
            elif profile.kind == "datetime":
                converted = pd.to_datetime(original, errors="coerce", format="mixed")
                failed = int(((original.notna()) & (converted.isna())).sum())
                work[col] = converted
                details["conversions"].append({"column": col, "to": "datetime", "failed_count": failed})
                if failed:
                    warnings.append(f"Column '{col}': {failed} value(s) could not parse as a date; set to missing.")
        return work, details, warnings

    return run_step(df, "coerce_types", "Infer and apply numeric/boolean/datetime types per column", _fn)


def impute_missing(
    df: pd.DataFrame,
    *,
    numeric_strategy: str = DEFAULT_NUMERIC_STRATEGY,
    categorical_strategy: str = DEFAULT_CATEGORICAL_STRATEGY,
    datetime_strategy: str = DEFAULT_DATETIME_STRATEGY,
    overrides: dict[str, str] | None = None,
) -> tuple[pd.DataFrame, StepReport]:
    """Fill missing values so no row needs to be dropped for having a gap.

    strategy values: "mean" | "median" | "mode" | "ffill_bfill" | "constant:<value>" | "skip"
    `overrides` lets a caller force a specific column to a specific strategy.
    """
    overrides = overrides or {}

    def _fn(work: pd.DataFrame):
        details: dict[str, Any] = {"imputations": []}
        warnings: list[str] = []
        for col in work.columns:
            null_count = int(work[col].isna().sum())
            if null_count == 0:
                continue

            profile = profile_column(work[col], col)
            strategy = overrides.get(col)
            if strategy is None:
                if profile.kind == "numeric":
                    strategy = numeric_strategy
                elif profile.kind == "datetime":
                    strategy = datetime_strategy
                elif profile.kind in ("categorical", "boolean", "text", "identifier"):
                    strategy = categorical_strategy
                else:
                    strategy = "skip"

            if strategy == "skip" or profile.kind == "empty":
                warnings.append(f"Column '{col}': {null_count} missing value(s) left as-is (strategy=skip).")
                continue

            fill_value = None
            if strategy == "mean" and profile.kind == "numeric":
                fill_value = work[col].mean()
                work[col] = work[col].fillna(fill_value)
            elif strategy == "median" and profile.kind == "numeric":
                fill_value = work[col].median()
                work[col] = work[col].fillna(fill_value)
            elif strategy == "mode":
                mode_vals = work[col].mode(dropna=True)
                fill_value = mode_vals.iloc[0] if not mode_vals.empty else None
                if fill_value is not None:
                    work[col] = work[col].fillna(fill_value)
            elif strategy == "ffill_bfill":
                work[col] = work[col].ffill().bfill()
                fill_value = "forward/backward fill"
            elif strategy.startswith("constant:"):
                fill_value = strategy.split(":", 1)[1]
                work[col] = work[col].fillna(fill_value)
            else:
                warnings.append(
                    f"Column '{col}': strategy '{strategy}' not applicable to kind '{profile.kind}'; left as-is."
                )
                continue

            remaining = int(work[col].isna().sum())
            filled = null_count - remaining
            details["imputations"].append(
                {"column": col, "strategy": strategy, "filled_count": filled, "fill_value": str(fill_value)}
            )
            if remaining:
                warnings.append(
                    f"Column '{col}': {remaining} value(s) still missing after imputation "
                    "(e.g. entire column may be null)."
                )
        return work, details, warnings

    return run_step(df, "impute_missing", "Fill missing values using per-column strategies", _fn)


def handle_duplicates(
    df: pd.DataFrame, *, subset: list[str] | None = None, drop: bool = False
) -> tuple[pd.DataFrame, StepReport]:
    """Detect (and optionally remove) duplicate rows.

    Detection always runs and is reported. Removal is opt-in (`drop=True`)
    so duplicate rows are never silently discarded.
    """

    def _fn(work: pd.DataFrame):
        dup_mask = work.duplicated(subset=subset, keep="first")
        dup_count = int(dup_mask.sum())
        dup_indices = work.index[dup_mask].tolist()
        details: dict[str, Any] = {"duplicate_count_found": dup_count, "duplicate_indices": dup_indices[:200]}
        warnings: list[str] = []
        if dup_count and not drop:
            warnings.append(f"{dup_count} duplicate row(s) found but NOT removed (drop=False).")
        if drop and dup_count:
            work = work.loc[~dup_mask].reset_index(drop=True)
            details["rows_removed"] = dup_count
        return work, details, warnings

    return run_step(df, "handle_duplicates", "Detect and optionally remove exact duplicate rows", _fn)
