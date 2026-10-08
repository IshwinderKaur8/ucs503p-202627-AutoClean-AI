from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.audit import DataLossError
from app.core.pipeline import combine as combine_module
from app.core.pipeline import synthetic as synthetic_module
from app.core.pipeline.llm_advisor import get_advisor
from app.core.pipeline.orchestrator import PipelineConfig, run_pipeline
from app.core.pipeline.profiling import profile_dataframe
from app.schemas.pipeline import CombineRequest, RunPipelineRequest, SyntheticRequest
from app.services.session_store import store

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run")
def run_pipeline_endpoint(payload: RunPipelineRequest) -> dict:
    try:
        source = store.get(payload.dataset_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e

    config = PipelineConfig(**payload.config.model_dump())
    try:
        result_df, trail = run_pipeline(source.dataframe, config=config)
    except DataLossError as e:
        raise HTTPException(500, f"Pipeline aborted to prevent silent data loss: {e}") from e

    result_name = payload.result_name or f"{source.name} (cleaned)"
    record = store.add(result_df, result_name, parent_id=source.id, audit_trail=trail)

    advisor = get_advisor()
    explanations = [{"step_name": s.step_name, "explanation": advisor.explain_step(s)} for s in trail.steps]

    return {
        "dataset_id": record.id,
        "name": record.name,
        "rows": len(result_df),
        "columns": len(result_df.columns),
        "audit_trail": trail.to_dict(),
        "step_explanations": explanations,
    }


@router.post("/combine")
def combine_endpoint(payload: CombineRequest) -> dict:
    if len(payload.dataset_ids) < 1:
        raise HTTPException(400, "Provide at least one dataset_id to combine.")
    try:
        sources = [(store.get(did).name, store.get(did).dataframe) for did in payload.dataset_ids]
    except KeyError as e:
        raise HTTPException(404, str(e)) from e

    try:
        combined_df, report = combine_module.combine_datasets(
            sources, mode=payload.mode, on=payload.on, how=payload.how
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    result_name = payload.result_name or f"combined ({payload.mode})"
    record = store.add(combined_df, result_name, warnings=report.warnings)

    return {
        "dataset_id": record.id,
        "name": record.name,
        "rows": len(combined_df),
        "columns": len(combined_df.columns),
        "report": report.to_dict(),
    }


@router.post("/synthetic")
def synthetic_endpoint(payload: SyntheticRequest) -> dict:
    try:
        source = store.get(payload.dataset_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e

    if payload.augment:
        result_df, report = synthetic_module.augment_with_synthetic(
            source.dataframe, n_rows=payload.n_rows, seed=payload.seed
        )
        default_name = f"{source.name} (+{payload.n_rows} synthetic)"
    else:
        result_df, report = synthetic_module.generate_synthetic(
            source.dataframe, n_rows=payload.n_rows, seed=payload.seed
        )
        default_name = f"{source.name} (synthetic only)"

    record = store.add(result_df, payload.result_name or default_name, parent_id=source.id, warnings=report.warnings)

    return {
        "dataset_id": record.id,
        "name": record.name,
        "rows": len(result_df),
        "columns": len(result_df.columns),
        "report": report.to_dict(),
    }


@router.get("/{dataset_id}/suggestions")
def column_suggestions(dataset_id: str) -> list[dict]:
    try:
        record = store.get(dataset_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    advisor = get_advisor()
    profiles = profile_dataframe(record.dataframe)
    suggestions = [advisor.suggest_column_role(p) for p in profiles]
    return [
        {"column": s.column, "suggested_role": s.suggested_role, "confidence": s.confidence, "reason": s.reason}
        for s in suggestions
    ]
