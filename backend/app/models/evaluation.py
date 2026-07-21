"""
Evaluation 模型 — 5 维评估记录
===============================

字段:
- id, user_id
- piece_name (曲目,如 "Bach Prelude in C")
- midi_url (S3/MinIO 路径)
- 5 维分数: pitch / expressiveness / hand_pose / rhythm / sight_reading
- overall_score (5 维加权)
- llm_feedback (LLM 反馈文本)
- duration_seconds (录音时长)
"""
import enum
import uuid

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class DifficultyLevel(str, enum.Enum):
    """难度等级"""
    BEGINNER = "beginner"
    ELEMENTARY = "elementary"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class Evaluation(Base, TimestampMixin):
    __tablename__ = "evaluations"

    # 主键 + 外键
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

    # 曲目信息
    piece_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    piece_composer: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        Enum(DifficultyLevel, name="difficulty_enum"),
        default=DifficultyLevel.ELEMENTARY,
        nullable=False,
    )

    # MIDI 文件
    midi_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    midi_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # 5 维分数 (0.0 - 1.0)
    pitch_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    expressiveness_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hand_pose_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rhythm_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    sight_reading_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # 总体分数 (5 维加权,SQL 不计算,Python 端算)
    overall_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False, index=True
    )

    # LLM 反馈
    llm_feedback: Mapped[str] = mapped_column(String(8192), default="", nullable=False)
    llm_model: Mapped[str] = mapped_column(
        String(100), default="qwen2.5-7b-instruct", nullable=False
    )
    llm_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 关系
    user = relationship("User", back_populates="evaluations")

    # ──────────────────────────────────────────────
    # 5 维权重 (与 v3.0 论文保持一致)
    # ──────────────────────────────────────────────
    WEIGHTS = {
        "pitch": 0.20,
        "expressiveness": 0.25,
        "hand_pose": 0.20,
        "rhythm": 0.20,
        "sight_reading": 0.15,
    }

    def compute_overall(self) -> float:
        """计算 5 维加权总分"""
        return round(
            self.pitch_score * self.WEIGHTS["pitch"]
            + self.expressiveness_score * self.WEIGHTS["expressiveness"]
            + self.hand_pose_score * self.WEIGHTS["hand_pose"]
            + self.rhythm_score * self.WEIGHTS["rhythm"]
            + self.sight_reading_score * self.WEIGHTS["sight_reading"],
            4,
        )

    def __repr__(self) -> str:
        return (
            f"<Evaluation {self.piece_name!r} "
            f"overall={self.overall_score:.2f} "
            f"pitch={self.pitch_score:.2f}>"
        )
