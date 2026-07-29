"""
Sight Reading Service — 视奏训练编排
========================================

基于 v3.0 sight_reading_trainer 移植:
- 4 难度 × 3 模式 × 3 输入
- Session 跟踪 + 统计
- landmark / interval / pattern 3 种教学法
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from app.services.sight_reading_trainer import (
    get_difficulty,
    interval_note_sequence,
    landmark_note_sequence,
    pattern_note_sequence,
    pitch_to_name,
)

logger = logging.getLogger("copiano.sight_reading")


class SightReadingService:
    """视奏训练服务"""

    # 4 难度
    DIFFICULTIES = ["beginner", "elementary", "intermediate", "advanced"]
    # 3 模式
    MODES = ["random", "interval", "piece"]
    # 3 输入
    INPUTS = ["keyboard", "midi", "note_name"]

    def __init__(self) -> None:
        pass

    def start_session(
        self,
        user_id: uuid.UUID,
        difficulty: str = "beginner",
        mode: str = "random",
        input_method: str = "keyboard",
    ) -> dict[str, Any]:
        """开始视奏会话"""
        if difficulty not in self.DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {difficulty}")
        if mode not in self.MODES:
            raise ValueError(f"Invalid mode: {mode}")
        if input_method not in self.INPUTS:
            raise ValueError(f"Invalid input_method: {input_method}")

        session_id = uuid.uuid4()
        first_q = self._generate_question(difficulty, mode)

        return {
            "session_id": str(session_id),
            "user_id": str(user_id),
            "difficulty": difficulty,
            "mode": mode,
            "input_method": input_method,
            "started_at": "2026-07-21T00:00:00Z",
            "current_question": first_q,
            "question_count": 0,
        }

    def _generate_question(
        self,
        difficulty: str,
        mode: str,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """生成一道题"""
        diff = get_difficulty(difficulty)
        count = diff.get("count", 5)

        if mode == "random":
            notes = landmark_note_sequence(difficulty, count=count, seed=seed)
            method = "landmark"
        elif mode == "interval":
            notes = interval_note_sequence(difficulty, count=count, seed=seed)
            method = "interval"
        else:  # piece
            notes = pattern_note_sequence(difficulty, count=count + 3, seed=seed)
            method = "pattern"

        return {
            "method": method,
            "notes": [n.pitch for n in notes],
            "note_names": [pitch_to_name(n.pitch) for n in notes],
            "count": len(notes),
        }

    def check_answer(
        self,
        question: dict[str, Any],
        user_notes: list[int],
    ) -> dict[str, Any]:
        """检查用户答案"""
        expected = question["notes"]
        total = max(len(expected), len(user_notes))
        if total == 0:
            return {"correct": True, "accuracy": 1.0, "matched": 0, "total": 0}

        matched = sum(1 for e, u in zip(expected, user_notes) if e == u)
        accuracy = matched / total
        return {
            "correct": accuracy >= 0.8,
            "accuracy": round(accuracy, 4),
            "matched": matched,
            "total": total,
        }


# Singleton
sight_reading_service = SightReadingService()
