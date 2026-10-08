from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.pipeline.chat_assistant import answer_question
from app.core.pipeline.recommender import recommend_algorithms
from app.schemas.assistant import ChatRequest, RecommendRequest
from app.services.session_store import store

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/recommend")
def recommend_endpoint(payload: RecommendRequest) -> dict:
    try:
        record = store.get(payload.dataset_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e

    try:
        result = recommend_algorithms(record.dataframe, target_column=payload.target_column)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    return result.to_dict()


@router.post("/chat")
def chat_endpoint(payload: ChatRequest) -> dict:
    try:
        record = store.get(payload.dataset_id)
    except KeyError as e:
        raise HTTPException(404, str(e)) from e

    if not payload.message.strip():
        raise HTTPException(400, "message must not be empty.")

    try:
        reply = answer_question(
            payload.message,
            record.dataframe,
            record.name,
            audit_trail=record.audit_trail,
            target_column=payload.target_column,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    return reply.to_dict()
