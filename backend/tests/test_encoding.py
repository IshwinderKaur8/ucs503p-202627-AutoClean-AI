import pandas as pd

from app.core.pipeline import encoding


def test_onehot_encodes_low_cardinality_categorical():
    df = pd.DataFrame({"color": ["red", "blue", "red", "green", "blue"]})
    result, report = encoding.encode_categoricals(df, one_hot_max_cardinality=15)
    assert "color" not in result.columns
    assert {"color_red", "color_blue", "color_green"} <= set(result.columns)
    assert len(result) == len(df)


def test_label_encodes_high_cardinality_categorical():
    values = [f"cat_{i}" for i in range(30)] * 2
    df = pd.DataFrame({"tag": values})
    result, report = encoding.encode_categoricals(df, one_hot_max_cardinality=15)
    assert "tag" in result.columns
    assert pd.api.types.is_integer_dtype(result["tag"])
    assert len(result) == len(df)


def test_identifier_column_left_untouched_not_dropped():
    df = pd.DataFrame({"user_id": [f"u{i}" for i in range(25)]})
    result, report = encoding.encode_categoricals(df)
    assert "user_id" in result.columns
    assert list(result["user_id"]) == list(df["user_id"])
    assert any("identifier" in w for w in report.warnings)
