import pandas as pd

from app.core.pipeline.recommender import recommend_algorithms


def test_classification_target_detected_and_scored():
    df = pd.DataFrame({
        "age": [25, 30, 35, 40, 45, 50, 55, 60],
        "income": [30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000],
        "label": ["yes", "no", "yes", "no", "yes", "no", "yes", "no"],
    })
    result = recommend_algorithms(df)
    assert result.target_column == "label"
    assert result.problem_type == "binary_classification"
    assert len(result.recommendations) > 0
    top = sorted(result.recommendations, key=lambda r: -r.score)[0]
    assert top.reasons  # every recommendation must be explainable


def test_regression_case_detected():
    df = pd.DataFrame({
        "sqft": [500, 800, 1200, 1500, 1800, 2200, 2500, 3000],
        "rooms": [1, 2, 3, 3, 4, 4, 5, 5],
        "target": [100000.5, 150000.2, 220000.7, 260000.1, 310000.9, 380000.3, 420000.6, 500000.8],
    })
    result = recommend_algorithms(df)
    assert result.target_column == "target"
    assert result.problem_type == "regression"
    algorithm_names = {r.algorithm for r in result.recommendations}
    assert "Linear Regression" in algorithm_names


def test_no_target_falls_back_to_clustering():
    df = pd.DataFrame({
        "measurement_a": [1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.7, 8.8],
        "measurement_b": [9.9, 8.8, 7.7, 6.6, 5.5, 4.4, 3.3, 2.2],
    })
    result = recommend_algorithms(df)
    assert result.target_column is None
    assert result.problem_type == "clustering"
    algorithm_names = {r.algorithm for r in result.recommendations}
    assert "K-Means" in algorithm_names


def test_class_imbalance_flagged():
    df = pd.DataFrame({
        "feature": list(range(20)),
        "label": ["minority"] * 2 + ["majority"] * 18,
    })
    result = recommend_algorithms(df)
    assert result.dataset_characteristics["class_balance"]["is_imbalanced"] is True
    assert any("imbalanced" in note.lower() for note in result.preprocessing_notes)


def test_high_feature_to_row_ratio_boosts_regularized_regression():
    df = pd.DataFrame({
        "f1": [1.0, 2.0, 3.0, 4.0, 5.0],
        "f2": [2.0, 3.0, 4.0, 5.0, 6.0],
        "f3": [3.0, 4.0, 5.0, 6.0, 7.0],
        "f4": [4.0, 5.0, 6.0, 7.0, 8.0],
        "f5": [5.0, 6.0, 7.0, 8.0, 9.0],
        "f6": [6.0, 7.0, 8.0, 9.0, 10.0],
        "target": [10.5, 20.1, 30.7, 40.2, 50.9],
    })
    result = recommend_algorithms(df)
    assert result.dataset_characteristics["feature_to_row_ratio"] > 0.5
    by_name = {r.algorithm: r for r in result.recommendations}
    assert by_name["Ridge / Lasso Regression"].score > by_name["Linear Regression"].score


def test_explicit_target_column_overrides_auto_detection():
    df = pd.DataFrame({
        "a": [1, 2, 3, 4, 5, 6],
        "chosen": ["p", "q", "p", "q", "p", "q"],
    })
    result = recommend_algorithms(df, target_column="chosen")
    assert result.target_column == "chosen"
    assert result.target_auto_detected is False


def test_unknown_target_column_raises():
    df = pd.DataFrame({"a": [1, 2, 3]})
    try:
        recommend_algorithms(df, target_column="does_not_exist")
        assert False, "expected ValueError"
    except ValueError:
        pass
