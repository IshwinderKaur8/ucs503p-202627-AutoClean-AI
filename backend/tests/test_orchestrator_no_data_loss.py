import pandas as pd
import pytest

from app.core.audit import DataLossError
from app.core.pipeline.orchestrator import PipelineConfig, run_pipeline, run_pipeline_multi_source, run_synthetic_augmentation


def test_default_pipeline_never_drops_rows(messy_df):
    result, trail = run_pipeline(messy_df)
    assert len(result) == len(messy_df)
    assert trail.original_snapshot.rows == len(messy_df)
    for step in trail.steps:
        # every recorded step in the default (non-dedupe, non-remove) config must be row-preserving
        assert step.rows_changed == 0


def test_pipeline_with_dedupe_reports_removed_rows():
    df = pd.DataFrame({
        "a": [1, 1, 2, 3],
        "b": ["x", "x", "y", "z"],
    })
    config = PipelineConfig(dedupe=True, encode=False, engineer_features=False, scale_method="none")
    result, trail = run_pipeline(df, config=config)
    assert len(result) == 3
    dedupe_step = next(s for s in trail.steps if s.step_name == "handle_duplicates")
    assert dedupe_step.rows_changed == -1


def test_no_data_left_behind_missing_values_all_imputed(messy_df):
    result, _ = run_pipeline(messy_df)
    # after coerce+impute, no nulls should remain in the numeric/categorical source columns
    assert result["age"].isna().sum() == 0
    assert result["is_active"].isna().sum() == 0


def test_audit_trail_is_complete_and_serializable(messy_df):
    _, trail = run_pipeline(messy_df)
    payload = trail.to_dict()
    assert payload["original"]["rows"] == len(messy_df)
    assert payload["step_count"] == len(trail.steps)
    assert all("step_name" in s for s in payload["steps"])


def test_combine_then_clean_unions_columns_without_loss():
    source_a = pd.DataFrame({"id": [1, 2, 3], "age": ["25", "30", "35"], "city": ["NYC", "LA", "SF"]})
    source_b = pd.DataFrame({"id": [4, 5], "age": ["40", "45"]})  # no "city" column

    config = PipelineConfig(encode=False, engineer_features=False, scale_method="none")
    result, trail = run_pipeline_multi_source(
        [("a.csv", source_a), ("b.csv", source_b)], combine_mode="concat", config=config
    )

    assert len(result) == 5  # 3 + 2, no rows lost
    assert "city" in result.columns  # union of columns kept, not dropped
    combine_step = trail.steps[0]
    assert combine_step.step_name == "combine_datasets"
    assert combine_step.details["total_rows_produced"] == 5


def test_synthetic_augmentation_is_purely_additive(messy_df):
    result, report = run_synthetic_augmentation(messy_df, n_rows=20, seed=42)
    assert len(result) == len(messy_df) + 20
    # original rows must still be present untouched at the top (dtype may
    # upcast e.g. int64 -> float64 when concatenated with sampled float
    # columns; values themselves must be unchanged)
    pd.testing.assert_frame_equal(
        result.iloc[: len(messy_df)].reset_index(drop=True), messy_df, check_dtype=False
    )
    assert report.rows_changed == 20


def test_data_loss_error_raised_if_row_invariant_violated():
    df = pd.DataFrame({"a": [1, 2, 3]})

    def _bad_fn(work):
        return work.iloc[:1], {}, []

    from app.core.audit import run_step
    _, bad_report = run_step(df, "coerce_types", "intentionally broken step for testing", _bad_fn)

    from app.core.pipeline.orchestrator import _assert_row_invariant
    with pytest.raises(DataLossError):
        _assert_row_invariant(bad_report)
