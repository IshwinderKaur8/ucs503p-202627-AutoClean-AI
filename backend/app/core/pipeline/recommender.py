"""Rule-based ML algorithm recommendation engine.

No LLM involved: this reads the same ColumnProfile data the rest of the
pipeline already computes (see profiling.py) and scores a fixed candidate
list of scikit-learn-style algorithms per problem type. Every score
adjustment carries a human-readable reason so recommendations are always
explainable, never a bare number.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

from app.core.pipeline.profiling import ColumnProfile, profile_dataframe

ProblemType = Literal["binary_classification", "multiclass_classification", "regression", "clustering"]

_TARGET_NAME_HINTS = ("target", "label", "class", "y", "outcome", "result")


@dataclass
class AlgorithmRecommendation:
    algorithm: str
    score: float
    reasons: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "algorithm": self.algorithm,
            "score": round(max(0.0, min(1.0, self.score)), 3),
            "reasons": self.reasons,
            "caveats": self.caveats,
        }


@dataclass
class RecommendationResult:
    problem_type: ProblemType
    target_column: str | None
    target_auto_detected: bool
    dataset_characteristics: dict
    recommendations: list[AlgorithmRecommendation]
    preprocessing_notes: list[str]

    def to_dict(self) -> dict:
        return {
            "problem_type": self.problem_type,
            "target_column": self.target_column,
            "target_auto_detected": self.target_auto_detected,
            "dataset_characteristics": self.dataset_characteristics,
            "recommendations": [r.to_dict() for r in sorted(self.recommendations, key=lambda r: -r.score)],
            "preprocessing_notes": self.preprocessing_notes,
        }


def _detect_target(df: pd.DataFrame, profiles: list[ColumnProfile]) -> tuple[ColumnProfile | None, bool]:
    by_name = {p.name: p for p in profiles}
    for hint in _TARGET_NAME_HINTS:
        for name, profile in by_name.items():
            if hint == name.lower() or name.lower().endswith(f"_{hint}"):
                return profile, True

    for profile in profiles:
        if profile.kind == "boolean":
            return profile, True
    for profile in profiles:
        if profile.kind == "categorical" and 2 <= profile.unique_count <= 20:
            return profile, True
    return None, True


def _classify_problem(target: ColumnProfile | None) -> ProblemType:
    if target is None:
        return "clustering"
    if target.kind == "boolean" or (target.kind == "categorical" and target.unique_count == 2):
        return "binary_classification"
    if target.kind == "categorical":
        return "multiclass_classification"
    return "regression"


def _class_balance(df: pd.DataFrame, target_col: str) -> dict | None:
    counts = df[target_col].dropna().value_counts()
    if counts.empty or len(counts) < 2:
        return None
    majority, minority = counts.iloc[0], counts.iloc[-1]
    ratio = float(majority / minority) if minority > 0 else float("inf")
    return {
        "class_counts": {str(k): int(v) for k, v in counts.items()},
        "majority_minority_ratio": round(ratio, 2) if ratio != float("inf") else None,
        "is_imbalanced": ratio >= 4.0,
    }


def _characteristics(df: pd.DataFrame, profiles: list[ColumnProfile], target_col: str | None) -> dict:
    feature_profiles = [p for p in profiles if p.name != target_col]
    n_rows = len(df)
    n_features = len(feature_profiles)
    missing_ratios = [p.null_ratio for p in feature_profiles]
    avg_missing_ratio = sum(missing_ratios) / len(missing_ratios) if missing_ratios else 0.0
    has_categorical = any(p.kind == "categorical" for p in feature_profiles)
    has_high_cardinality = any(
        p.kind in ("categorical", "identifier") and p.unique_count > 15 for p in feature_profiles
    )
    has_outliers = any(p.outlier_count > 0 for p in feature_profiles)
    feature_to_row_ratio = (n_features / n_rows) if n_rows else 0.0

    characteristics = {
        "n_rows": n_rows,
        "n_features": n_features,
        "feature_to_row_ratio": round(feature_to_row_ratio, 4),
        "has_categorical": has_categorical,
        "has_high_cardinality": has_high_cardinality,
        "has_outliers": has_outliers,
        "avg_missing_ratio": round(avg_missing_ratio, 4),
    }

    if target_col is not None:
        balance = _class_balance(df, target_col)
        if balance is not None:
            characteristics["class_balance"] = balance

    return characteristics


def _score_classification(chars: dict) -> list[AlgorithmRecommendation]:
    large = chars["n_rows"] > 20000
    imbalanced = chars.get("class_balance", {}).get("is_imbalanced", False)
    high_dim = chars["feature_to_row_ratio"] > 0.5
    mixed_or_nonlinear = chars["has_categorical"] or chars["has_high_cardinality"] or chars["has_outliers"]

    recs = []

    r = AlgorithmRecommendation("Logistic Regression", 0.6, ["Fast, interpretable baseline for linearly separable problems."])
    if high_dim:
        r.score += 0.1
        r.reasons.append("Regularized linear models handle high feature-to-row ratios well.")
    if imbalanced:
        r.caveats.append("Classes are imbalanced — use class_weight='balanced'.")
    recs.append(r)

    r = AlgorithmRecommendation("Random Forest", 0.75, ["Robust to mixed feature types, outliers, and nonlinear relationships without extra tuning."])
    if mixed_or_nonlinear:
        r.score += 0.1
        r.reasons.append("Dataset has categorical/high-cardinality/outlier characteristics that tree ensembles handle natively.")
    if high_dim:
        r.score -= 0.15
        r.caveats.append("High feature-to-row ratio increases overfitting risk — consider limiting tree depth.")
    if imbalanced:
        r.caveats.append("Classes are imbalanced — use class_weight='balanced'.")
    recs.append(r)

    r = AlgorithmRecommendation("Gradient Boosting", 0.7, ["Typically the strongest accuracy among tree-based methods when enough data is available."])
    if chars["n_rows"] < 200:
        r.score -= 0.3
        r.caveats.append("Dataset is quite small; boosting may overfit without careful regularization.")
    else:
        r.score += 0.1
    recs.append(r)

    r = AlgorithmRecommendation("Support Vector Machine", 0.5, ["Effective for small-to-medium datasets with a clear margin between classes."])
    if large:
        r.score -= 0.3
        r.caveats.append("Training cost scales poorly beyond ~20k rows.")
    recs.append(r)

    r = AlgorithmRecommendation("K-Nearest Neighbors", 0.4, ["Simple, no-training-time baseline for small datasets."])
    if large or high_dim:
        r.score -= 0.2
        r.caveats.append("Distance-based methods degrade with large row counts or high dimensionality.")
    recs.append(r)

    r = AlgorithmRecommendation("Naive Bayes", 0.35, ["Very fast baseline, especially effective with many categorical features."])
    if chars["has_categorical"]:
        r.score += 0.1
    recs.append(r)

    return recs


def _score_regression(chars: dict) -> list[AlgorithmRecommendation]:
    large = chars["n_rows"] > 20000
    high_dim = chars["feature_to_row_ratio"] > 0.5
    mixed_or_nonlinear = chars["has_categorical"] or chars["has_high_cardinality"] or chars["has_outliers"]

    recs = []

    r = AlgorithmRecommendation("Linear Regression", 0.55, ["Fast, interpretable baseline for linear relationships."])
    if chars["has_outliers"]:
        r.caveats.append("Outliers present — ordinary least squares is sensitive to them; consider Robust or Huber regression.")
    recs.append(r)

    r = AlgorithmRecommendation("Ridge / Lasso Regression", 0.55, ["Regularization controls overfitting and multicollinearity."])
    if high_dim:
        r.score += 0.2
        r.reasons.append("High feature-to-row ratio makes regularization especially valuable here.")
    recs.append(r)

    r = AlgorithmRecommendation("Random Forest Regressor", 0.75, ["Robust to mixed feature types, outliers, and nonlinear relationships."])
    if mixed_or_nonlinear:
        r.score += 0.1
        r.reasons.append("Dataset has categorical/high-cardinality/outlier characteristics that tree ensembles handle natively.")
    if high_dim:
        r.score -= 0.15
        r.caveats.append("High feature-to-row ratio increases overfitting risk.")
    recs.append(r)

    r = AlgorithmRecommendation("Gradient Boosting Regressor", 0.7, ["Typically the strongest accuracy among tree-based regressors given enough data."])
    if chars["n_rows"] < 200:
        r.score -= 0.3
        r.caveats.append("Dataset is quite small; boosting may overfit.")
    else:
        r.score += 0.1
    recs.append(r)

    r = AlgorithmRecommendation("Support Vector Regression", 0.45, ["Effective for small-to-medium datasets with nonlinear kernels."])
    if large:
        r.score -= 0.3
        r.caveats.append("Training cost scales poorly beyond ~20k rows.")
    recs.append(r)

    return recs


def _score_clustering(chars: dict) -> list[AlgorithmRecommendation]:
    recs = []

    r = AlgorithmRecommendation("K-Means", 0.65, ["Simple, fast baseline for roughly spherical, similarly-sized clusters."])
    if chars["has_outliers"]:
        r.caveats.append("Sensitive to outliers — consider removing/clipping them first or using DBSCAN instead.")
    recs.append(r)

    r = AlgorithmRecommendation("DBSCAN", 0.55, ["Finds arbitrarily-shaped clusters and is robust to outliers/noise (labels them as noise instead of forcing them into a cluster)."])
    if chars["has_outliers"]:
        r.score += 0.15
        r.reasons.append("Dataset has flagged outliers, which DBSCAN handles natively.")
    recs.append(r)

    r = AlgorithmRecommendation("Hierarchical (Agglomerative) Clustering", 0.45, ["Produces a dendrogram useful for exploring cluster structure at multiple granularities."])
    if chars["n_rows"] > 5000:
        r.score -= 0.2
        r.caveats.append("Computationally expensive (O(n^2) or worse) for large row counts.")
    recs.append(r)

    return recs


def recommend_algorithms(df: pd.DataFrame, target_column: str | None = None) -> RecommendationResult:
    profiles = profile_dataframe(df)
    profile_by_name = {p.name: p for p in profiles}

    target_profile: ColumnProfile | None
    target_auto_detected: bool
    if target_column is not None:
        if target_column not in profile_by_name:
            raise ValueError(f"Column '{target_column}' not found in dataset.")
        target_profile, target_auto_detected = profile_by_name[target_column], False
    else:
        target_profile, target_auto_detected = _detect_target(df, profiles)

    problem_type = _classify_problem(target_profile)
    target_name = target_profile.name if target_profile is not None else None
    chars = _characteristics(df, profiles, target_name)

    if problem_type in ("binary_classification", "multiclass_classification"):
        recs = _score_classification(chars)
    elif problem_type == "regression":
        recs = _score_regression(chars)
    else:
        recs = _score_clustering(chars)

    notes: list[str] = []
    if chars["avg_missing_ratio"] > 0:
        notes.append(
            f"Average {chars['avg_missing_ratio']:.1%} missing values across feature columns — "
            "make sure imputation has run before training."
        )
    if chars.get("class_balance", {}).get("is_imbalanced"):
        ratio = chars["class_balance"]["majority_minority_ratio"]
        notes.append(f"Target classes are imbalanced (~{ratio}:1) — consider class_weight, resampling, or SMOTE.")
    if chars["has_high_cardinality"]:
        notes.append("High-cardinality categorical column(s) present — tree-based models handle these better than linear/distance-based ones.")
    if target_profile is None:
        notes.append("No clear target column detected — treating this as an unsupervised/clustering problem. Pass target_column explicitly if there is one.")

    return RecommendationResult(
        problem_type=problem_type,
        target_column=target_name,
        target_auto_detected=target_auto_detected,
        dataset_characteristics=chars,
        recommendations=recs,
        preprocessing_notes=notes,
    )
