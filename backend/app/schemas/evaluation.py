"""
Evaluation Schemas — 评估 API 请求/响应
=========================================
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.evaluation import DifficultyLevel


# ──────────────────────────────────────────────
# 请求
# ──────────────────────────────────────────────
class EvaluationCreateRequest(BaseModel):
    """multipart/form-data 请求(MIDI 文件通过 UploadFile 单独传)"""
    piece_name: str = Field(..., min_length=1, max_length=255)
    piece_composer: str = Field(default="", max_length=255)
    difficulty: DifficultyLevel = DifficultyLevel.ELEMENTARY
    period_hint: str = Field(default="", description="baroque / classical / romantic")


# ──────────────────────────────────────────────
# 响应
# ──────────────────────────────────────────────
class EvaluationResponse(BaseModel):
    """评估详情响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    piece_name: str
    piece_composer: str
    difficulty: DifficultyLevel
    midi_url: str
    midi_size_bytes: int
    duration_seconds: float

    # 5 维分数
    pitch_score: float
    expressiveness_score: float
    hand_pose_score: float
    rhythm_score: float
    sight_reading_score: float
    overall_score: float

    # LLM 反馈(留空,等 A4.7)
    llm_feedback: str = ""
    llm_model: str = "qwen2.5-7b-instruct"
    llm_latency_ms: int = 0

    created_at: datetime
    updated_at: datetime

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class EvaluationListResponse(BaseModel):
    """历史评估列表(分页)"""
    items: list[EvaluationResponse]
    total: int
    skip: int
    limit: int


class EvaluationCreateResponse(BaseModel):
    """创建评估响应(包含 5 维详情 + 教学建议)"""
    evaluation: EvaluationResponse
    tips: list[str] = []
    # 详细数据(可选,前端展示用)
    pitch_detail: dict[str, Any] | None = None
    expressiveness_detail: dict[str, Any] | None = None
    hand_pose_detail: dict[str, Any] | None = None
    duration_ms: int = 0
