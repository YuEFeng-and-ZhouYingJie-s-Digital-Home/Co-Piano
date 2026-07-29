"""
SightReadingSession 模型 — 视奏训练记录
=======================================

字段:
- id, user_id
- difficulty (4 级: beginner/elementary/intermediate/advanced)
- mode (3 模式: random/interval/piece)
- input_method (3 输入: keyboard/midi/note_name)
- accuracy, streak, notes_per_minute
- 总题数 + 正确数
- started_at, ended_at, duration
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class SightReadingDifficulty(str, enum.Enum):
    """视奏难度 (与 v3.0 sight_reading_trainer 一致)"""
    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class SightReadingMode(str, enum.Enum):
    """视奏模式"""
    RANDOM = "random"
    INTERVAL = "interval"
    PIECE = "piece"


class SightReadingInput(str, enum.Enum):
    """输入方式"""
    KEYBOARD = "keyboard"  # 屏幕键盘 1-7
    MIDI = "midi"          # MIDI 键盘
    NOTE_NAME = "note_name"  # 唱名


class SightReadingSession(Base, TimestampMixin):
    __tablename__ = "sight_reading_sessions"

    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 配置
    difficulty: Mapped[SightReadingDifficulty] = mapped_column(
        Enum(SightReadingDifficulty, name="sight_reading_difficulty_enum"),
        default=SightReadingDifficulty.BEGINNER,
        nullable=False,
        index=True,
    )
    mode: Mapped[SightReadingMode] = mapped_column(
        Enum(SightReadingMode, name="sight_reading_mode_enum"),
        default=SightReadingMode.RANDOM,
        nullable=False,
    )
    input_method: Mapped[SightReadingInput] = mapped_column(
        Enum(SightReadingInput, name="sight_reading_input_enum"),
        default=SightReadingInput.KEYBOARD,
        nullable=False,
    )

    # 表现指标
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    streak_max: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes_per_minute: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # 时间
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # 关系
    user = relationship("User", back_populates="sight_reading_sessions")

    def compute_accuracy(self) -> float:
        """根据 correct/total 重算 accuracy"""
        if self.total_questions == 0:
            return 0.0
        return round(self.correct_count / self.total_questions, 4)

    def __repr__(self) -> str:
        return (
            f"<SightReadingSession {self.difficulty.value} "
            f"acc={self.accuracy:.0%} n/m={self.notes_per_minute:.1f}>"
        )
