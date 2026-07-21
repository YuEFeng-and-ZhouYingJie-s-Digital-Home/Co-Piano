"""
Curriculum Service — 7 天课程编排
====================================

基于 v3.0 curriculum_v2 移植:
- AdaptivePlanner: 7 天课程生成
- SpacedRepetition: SM-2 算法
- WeaknessDetector: 弱点检测
- 8 种 block 类型

与 ORM 模型 BlockType 枚举对齐(hand 而非 warmup_hand)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from app.services.curriculum_v2 import (
    AdaptivePlanner as V3Planner,
    BlockSpec,
    DayPlanV2,
    SpacedRepetition,
    WeekPlanV2,
    WeaknessDetector,
)

logger = logging.getLogger("copiano.curriculum")

# v3.0 → v4 block_type 映射(v3.0 用 warmup_hand/weakness_drill/cooldown_relax)
BLOCK_TYPE_MAP = {
    "warmup_pitch": "warmup_pitch",
    "warmup_hand": "hand",  # 兼容 v3.0 命名
    "expressiveness": "expressiveness",
    "sight_reading": "sight_reading",
    "main_piece": "main_piece",
    "review": "review",
    "weakness": "weakness",
    "cooldown": "cooldown",
    # v3.0 实际可能产生的扩展名
    "weakness_drill": "weakness",
    "cooldown_relax": "cooldown",
}


class CurriculumService:
    """7 天课程服务"""

    def __init__(self) -> None:
        self._srs = SpacedRepetition()

    def _make_planner(
        self,
        avg_score: float = 0.5,
        user_age: Optional[int] = None,
    ) -> V3Planner:
        """每次生成都新建一个 planner(传入 age)"""
        return V3Planner(age=user_age, time_per_day_min=30, days=7)

    def generate_week_plan(
        self,
        user_id: uuid.UUID,
        avg_score: float = 0.5,
        user_age: Optional[int] = None,
        weakness_dimensions: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """生成 7 天课程计划

        Args:
            user_id: 用户 UUID
            avg_score: 历史平均分 (0-1)
            user_age: 用户年龄(影响难度)
            weakness_dimensions: 弱点维度列表 (e.g. ['pitch', 'rhythm'])

        Returns: dict with week_id + days[]
        """
        # 注入弱点到 WeaknessDetector(影响 plan 排序)
        planner = self._make_planner(avg_score=avg_score, user_age=user_age)
        if weakness_dimensions:
            # 把弱点作为已知 dim 注入(简化)
            for d in weakness_dimensions:
                if d in planner.weakness_detector.dim_scores:
                    planner.weakness_detector.dim_scores[d] = 40.0  # 40 < 60 = 弱点

        plan = planner.generate_week_plan()

        # 转换为前端友好格式
        days = []
        for day in plan.days:
            blocks = []
            for idx, block in enumerate(day.blocks):
                # BlockSpec 字段(block_type / minutes / target / piece / module)
                bt = block.block_type
                blocks.append({
                    "id": f"{bt}_{day.day_num}_{idx}",
                    "type": BLOCK_TYPE_MAP.get(bt, bt),
                    "title": block.name,  # BlockSpec.name property
                    "description": block.target or BLOCK_TYPE_MAP.get(bt, ""),
                    "duration_min": block.minutes,
                })
            days.append({
                "day_num": day.day_num,
                "difficulty": day.difficulty,
                "blocks": blocks,
            })

        return {
            "week_id": f"week_{user_id.hex[:8]}_{datetime.utcnow().strftime('%Y%m%d')}",
            "user_id": str(user_id),
            "total_days": len(days),
            "total_blocks": sum(len(d["blocks"]) for d in days),
            "days": days,
        }

    def mark_block_complete(
        self,
        block_id: str,
        score: float = 0.0,
    ) -> dict[str, Any]:
        """标记 block 完成,更新 SM-2 spaced repetition

        Returns:
            {
                "next_review_days": 7,
                "ease_factor": 2.5,
                "repetitions": 1
            }
        """
        # v3.0 SM-2 用 0-100 分制,我们 0-1 → 乘 100
        score_100 = score * 100
        self._srs.record_review(block_id, score_100)
        # 查询下次复习
        next_review = self._srs.get_next_review(block_id)
        return next_review or {
            "piece": block_id,
            "next_review": None,
            "days_until": 0,
            "ease": 1.5,
            "interval_idx": 0,
        }

    def detect_weaknesses(
        self,
        recent_evaluations: list[dict[str, Any]],
    ) -> list[str]:
        """根据最近评估分数检测弱点维度

        Args:
            recent_evaluations: [{"pitch": 0.5, "expressiveness": 0.9, ...}, ...]

        Returns:
            ["pitch", "rhythm"] (得分最低的维度,阈值 <0.6)
        """
        if not recent_evaluations:
            return []

        # 平均分
        dims = ["pitch", "expressiveness", "hand_pose", "rhythm", "sight_reading"]
        avg = {d: sum(e.get(d, 0) for e in recent_evaluations) / len(recent_evaluations)
               for d in dims}

        # 弱点 = 得分 < 0.6 的维度
        return [d for d, score in avg.items() if score < 0.6]


# Singleton
curriculum_service = CurriculumService()
