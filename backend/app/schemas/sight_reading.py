"""
Sight Reading Schemas
======================
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.sight_reading import (
    SightReadingDifficulty,
    SightReadingInput,
    SightReadingMode,
)


# ──────────────────────────────────────────────
# 请求
# ──────────────────────────────────────────────
class SightReadingStartRequest(BaseModel):
    difficulty: SightReadingDifficulty = SightReadingDifficulty.BEGINNER
    mode: SightReadingMode = SightReadingMode.RANDOM
    input_method: SightReadingInput = SightReadingInput.KEYBOARD


class SightReadingAnswerRequest(BaseModel):
    user_notes: list[int] = Field(..., description="用户回答的 MIDI 数字列表")


# ──────────────────────────────────────────────
# 响应
# ──────────────────────────────────────────────
class SightReadingQuestion(BaseModel):
    method: str  # landmark / interval / pattern
    notes: list[int]  # MIDI 数字
    note_names: list[str]  # C4, D4, ...
    count: int


class SightReadingStartResponse(BaseModel):
    session_id: str
    difficulty: SightReadingDifficulty
    mode: SightReadingMode
    input_method: SightReadingInput
    current_question: SightReadingQuestion
    question_count: int = 0


class SightReadingAnswerResponse(BaseModel):
    session_id: str
    question: SightReadingQuestion
    correct: bool
    accuracy: float
    matched: int
    total: int
    next_question: SightReadingQuestion | None = None
    session_complete: bool = False


class SightReadingSessionStats(BaseModel):
    total_questions: int
    correct_count: int
    accuracy: float
    streak_max: int
    notes_per_minute: float
    duration_seconds: float


class SightReadingSessionResponse(BaseModel):
    session_id: str
    user_id: str
    difficulty: SightReadingDifficulty
    mode: SightReadingMode
    input_method: SightReadingInput
    started_at: datetime
    ended_at: datetime | None = None
    stats: SightReadingSessionStats

    @field_validator("session_id", "user_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
