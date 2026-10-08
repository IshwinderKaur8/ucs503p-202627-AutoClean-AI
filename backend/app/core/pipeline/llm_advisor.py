"""LLM-assist interface, currently backed by a heuristic stub.

The rest of the pipeline is fully deterministic and never calls this
module for anything load-bearing — it only produces suggestions and
human-readable explanations. Swap `_STUB_ADVISOR` for a real Claude API
call later; nothing else in the codebase needs to change.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.audit import StepReport
from app.core.pipeline.profiling import ColumnProfile


@dataclass
class ColumnRoleSuggestion:
    column: str
    suggested_role: str  # "feature" | "target" | "identifier" | "drop_candidate"
    confidence: float
    reason: str


class AdvisorBackend(Protocol):
    def suggest_column_role(self, profile: ColumnProfile) -> ColumnRoleSuggestion: ...
    def explain_step(self, report: StepReport) -> str: ...


class HeuristicAdvisor:
    """Rule-based stand-in for an LLM. No network calls, no API key required."""

    def suggest_column_role(self, profile: ColumnProfile) -> ColumnRoleSuggestion:
        if profile.kind == "identifier":
            return ColumnRoleSuggestion(
                profile.name, "identifier", 0.8,
                "All values are unique, which usually means this is a row identifier rather than a predictive feature.",
            )
        if profile.null_ratio > 0.9:
            return ColumnRoleSuggestion(
                profile.name, "drop_candidate", 0.6,
                f"{profile.null_ratio:.0%} of values are missing; unlikely to carry much signal even after imputation.",
            )
        if profile.kind in ("numeric", "categorical", "boolean", "datetime"):
            return ColumnRoleSuggestion(
                profile.name, "feature", 0.5,
                f"Column looks like a well-formed {profile.kind} column suitable as a model feature.",
            )
        return ColumnRoleSuggestion(
            profile.name, "feature", 0.3,
            f"Column kind '{profile.kind}' inferred with low confidence; review manually.",
        )

    def explain_step(self, report: StepReport) -> str:
        parts = [report.description]
        if report.rows_changed:
            parts.append(f"Rows changed by {report.rows_changed:+d}.")
        if report.columns_changed:
            parts.append(f"Columns changed by {report.columns_changed:+d}.")
        if report.warnings:
            parts.append(f"{len(report.warnings)} warning(s) raised.")
        return " ".join(parts)


_STUB_ADVISOR: AdvisorBackend = HeuristicAdvisor()


def get_advisor() -> AdvisorBackend:
    return _STUB_ADVISOR
