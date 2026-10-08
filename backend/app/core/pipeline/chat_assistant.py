"""Rule-based chat assistant: answers questions about a dataset by reading
its profile/audit-trail and (for algorithm questions) the recommender.

No LLM: intent is picked by keyword matching, and replies are templated
sentences with real, computed numbers interpolated — never canned text
and never a network call. This is the same "heuristic advisor" pattern
already used in llm_advisor.py, applied to free-text questions instead of
structured column suggestions.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd

from app.core.audit import AuditTrail
from app.core.pipeline.profiling import profile_dataframe
from app.core.pipeline.recommender import recommend_algorithms

Intent = str

_RECOMMEND_KEYWORDS = ("algorithm", "model", "train", "predict", "classifier", "regressor", "recommend")
_QUALITY_KEYWORDS = ("missing", "null", "clean", "quality", "complete", "nan")
_OUTLIER_KEYWORDS = ("outlier", "anomaly", "extreme", "weird value")


@dataclass
class ChatReply:
    reply: str
    intent: Intent
    recommendations: list[dict] | None = None

    def to_dict(self) -> dict:
        return {"reply": self.reply, "intent": self.intent, "recommendations": self.recommendations}


def _detect_intent(question: str) -> Intent:
    q = question.lower()
    if any(k in q for k in _RECOMMEND_KEYWORDS):
        return "recommend"
    if any(k in q for k in _QUALITY_KEYWORDS):
        return "data_quality"
    if any(k in q for k in _OUTLIER_KEYWORDS):
        return "outlier"
    return "summary"


def _answer_recommend(df: pd.DataFrame, dataset_name: str, target_column: str | None) -> ChatReply:
    result = recommend_algorithms(df, target_column)
    ranked = sorted(result.recommendations, key=lambda r: -r.score)
    chars = result.dataset_characteristics

    reply = f"Looking at '{dataset_name}': {chars['n_rows']} rows, {chars['n_features']} feature columns. "
    if result.target_column:
        detected = " (auto-detected)" if result.target_auto_detected else ""
        reply += f"This looks like a **{result.problem_type.replace('_', ' ')}** problem targeting '{result.target_column}'{detected}. "
    else:
        reply += "No clear target column was detected, so I'm treating this as unsupervised/clustering. "

    if ranked:
        top = ranked[0]
        top_reason = top.reasons[0] if top.reasons else "a solid general-purpose choice for this problem type."
        reply += f"I'd start with **{top.algorithm}** ({top.score:.0%} fit) — {top_reason}"
        if len(ranked) > 1:
            second = ranked[1]
            second_reason = second.reasons[0] if second.reasons else "worth trying as well."
            reply += f" **{second.algorithm}** is a solid alternative — {second_reason}"

    if result.preprocessing_notes:
        reply += " Also: " + " ".join(result.preprocessing_notes)

    return ChatReply(reply=reply.strip(), intent="recommend", recommendations=[r.to_dict() for r in ranked[:5]])


def _answer_data_quality(df: pd.DataFrame, dataset_name: str, audit_trail: AuditTrail | None) -> ChatReply:
    profiles = profile_dataframe(df)
    total_nulls = sum(p.null_count for p in profiles)
    cols_with_nulls = [p for p in profiles if p.null_count > 0]

    if total_nulls == 0:
        reply = f"'{dataset_name}' has no missing values across its {len(profiles)} columns — looks clean and ready for training."
    else:
        worst = max(cols_with_nulls, key=lambda p: p.null_ratio)
        reply = (
            f"'{dataset_name}' has {total_nulls} missing value(s) across {len(cols_with_nulls)} of "
            f"{len(profiles)} column(s). The most affected is '{worst.name}' at {worst.null_ratio:.1%} missing."
        )
        impute_step = None
        if audit_trail is not None:
            impute_step = next((s for s in audit_trail.steps if s.step_name == "impute_missing"), None)
        if impute_step is not None:
            reply += f" The cleaning pipeline already ran imputation on this dataset (nulls {impute_step.nulls_before} → {impute_step.nulls_after})."
        else:
            reply += " Run the cleaning pipeline to impute these before training."

    return ChatReply(reply=reply, intent="data_quality")


def _answer_outlier(df: pd.DataFrame, dataset_name: str) -> ChatReply:
    profiles = profile_dataframe(df)
    outlier_cols = [p for p in profiles if p.outlier_count > 0]

    if not outlier_cols:
        reply = f"No IQR-based outliers detected in '{dataset_name}'."
    else:
        parts = ", ".join(f"'{p.name}' ({p.outlier_count})" for p in outlier_cols)
        reply = (
            f"Outliers detected in: {parts}. By default the pipeline flags these rather than deleting "
            "them (adds an `__is_outlier` column) — set outlier_default_strategy to 'clip' or 'remove' "
            "in the pipeline config if you want them handled automatically."
        )

    return ChatReply(reply=reply, intent="outlier")


def _answer_summary(df: pd.DataFrame, dataset_name: str) -> ChatReply:
    profiles = profile_dataframe(df)
    kind_counts = Counter(p.kind for p in profiles)
    kinds_text = ", ".join(f"{count} {kind}" for kind, count in kind_counts.items())
    total_nulls = sum(p.null_count for p in profiles)

    reply = (
        f"'{dataset_name}' has {len(df)} rows and {len(profiles)} column(s): {kinds_text}. "
        f"Total missing values: {total_nulls}. "
        'Ask me things like "what algorithm should I use" or "is my data clean" for more specific guidance.'
    )
    return ChatReply(reply=reply, intent="summary")


def answer_question(
    question: str,
    df: pd.DataFrame,
    dataset_name: str,
    *,
    audit_trail: AuditTrail | None = None,
    target_column: str | None = None,
) -> ChatReply:
    intent = _detect_intent(question)
    if intent == "recommend":
        return _answer_recommend(df, dataset_name, target_column)
    if intent == "data_quality":
        return _answer_data_quality(df, dataset_name, audit_trail)
    if intent == "outlier":
        return _answer_outlier(df, dataset_name)
    return _answer_summary(df, dataset_name)
