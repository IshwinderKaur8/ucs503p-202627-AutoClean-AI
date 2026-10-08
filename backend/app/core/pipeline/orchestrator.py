"""Runs the full cleaning/feature-engineering/scaling pipeline in order,
building a single AuditTrail and enforcing no-data-loss invariants between
steps: any step that is not explicitly configured to add or remove rows
must not change the row count, or the pipeline aborts with a
DataLossError rather than silently continuing with fewer/more rows than
expected.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from app.core.audit import AuditTrail, DataLossError, StepReport
from app.core.pipeline import cleaning, combine, encoding, feature_engineering, outliers, scaling, synthetic
from app.core.pipeline.combine import CombineMode, JoinHow
from app.core.pipeline.encoding import EncodingStrategy
from app.core.pipeline.outliers import OutlierStrategy
from app.core.pipeline.scaling import ScalerMethod

# Steps whose row count must not change unless explicitly noted otherwise.
_ROW_PRESERVING_STEPS = {"coerce_types", "impute_missing", "encode_categoricals", "engineer_features", "scale_features"}


@dataclass
class PipelineConfig:
    coerce_types: bool = True

    numeric_impute_strategy: str = "median"
    categorical_impute_strategy: str = "mode"
    datetime_impute_strategy: str = "ffill_bfill"
    impute_overrides: dict[str, str] = field(default_factory=dict)

    dedupe: bool = False
    dedupe_subset: list[str] | None = None

    outlier_default_strategy: OutlierStrategy = "flag"
    outlier_overrides: dict[str, OutlierStrategy] = field(default_factory=dict)

    encode: bool = True
    one_hot_max_cardinality: int = 15
    encoding_overrides: dict[str, EncodingStrategy] = field(default_factory=dict)

    engineer_features: bool = True

    scale_method: ScalerMethod = "standard"
    scale_columns: list[str] | None = None


def _assert_row_invariant(report: StepReport, *, allow_decrease: bool = False, allow_increase: bool = False) -> None:
    delta = report.rows_changed
    if delta > 0 and not allow_increase:
        raise DataLossError(
            f"Step '{report.step_name}' unexpectedly increased row count by {delta}; "
            "aborting rather than continue with an unexplained row count change."
        )
    if delta < 0 and not allow_decrease:
        raise DataLossError(
            f"Step '{report.step_name}' unexpectedly dropped {-delta} row(s) without being "
            "configured to do so; aborting to avoid silent data loss."
        )


def run_pipeline(df: pd.DataFrame, config: PipelineConfig | None = None) -> tuple[pd.DataFrame, AuditTrail]:
    config = config or PipelineConfig()
    trail = AuditTrail(df)
    working = df

    if config.coerce_types:
        working, report = cleaning.coerce_types(working)
        trail.record(report)
        _assert_row_invariant(report)

    working, report = cleaning.impute_missing(
        working,
        numeric_strategy=config.numeric_impute_strategy,
        categorical_strategy=config.categorical_impute_strategy,
        datetime_strategy=config.datetime_impute_strategy,
        overrides=config.impute_overrides,
    )
    trail.record(report)
    _assert_row_invariant(report)

    working, report = cleaning.handle_duplicates(working, subset=config.dedupe_subset, drop=config.dedupe)
    trail.record(report)
    _assert_row_invariant(report, allow_decrease=config.dedupe)

    outlier_removal_possible = config.outlier_default_strategy == "remove" or "remove" in config.outlier_overrides.values()
    working, report = outliers.handle_outliers(
        working,
        default_strategy=config.outlier_default_strategy,
        overrides=config.outlier_overrides,
    )
    trail.record(report)
    _assert_row_invariant(report, allow_decrease=outlier_removal_possible)

    if config.encode:
        working, report = encoding.encode_categoricals(
            working, one_hot_max_cardinality=config.one_hot_max_cardinality, overrides=config.encoding_overrides
        )
        trail.record(report)
        _assert_row_invariant(report)

    if config.engineer_features:
        working, report = feature_engineering.engineer_features(working)
        trail.record(report)
        _assert_row_invariant(report)

    working, report = scaling.scale_features(working, method=config.scale_method, columns=config.scale_columns)
    trail.record(report)
    _assert_row_invariant(report)

    return working, trail


def run_pipeline_multi_source(
    sources: list[tuple[str, pd.DataFrame]],
    *,
    combine_mode: CombineMode = "concat",
    combine_on: list[str] | None = None,
    combine_how: JoinHow = "outer",
    config: PipelineConfig | None = None,
) -> tuple[pd.DataFrame, AuditTrail]:
    """Combine multiple uploaded sources into one dataset, then run the
    standard cleaning pipeline on the result."""
    combined_df, combine_report = combine.combine_datasets(sources, mode=combine_mode, on=combine_on, how=combine_how)
    final_df, trail = run_pipeline(combined_df, config=config)
    trail.steps.insert(0, combine_report)
    return final_df, trail


def run_synthetic_augmentation(
    df: pd.DataFrame, *, n_rows: int = 100, seed: int | None = None
) -> tuple[pd.DataFrame, StepReport]:
    result_df, report = synthetic.augment_with_synthetic(df, n_rows=n_rows, seed=seed)
    _assert_row_invariant(report, allow_increase=True)
    return result_df, report
