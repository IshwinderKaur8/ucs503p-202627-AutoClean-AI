"""Combine multiple datasets into one before running the cleaning pipeline.

Two modes:
  - "concat": stack rows from every source on top of each other. Sources
    don't need identical columns — the result is the UNION of all columns;
    any source missing a column gets NaN there (never dropped, and those
    gaps flow into the normal impute_missing step downstream). A
    `__source_file` column records where every row came from.
  - "merge": relational join of sources on a shared key, applied
    sequentially. Uses an outer join by default so rows that don't match
    on the key are kept (with NaN in the other source's columns) instead
    of being silently dropped — that's the "no data loss" invariant for
    joins.

This module builds its own StepReport instead of using audit.run_step
because it takes multiple input dataframes rather than one.
"""
from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from app.core.audit import ColumnSnapshot, StepReport

CombineMode = Literal["concat", "merge"]
JoinHow = Literal["outer", "left", "right", "inner"]


def _empty_snapshot() -> ColumnSnapshot:
    return ColumnSnapshot(rows=0, columns=0, null_counts={}, dtypes={})


def combine_datasets(
    sources: list[tuple[str, pd.DataFrame]],
    *,
    mode: CombineMode = "concat",
    on: list[str] | None = None,
    how: JoinHow = "outer",
) -> tuple[pd.DataFrame, StepReport]:
    if not sources:
        raise ValueError("combine_datasets requires at least one source dataframe.")

    before = _empty_snapshot()
    warnings: list[str] = []
    details: dict[str, Any] = {
        "mode": mode,
        "sources": [{"name": name, "rows": len(df), "columns": list(df.columns)} for name, df in sources],
    }

    if len(sources) == 1:
        name, only_df = sources[0]
        combined = only_df.copy(deep=True)
        details["note"] = "Only one source provided; combine is a no-op."
    elif mode == "concat":
        all_columns: list[str] = []
        for _, df in sources:
            for col in df.columns:
                if col not in all_columns:
                    all_columns.append(col)

        frames = []
        for name, df in sources:
            work = df.copy(deep=True)
            missing_cols = [c for c in all_columns if c not in work.columns]
            for col in missing_cols:
                work[col] = pd.NA
            if missing_cols:
                warnings.append(
                    f"Source '{name}' was missing columns {missing_cols}; filled with NaN "
                    "(not dropped from the combined schema)."
                )
            work["__source_file"] = name
            frames.append(work[all_columns + ["__source_file"]])

        combined = pd.concat(frames, axis=0, ignore_index=True)
        details["union_columns"] = all_columns
        details["total_rows_expected"] = sum(len(df) for _, df in sources)
        details["total_rows_produced"] = len(combined)

    elif mode == "merge":
        if not on:
            raise ValueError("mode='merge' requires `on` (join key column(s)).")
        combined = sources[0][1].copy(deep=True)
        for name, df in sources[1:]:
            missing_keys = [k for k in on if k not in df.columns or k not in combined.columns]
            if missing_keys:
                raise ValueError(f"Join key(s) {missing_keys} missing from source '{name}' or accumulated result.")
            before_rows = len(combined)
            combined = combined.merge(df, on=on, how=how, suffixes=("", f"__{name}"))
            unmatched = combined[on].isna().any(axis=1).sum() if how != "inner" else 0
            warnings.append(
                f"Merged '{name}': {before_rows} rows -> {len(combined)} rows "
                f"(how='{how}', unmatched-side rows kept: {int(unmatched)})."
            )
        details["join_on"] = on
        details["how"] = how
        details["total_rows_produced"] = len(combined)
    else:
        raise ValueError(f"Unknown combine mode: {mode}")

    after = ColumnSnapshot.from_dataframe(combined)
    report = StepReport(
        step_name="combine_datasets",
        description=f"Combine {len(sources)} source(s) using mode='{mode}'",
        before=before,
        after=after,
        details=details,
        warnings=warnings,
    )
    return combined, report
