"""
Curriculum API — 课程端点
============================

端点:
- GET  /api/v1/curriculum             当前用户 7 天课程(动态生成)
- GET  /api/v1/curriculum/{day_num}   某天详情
- POST /api/v1/curriculum/blocks/{id}/complete  标记完成 → SM-2 更新 + 写 PG
"""
from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.base import get_async_db
from app.models.curriculum import BlockType, CurriculumProgress
from app.models.evaluation import Evaluation
from app.models.user import User
from app.schemas.curriculum import (
    BlockCompleteRequest,
    BlockCompleteResponse,
    CurriculumBlock,
    CurriculumDay,
    CurriculumWeekResponse,
)
from app.services.curriculum_service import curriculum_service

logger = logging.getLogger("copiano.curriculum.api")

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


def _parse_block_id(block_id: str) -> tuple[int, BlockType]:
    """从 block_id 解析 (day_num, block_type)

    格式: <block_type>_<day_num>_<idx>
    例如: warmup_pitch_1_0 → (1, warmup_pitch)
          hand_2_1 → (2, hand)
    """
    parts = block_id.split("_")
    if len(parts) < 3:
        raise ValueError(f"Invalid block_id format: {block_id}")
    # day_num 是倒数第二段(忽略最后的 idx)
    try:
        day_num = int(parts[-2])
    except ValueError:
        raise ValueError(f"Invalid day_num in block_id: {block_id}")
    # 块类型 = 前面所有段用 _ 拼回
    type_str = "_".join(parts[:-2])
    try:
        block_type = BlockType(type_str)
    except ValueError:
        # 兼容 v3.0 warmup_hand → v4 hand
        if type_str == "warmup_hand":
            block_type = BlockType.HAND
        else:
            raise ValueError(f"Invalid block_type: {type_str}")
    return day_num, block_type


def _to_week_response(plan: dict) -> CurriculumWeekResponse:
    """service 字典 → Pydantic response"""
    days = []
    for d in plan["days"]:
        blocks = [
            CurriculumBlock(
                id=b["id"],
                type=BlockType(b["type"]),
                title=b["title"],
                description=b["description"],
                duration_min=b["duration_min"],
            )
            for b in d["blocks"]
        ]
        days.append(CurriculumDay(
            day_num=d["day_num"],
            difficulty=d["difficulty"],
            blocks=blocks,
        ))
    return CurriculumWeekResponse(
        week_id=plan["week_id"],
        user_id=plan["user_id"],
        total_days=plan["total_days"],
        total_blocks=plan["total_blocks"],
        days=days,
    )


async def _get_user_avg_score(db: AsyncSession, user_id) -> float:
    """从最近 10 次评估算平均分"""
    q = (
        select(Evaluation.overall_score)
        .where(Evaluation.user_id == user_id)
        .order_by(Evaluation.created_at.desc())
        .limit(10)
    )
    result = await db.execute(q)
    scores = [s for s in result.scalars().all() if s is not None]
    if not scores:
        return 0.5  # 默认中等
    return sum(scores) / len(scores)


async def _get_recent_evaluations(db: AsyncSession, user_id, limit: int = 5) -> list[dict]:
    """最近 N 次评估的 5 维分数(用于弱点检测)"""
    q = (
        select(
            Evaluation.pitch_score,
            Evaluation.expressiveness_score,
            Evaluation.hand_pose_score,
            Evaluation.rhythm_score,
            Evaluation.sight_reading_score,
        )
        .where(Evaluation.user_id == user_id)
        .order_by(Evaluation.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(q)
    rows = result.all()
    return [
        {
            "pitch": r[0],
            "expressiveness": r[1],
            "hand_pose": r[2],
            "rhythm": r[3],
            "sight_reading": r[4],
        }
        for r in rows
    ]


@router.get(
    "",
    response_model=CurriculumWeekResponse,
    summary="获取当前用户的 7 天课程(动态生成)",
)
async def get_curriculum(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> CurriculumWeekResponse:
    # 1. 算用户水平
    avg = await _get_user_avg_score(db, current_user.id)

    # 2. 检测弱点
    recent = await _get_recent_evaluations(db, current_user.id)
    weaknesses = curriculum_service.detect_weaknesses(recent)

    # 3. 生成 7 天计划
    plan = curriculum_service.generate_week_plan(
        user_id=current_user.id,
        avg_score=avg,
        user_age=current_user.age,
        weakness_dimensions=weaknesses,
    )

    logger.info(
        "curriculum_generated user=%s avg=%.2f weaknesses=%s blocks=%d",
        current_user.id, avg, weaknesses, plan["total_blocks"],
    )

    return _to_week_response(plan)


@router.get(
    "/{day_num}",
    response_model=CurriculumDay,
    summary="获取某天的课程详情",
)
async def get_curriculum_day(
    day_num: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> CurriculumDay:
    if day_num < 1 or day_num > 7:
        raise HTTPException(
            status_code=400,
            detail="day_num must be between 1 and 7",
        )
    avg = await _get_user_avg_score(db, current_user.id)
    recent = await _get_recent_evaluations(db, current_user.id)
    weaknesses = curriculum_service.detect_weaknesses(recent)
    plan = curriculum_service.generate_week_plan(
        user_id=current_user.id,
        avg_score=avg,
        user_age=current_user.age,
        weakness_dimensions=weaknesses,
    )
    # 找 day_num
    for d in plan["days"]:
        if d["day_num"] == day_num:
            return CurriculumDay(
                day_num=d["day_num"],
                difficulty=d["difficulty"],
                blocks=[
                    CurriculumBlock(
                        id=b["id"],
                        type=BlockType(b["type"]),
                        title=b["title"],
                        description=b["description"],
                        duration_min=b["duration_min"],
                    )
                    for b in d["blocks"]
                ],
            )
    raise HTTPException(status_code=404, detail=f"day {day_num} not in plan")


@router.post(
    "/blocks/{block_id}/complete",
    response_model=BlockCompleteResponse,
    summary="标记 block 完成 → SM-2 更新 + 写 PG",
)
async def mark_block_complete(
    block_id: str,
    body: BlockCompleteRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> BlockCompleteResponse:
    # 1. 解析 block_id
    try:
        day_num, block_type = _parse_block_id(block_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. 调 SM-2 更新
    sm2_result = curriculum_service.mark_block_complete(block_id, body.score)

    # 3. 查/写 PG(CurriculumProgress)
    # 用 (user_id, day_num, block_id) 查
    q = select(CurriculumProgress).where(
        CurriculumProgress.user_id == current_user.id,
        CurriculumProgress.day_num == day_num,
        CurriculumProgress.block_id == block_id,
    )
    existing = (await db.execute(q)).scalar_one_or_none()

    if existing:
        # 更新
        existing.score = body.score
        existing.completed_at = datetime.utcnow()
        existing.duration_seconds = body.duration_seconds
        existing.ease_factor = sm2_result.get("ease", existing.ease_factor)
        existing.interval_days = sm2_result.get("interval_days", 0)
        existing.repetitions += 1
        progress = existing
    else:
        # 新建
        progress = CurriculumProgress(
            user_id=current_user.id,
            day_num=day_num,
            block_id=block_id,
            block_type=block_type,
            title=block_type.value,
            score=body.score,
            completed_at=datetime.utcnow(),
            duration_seconds=body.duration_seconds,
            ease_factor=sm2_result.get("ease", 1.5),
            interval_days=sm2_result.get("interval_days", 0),
            repetitions=1,
        )
        db.add(progress)

    await db.commit()
    await db.refresh(progress)

    # 4. 计算 next_review_days
    ease = progress.ease_factor
    interval = progress.interval_days
    if progress.repetitions == 0:
        next_review = 1
    elif progress.repetitions == 1:
        next_review = 3
    else:
        next_review = max(1, int(interval * ease))

    logger.info(
        "block_completed user=%s block=%s score=%.2f next_review=%d",
        current_user.id, block_id, body.score, next_review,
    )

    return BlockCompleteResponse(
        block_id=block_id,
        user_id=str(current_user.id),
        day_num=day_num,
        block_type=block_type,
        score=body.score,
        completed_at=progress.completed_at,
        next_review_days=next_review,
        ease_factor=ease,
        interval_days=interval,
        repetitions=progress.repetitions,
    )
