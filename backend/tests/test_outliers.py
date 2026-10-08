import pandas as pd

from app.core.pipeline import outliers


def _df_with_outlier():
    return pd.DataFrame({"value": [10, 12, 11, 13, 12, 11, 500, 12, 10, 13]})


def test_flag_strategy_preserves_rows_and_adds_flag_column():
    df = _df_with_outlier()
    result, report = outliers.handle_outliers(df, default_strategy="flag")
    assert len(result) == len(df)
    assert "value__is_outlier" in result.columns
    assert result["value__is_outlier"].sum() >= 1
    assert report.rows_changed == 0


def test_clip_strategy_preserves_rows_and_bounds_values():
    df = _df_with_outlier()
    result, report = outliers.handle_outliers(df, default_strategy="clip")
    assert len(result) == len(df)
    assert result["value"].max() < 500
    assert report.rows_changed == 0


def test_remove_strategy_removes_only_outlier_rows():
    df = _df_with_outlier()
    result, report = outliers.handle_outliers(df, default_strategy="remove")
    assert len(result) < len(df)
    assert 500 not in result["value"].values
    assert report.rows_changed < 0
