import pandas as pd

from app.core.pipeline import cleaning


def test_coerce_types_preserves_row_count(messy_df):
    result, report = cleaning.coerce_types(messy_df)
    assert len(result) == len(messy_df)
    assert report.rows_changed == 0


def test_coerce_types_converts_age_to_numeric(messy_df):
    result, _ = cleaning.coerce_types(messy_df)
    assert pd.api.types.is_numeric_dtype(result["age"])


def test_impute_missing_fills_all_gaps_by_default(messy_df):
    coerced, _ = cleaning.coerce_types(messy_df)
    result, report = cleaning.impute_missing(coerced)
    assert result["age"].isna().sum() == 0
    assert result["city"].isna().sum() == 0
    assert len(result) == len(messy_df)
    assert report.rows_changed == 0


def test_impute_missing_never_drops_rows(messy_df):
    coerced, _ = cleaning.coerce_types(messy_df)
    result, _ = cleaning.impute_missing(coerced)
    assert len(result) == len(messy_df)


def test_handle_duplicates_detects_without_removing_by_default():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    result, report = cleaning.handle_duplicates(df, drop=False)
    assert len(result) == len(df)
    assert report.details["duplicate_count_found"] == 1
    assert any("NOT removed" in w for w in report.warnings)


def test_handle_duplicates_removes_when_enabled():
    df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    result, report = cleaning.handle_duplicates(df, drop=True)
    assert len(result) == 2
    assert report.rows_changed == -1
