"""
CurriculumProgress 模型 — 7 天课程进度
======================================

字段:
- user_id, day_num (1-7), block_id
- 8 种 block 类型: warmup_pitch / hand / expressiveness / sight_reading / main_piece / review / weakness / cooldown
- completed_at + score + duration
- SM-2 spaced repetition: ease_factor, interval_days, repetitions
"""
import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class BlockType(str, enum.Enum):
    """课程块类型 (与 v3.0 curriculum_v2 一致)"""
    WARMUP_PITCH = "warmup_pitch"
    HAND = "hand"
    EXPRESSIVENESS = "expressiveness"
    SIGHT_READING = "sight_reading"
    MAIN_PIECE = "main_piece"
    REVIEW = "review"
    WEAKNESS = "weakness"
    COOLDOWN = "cooldown"


class CurriculumProgress(Base, TimestampMixin):
    __tablename__ = "curriculum_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "day_num", "block_id", name="uq_user_day_block"),
    )

    # 复合主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 课程结构
    day_num: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-7
    block_id: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "warmup_pitch_1"
    block_type: Mapped[BlockType] = mapped_column(
        Enum(BlockType, name="block_type_enum"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    description: Mapped[str] = mapped_column(String(2000), default="", nullable=False)

    # 完成情况
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # SM-2 spaced repetition 字段
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 关系
    user = relationship("User", back_populates="curriculum_progress")

    def is_completed(self) -> bool:
        return self.completed_at is not None

    def __repr__(self) -> str:
        return (
            f"<CurriculumProgress day={self.day_num} "
            f"block={self.block_id} score={self.score:.2f}>"
        )
