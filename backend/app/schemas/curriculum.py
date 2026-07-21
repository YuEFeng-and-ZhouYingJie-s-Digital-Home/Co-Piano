"""
Curriculum Schemas — 课程 API 请求/响应
==========================================
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.curriculum import BlockType


class CurriculumBlock(BaseModel):
    """单个课程块"""
    id: str
    type: BlockType
    title: str
    description: str = ""
    duration_min: int = Field(ge=1, le=60)


class CurriculumDay(BaseModel):
    """一天课程"""
    day_num: int = Field(ge=1, le=7)
    difficulty: str
    blocks: list[CurriculumBlock]


class CurriculumWeekResponse(BaseModel):
    """7 天课程响应"""
    week_id: str
    user_id: str
    total_days: int
    total_blocks: int
    days: list[CurriculumDay]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class BlockCompleteRequest(BaseModel):
    """标记 block 完成请求"""
    score: float = Field(ge=0.0, le=1.0, description="0-1 评分")
    duration_seconds: float = Field(ge=0, default=0.0)


class BlockCompleteResponse(BaseModel):
    """标记完成响应"""
    block_id: str
    user_id: str
    day_num: int
    block_type: BlockType
    score: float
    completed_at: datetime

    # SM-2 spaced repetition
    next_review_days: int
    ease_factor: float
    interval_days: int
    repetitions: int

    @field_validator("user_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v
