"""Categorical/boolean encoding for model-readiness.

Strategy per column, chosen automatically from cardinality unless
overridden:
  - boolean            -> 0/1 integer
  - low-cardinality categorical -> one-hot (new columns, original dropped)
  - high-cardinality categorical -> label/ordinal encoding (int codes)
  - identifier / text  -> left untouched by default (flagged, not deleted);
                          encoding an identifier as a feature is usually a
                          modeling mistake, but silently dropping the column
                          would be data loss, so we only warn.
"""
from __future__ import annotations

from typing import Any, Literal

import pandas as pd

from app.core.audit import StepReport, run_step
from app.core.pipeline.profiling import profile_dataframe

EncodingStrategy = Literal["onehot", "label", "skip"]


def encode_categoricals(
    df: pd.DataFrame,
    *,
    one_hot_max_cardinality: int = 15,
    overrides: dict[str, EncodingStrategy] | None = None,
) -> tuple[pd.DataFrame, StepReport]:
    overrides = overrides or {}
    profiles = profile_dataframe(df)
    profile_by_col = {p.name: p for p in profiles}

    def _fn(work: pd.DataFrame):
        details: dict[str, Any] = {"columns": []}
        warnings: list[str] = []

        for col in list(work.columns):
            profile = profile_by_col.get(col)
            if profile is None:
                continue

            if profile.kind == "boolean":
                work[col] = work[col].astype("boolean").astype("Int64")
                details["columns"].append({"column": col, "strategy": "boolean_to_int"})
                continue

            if profile.kind == "identifier":
                warnings.append(
                    f"Column '{col}' looks like an identifier (all values unique); "
                    "left unencoded rather than dropped — exclude it manually before training if not needed."
                )
                continue

            if profile.kind == "text":
                warnings.append(f"Column '{col}' looks like free text; left unencoded (no bag-of-words/embedding step configured).")
                continue

            if profile.kind != "categorical":
                continue

            strategy = overrides.get(col)
            if strategy is None:
                strategy = "onehot" if profile.unique_count <= one_hot_max_cardinality else "label"

            if strategy == "skip":
                continue
            elif strategy == "onehot":
                dummies = pd.get_dummies(work[col], prefix=col, dummy_na=False)
                dummies = dummies.astype("Int64")
                insert_at = work.columns.get_loc(col)
                work = work.drop(columns=[col])
                for offset, dummy_col in enumerate(dummies.columns):
                    work.insert(min(insert_at + offset, len(work.columns)), dummy_col, dummies[dummy_col])
                details["columns"].append({
                    "column": col, "strategy": "onehot",
                    "new_columns": list(dummies.columns), "cardinality": profile.unique_count,
                })
            elif strategy == "label":
                codes, uniques = pd.factorize(work[col], sort=True)
                work[col] = codes
                details["columns"].append({
                    "column": col, "strategy": "label",
                    "cardinality": profile.unique_count,
                    "mapping_sample": {str(u): i for i, u in enumerate(uniques[:20])},
                })
            else:
                warnings.append(f"Column '{col}': unknown encoding strategy '{strategy}'; skipped.")

        return work, details, warnings

    return run_step(df, "encode_categoricals", "Encode boolean/categorical columns for model input", _fn)
