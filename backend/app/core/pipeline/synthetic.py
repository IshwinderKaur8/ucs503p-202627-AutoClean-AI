"""Synthetic data generation.

Generates new rows by sampling each column's *marginal* distribution
independently (empirical bootstrap for numeric/categorical/boolean,
uniform-range sampling for datetime). This is a lightweight, dependency-free
approach — it does NOT preserve correlations between columns (e.g. it won't
keep "age" and "income" jointly realistic), which is called out explicitly
in the report so it isn't mistaken for a full generative model.

Two entry points:
  - generate_synthetic(df, n_rows): produce a standalone synthetic dataframe
    with the same schema as `df`.
  - augment_with_synthetic(df, n_rows): append synthetic rows to `df`
    (purely additive — never removes or alters existing rows).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.core.audit import ColumnSnapshot, StepReport, run_step
from app.core.pipeline.profiling import profile_dataframe

_JITTER_FRACTION = 0.03


def _sample_numeric(series: pd.Series, n_rows: int, rng: np.random.Generator) -> pd.Series:
    clean = series.dropna()
    base = rng.choice(clean.to_numpy(), size=n_rows, replace=True)
    is_integer_like = bool((clean % 1 == 0).all())
    std = float(clean.std()) if len(clean) > 1 else 0.0
    if std > 0:
        noise = rng.normal(loc=0.0, scale=std * _JITTER_FRACTION, size=n_rows)
        base = base + noise
    if is_integer_like:
        base = np.round(base)
    return pd.Series(base)


def _sample_categorical(series: pd.Series, n_rows: int, rng: np.random.Generator) -> pd.Series:
    counts = series.dropna().value_counts(normalize=True)
    return pd.Series(rng.choice(counts.index.to_numpy(), size=n_rows, p=counts.to_numpy(), replace=True))


def _sample_datetime(series: pd.Series, n_rows: int, rng: np.random.Generator) -> pd.Series:
    ts = pd.to_datetime(series, errors="coerce").dropna().astype("int64")
    if ts.empty:
        return pd.Series([pd.NaT] * n_rows)
    sampled_ns = rng.integers(low=int(ts.min()), high=int(ts.max()) + 1, size=n_rows, dtype="int64")
    return pd.to_datetime(sampled_ns)


def generate_synthetic(
    df: pd.DataFrame, *, n_rows: int = 100, seed: int | None = None
) -> tuple[pd.DataFrame, StepReport]:
    """Produce a new, standalone synthetic dataframe with the same columns as `df`."""
    rng = np.random.default_rng(seed)
    profiles = profile_dataframe(df)
    before = ColumnSnapshot.from_dataframe(df)

    synthetic_cols: dict[str, pd.Series] = {}
    details: dict[str, Any] = {"n_rows": n_rows, "columns": [], "seed": seed}
    warnings: list[str] = [
        "Synthetic rows are sampled per-column independently; correlations "
        "between columns in the original data are NOT preserved."
    ]

    for profile in profiles:
        col = profile.name
        if profile.non_null_count == 0:
            synthetic_cols[col] = pd.Series([pd.NA] * n_rows)
            details["columns"].append({"column": col, "method": "all_missing_source"})
            continue

        numeric_series = pd.to_numeric(df[col], errors="coerce") if profile.kind == "numeric" else None
        is_binary_indicator = numeric_series is not None and set(numeric_series.dropna().unique().tolist()) <= {0, 1}

        if profile.kind == "numeric" and not is_binary_indicator:
            synthetic_cols[col] = _sample_numeric(numeric_series, n_rows, rng)
            method = "numeric_bootstrap_with_jitter"
        elif is_binary_indicator:
            synthetic_cols[col] = _sample_categorical(df[col], n_rows, rng)
            method = "binary_indicator_frequency_sampling"
        elif profile.kind in ("categorical", "boolean"):
            synthetic_cols[col] = _sample_categorical(df[col], n_rows, rng)
            method = "categorical_frequency_sampling"
        elif profile.kind == "datetime":
            synthetic_cols[col] = _sample_datetime(df[col], n_rows, rng)
            method = "datetime_uniform_range_sampling"
        elif profile.kind == "identifier":
            synthetic_cols[col] = pd.Series([f"synthetic_{col}_{i}" for i in range(n_rows)])
            method = "generated_placeholder_id"
            warnings.append(f"Column '{col}' is an identifier; synthetic values are placeholders, not real entity IDs.")
        else:  # text
            synthetic_cols[col] = _sample_categorical(df[col], n_rows, rng)
            method = "text_bootstrap_resample"
            warnings.append(f"Column '{col}' is free text; synthetic values are resampled existing text, not newly generated.")

        details["columns"].append({"column": col, "method": method})

    synthetic_df = pd.DataFrame(synthetic_cols)[df.columns]
    after = ColumnSnapshot.from_dataframe(synthetic_df)

    report = StepReport(
        step_name="generate_synthetic",
        description=f"Generate {n_rows} synthetic row(s) by sampling per-column marginal distributions",
        before=before,
        after=after,
        details=details,
        warnings=warnings,
    )
    return synthetic_df, report


def augment_with_synthetic(
    df: pd.DataFrame, *, n_rows: int = 100, seed: int | None = None
) -> tuple[pd.DataFrame, StepReport]:
    """Append synthetic rows to `df`. Purely additive: existing rows are untouched."""
    synthetic_df, gen_report = generate_synthetic(df, n_rows=n_rows, seed=seed)

    def _fn(work: pd.DataFrame):
        combined = pd.concat([work, synthetic_df], axis=0, ignore_index=True)
        details = {"synthetic_rows_added": len(synthetic_df), **gen_report.details}
        return combined, details, gen_report.warnings

    return run_step(df, "augment_with_synthetic", f"Append {n_rows} synthetic row(s) to the dataset", _fn)
