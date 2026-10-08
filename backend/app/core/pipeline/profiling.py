"""Per-column profiling: infer likely semantic type and surface data-quality
signals (missing values, cardinality, outliers) without mutating anything.

Profiling is read-only. It is run before cleaning so the orchestrator (and
the UI) can show the user what it *found* before deciding what to *do*.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

ColumnKind = Literal["numeric", "boolean", "datetime", "categorical", "text", "identifier", "empty"]

_BOOL_TRUE = {"true", "t", "yes", "y", "1"}
_BOOL_FALSE = {"false", "f", "no", "n", "0"}

# Below this ratio of unique-non-null values, a string column is treated as
# categorical rather than free text.
_CATEGORICAL_UNIQUE_RATIO = 0.5
_CATEGORICAL_MAX_UNIQUE = 50


@dataclass
class ColumnProfile:
    name: str
    kind: ColumnKind
    non_null_count: int
    null_count: int
    null_ratio: float
    unique_count: int
    numeric_convertible_ratio: float
    datetime_convertible_ratio: float
    sample_values: list[str]
    outlier_count: int = 0
    outlier_indices: list[int] = field(default_factory=list)
    stats: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "non_null_count": self.non_null_count,
            "null_count": self.null_count,
            "null_ratio": round(self.null_ratio, 4),
            "unique_count": self.unique_count,
            "numeric_convertible_ratio": round(self.numeric_convertible_ratio, 4),
            "datetime_convertible_ratio": round(self.datetime_convertible_ratio, 4),
            "sample_values": self.sample_values,
            "outlier_count": self.outlier_count,
            "outlier_indices": self.outlier_indices[:100],
            "stats": self.stats,
        }


def _numeric_convertible_ratio(series: pd.Series) -> float:
    non_null = series.dropna()
    if non_null.empty:
        return 0.0
    converted = pd.to_numeric(non_null, errors="coerce")
    return float(converted.notna().mean())


def _datetime_convertible_ratio(series: pd.Series) -> float:
    non_null = series.dropna()
    if non_null.empty:
        return 0.0
    converted = pd.to_datetime(non_null, errors="coerce", format="mixed")
    return float(converted.notna().mean())


def _detect_outliers_iqr(numeric: pd.Series) -> list[int]:
    clean = numeric.dropna()
    if len(clean) < 4:
        return []
    q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return []
    lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    mask = (numeric < lower) | (numeric > upper)
    return numeric[mask.fillna(False)].index.tolist()


def profile_column(series: pd.Series, name: str) -> ColumnProfile:
    non_null_count = int(series.notna().sum())
    null_count = int(series.isna().sum())
    total = len(series)
    null_ratio = null_count / total if total else 0.0
    unique_count = int(series.dropna().nunique())
    sample_values = [str(v) for v in series.dropna().unique()[:5]]

    if non_null_count == 0:
        return ColumnProfile(
            name=name, kind="empty", non_null_count=0, null_count=null_count,
            null_ratio=null_ratio, unique_count=0, numeric_convertible_ratio=0.0,
            datetime_convertible_ratio=0.0, sample_values=[],
        )

    kind: ColumnKind
    outlier_indices: list[int] = []
    stats: dict[str, float] = {}
    numeric_ratio = 0.0
    datetime_ratio = 0.0

    # If the column already has a concrete dtype (e.g. re-profiling after
    # coerce_types has run), trust the dtype directly. Falling back to the
    # string-convertibility heuristics below on an already-typed datetime64
    # column is wrong: pd.to_numeric() happily converts datetimes to
    # nanosecond epoch ints, which would misclassify dates as numeric.
    if pd.api.types.is_bool_dtype(series) or str(series.dtype) == "boolean":
        kind = "boolean"
        numeric_ratio = 0.0
    elif pd.api.types.is_datetime64_any_dtype(series):
        kind = "datetime"
        datetime_ratio = 1.0
    elif pd.api.types.is_numeric_dtype(series):
        kind = "numeric"
        numeric_ratio = 1.0
        outlier_indices = _detect_outliers_iqr(series)
        clean = series.dropna()
        if not clean.empty:
            stats = {
                "min": float(clean.min()),
                "max": float(clean.max()),
                "mean": float(clean.mean()),
                "median": float(clean.median()),
                "std": float(clean.std()) if len(clean) > 1 else 0.0,
            }
    else:
        str_series = series.dropna().astype(str).str.strip()
        lower_vals = set(str_series.str.lower().unique())

        numeric_ratio = _numeric_convertible_ratio(series)
        datetime_ratio = _datetime_convertible_ratio(series) if numeric_ratio < 0.9 else 0.0

        if lower_vals <= (_BOOL_TRUE | _BOOL_FALSE):
            kind = "boolean"
        elif numeric_ratio >= 0.95:
            kind = "numeric"
            numeric_series = pd.to_numeric(series, errors="coerce")
            outlier_indices = _detect_outliers_iqr(numeric_series)
            clean = numeric_series.dropna()
            if not clean.empty:
                stats = {
                    "min": float(clean.min()),
                    "max": float(clean.max()),
                    "mean": float(clean.mean()),
                    "median": float(clean.median()),
                    "std": float(clean.std()) if len(clean) > 1 else 0.0,
                }
        elif datetime_ratio >= 0.95:
            kind = "datetime"
        elif unique_count == non_null_count and non_null_count > 20:
            # Every value is unique: likely an identifier, not a feature.
            kind = "identifier"
        elif unique_count <= _CATEGORICAL_MAX_UNIQUE or (unique_count / non_null_count) <= _CATEGORICAL_UNIQUE_RATIO:
            kind = "categorical"
        else:
            kind = "text"

    return ColumnProfile(
        name=name,
        kind=kind,
        non_null_count=non_null_count,
        null_count=null_count,
        null_ratio=null_ratio,
        unique_count=unique_count,
        numeric_convertible_ratio=numeric_ratio,
        datetime_convertible_ratio=datetime_ratio,
        sample_values=sample_values,
        outlier_count=len(outlier_indices),
        outlier_indices=outlier_indices,
        stats=stats,
    )


def profile_dataframe(df: pd.DataFrame) -> list[ColumnProfile]:
    return [profile_column(df[col], col) for col in df.columns]
