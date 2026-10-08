from __future__ import annotations

from pydantic import BaseModel


class RecommendRequest(BaseModel):
    dataset_id: str
    target_column: str | None = None


class ChatRequest(BaseModel):
    dataset_id: str
    message: str
    target_column: str | None = None
