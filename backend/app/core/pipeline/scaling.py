"""Numeric feature scaling/normalization.

Binary 0/1 indicator columns (outlier flags, one-hot output) are excluded
by default since scaling them is rarely meaningful. Scaler parameters
(mean/scale or min/max) are recorded in the report so the transform is
reproducible and invertible later.
"""
from __future__ import annotations

from typing import Any, Literal

import pandas as pd
from sklearn.preprocessing import MinMaxScaler, RobustScaler, StandardScaler

from app.core.audit import StepReport, run_step
from app.core.pipeline.profiling import profile_dataframe

ScalerMethod = Literal["standard", "minmax", "robust", "none"]

_SCALERS = {"standard": StandardScaler, "minmax": MinMaxScaler, "robust": RobustScaler}


def _is_binary_indicator(series: pd.Series) -> bool:
    uniques = set(series.dropna().unique().tolist())
    return uniques <= {0, 1}


def scale_features(
    df: pd.DataFrame,
    *,
    method: ScalerMethod = "standard",
    columns: list[str] | None = None,
    exclude_binary: bool = True,
    train_mask: pd.Series | None = None,
) -> tuple[pd.DataFrame, StepReport]:
    """Scale numeric columns. If `train_mask` is given (True for train rows),
    the scaler is fit on those rows only and applied to all rows — avoiding
    test-set leakage. Rows are never dropped by this step.
    """
    if method == "none":
        def _noop(work: pd.DataFrame):
            return work, {"method": "none"}, ["Scaling skipped (method='none')."]
        return run_step(df, "scale_features", "Scaling skipped", _noop)

    profiles = profile_dataframe(df)
    target_cols = columns if columns is not None else [p.name for p in profiles if p.kind == "numeric"]

    def _fn(work: pd.DataFrame):
        details: dict[str, Any] = {"method": method, "columns": []}
        warnings: list[str] = []
        scaler_cls = _SCALERS[method]

        for col in target_cols:
            if col not in work.columns:
                continue
            series = pd.to_numeric(work[col], errors="coerce").astype("float64")
            if exclude_binary and _is_binary_indicator(series):
                continue
            work[col] = series
            if series.isna().any():
                warnings.append(
                    f"Column '{col}' has missing values at scaling time; those rows keep NaN "
                    "in this column (run imputation before scaling to avoid this)."
                )

            fit_rows = series[train_mask] if train_mask is not None else series
            fit_values = fit_rows.dropna().to_numpy().reshape(-1, 1)
            if fit_values.shape[0] < 2:
                warnings.append(f"Column '{col}': not enough non-null values to fit a scaler; skipped.")
                continue

            scaler = scaler_cls()
            scaler.fit(fit_values)

            non_null_mask = series.notna()
            transformed = scaler.transform(series[non_null_mask].to_numpy().reshape(-1, 1)).ravel()
            work.loc[non_null_mask, col] = transformed

            params: dict[str, Any] = {}
            if method == "standard":
                params = {"mean": float(scaler.mean_[0]), "scale": float(scaler.scale_[0])}
            elif method == "minmax":
                params = {"data_min": float(scaler.data_min_[0]), "data_max": float(scaler.data_max_[0])}
            elif method == "robust":
                params = {"center": float(scaler.center_[0]), "scale": float(scaler.scale_[0])}

            details["columns"].append({"column": col, "fit_rows": int(fit_values.shape[0]), "params": params})

        return work, details, warnings

    return run_step(df, "scale_features", f"Scale numeric columns using {method} scaler", _fn)
