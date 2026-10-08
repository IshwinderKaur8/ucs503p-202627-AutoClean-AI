import pandas as pd

from app.core.pipeline import scaling


def test_standard_scaler_preserves_rows_and_scales():
    df = pd.DataFrame({"value": [10.0, 20.0, 30.0, 40.0, 50.0]})
    result, report = scaling.scale_features(df, method="standard")
    assert len(result) == len(df)
    assert abs(result["value"].mean()) < 1e-9
    assert report.rows_changed == 0


def test_minmax_scaler_bounds_zero_to_one():
    df = pd.DataFrame({"value": [10.0, 20.0, 30.0, 40.0, 50.0]})
    result, _ = scaling.scale_features(df, method="minmax")
    assert result["value"].min() == 0.0
    assert result["value"].max() == 1.0


def test_binary_indicator_excluded_by_default():
    df = pd.DataFrame({"flag": [0, 1, 0, 1, 1], "value": [10.0, 20.0, 30.0, 40.0, 50.0]})
    result, report = scaling.scale_features(df, method="standard")
    assert list(result["flag"]) == [0, 1, 0, 1, 1]


def test_none_method_is_noop():
    df = pd.DataFrame({"value": [10.0, 20.0, 30.0]})
    result, report = scaling.scale_features(df, method="none")
    assert list(result["value"]) == [10.0, 20.0, 30.0]
