"""
Feedback API — LLM 教学反馈
==============================

端点:
- POST /api/v1/feedback                提交 evaluation_id → 调 LLM 反馈
- GET  /api/v1/feedback/history        当前用户历史反馈列表
- GET  /api/v1/feedback/{evaluation_id}  拿某次评估的反馈(从 PG 读)

行为:
- 调 llm_service.generate_feedback() → 5 维评估 → LLM 教学反馈
- 自动回写 evaluation.llm_feedback + llm_model + llm_latency_ms
- 银发用户 (age >= 60) 自动简化 prompt
- 限流 10/min/user
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.rate_limit import RATE_LIMIT_FEEDBACK
from app.db.base import get_async_db
from app.models.evaluation import Evaluation
from app.models.user import User
from app.schemas.feedback import (
    FeedbackHistoryItem,
    FeedbackHistoryResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from app.services.llm_service import llm_service

logger = logging.getLogger("copiano.feedback.api")

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post(
    "",
    response_model=FeedbackResponse,
    summary="为评估生成 LLM 教学反馈",
)
async def create_feedback(
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> FeedbackResponse:
    # 1. 查评估
    evaluation = await db.get(Evaluation, body.evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if evaluation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your evaluation")

    # 2. 构造 5 维 dict 喂给 LLM
    eval_dict = {
        "piece_name": evaluation.piece_name,
        "pitch_score": evaluation.pitch_score,
        "expressiveness_score": evaluation.expressiveness_score,
        "hand_pose_score": evaluation.hand_pose_score,
        "rhythm_score": evaluation.rhythm_score,
        "sight_reading_score": evaluation.sight_reading_score,
        "overall_score": evaluation.overall_score,
    }

    # 3. 调 LLM
    try:
        llm_resp = await llm_service.generate_feedback(
            eval_dict, user_age=current_user.age
        )
    except RuntimeError as e:
        logger.error("llm_failed evaluation=%s error=%s", body.evaluation_id, e)
        raise HTTPException(
            status_code=503,
            detail=f"LLM service unavailable: {e}",
        )

    # 4. 回写 PG
    evaluation.llm_feedback = llm_resp.content
    evaluation.llm_model = llm_resp.model
    evaluation.llm_latency_ms = llm_resp.latency_ms
    await db.commit()

    logger.info(
        "feedback_created evaluation=%s backend=%s latency=%dms tokens=%d",
        body.evaluation_id,
        llm_resp.backend,
        llm_resp.latency_ms,
        llm_resp.total_tokens,
    )

    return FeedbackResponse(
        evaluation_id=str(body.evaluation_id),
        feedback=llm_resp.content,
        model=llm_resp.model,
        backend=llm_resp.backend,
        latency_ms=llm_resp.latency_ms,
        prompt_tokens=llm_resp.prompt_tokens,
        completion_tokens=llm_resp.completion_tokens,
        total_tokens=llm_resp.total_tokens,
        created_at=datetime.utcnow(),
    )


@router.get(
    "/history",
    response_model=FeedbackHistoryResponse,
    summary="当前用户历史反馈(从 PG evaluation.llm_feedback 读)",
)
async def list_feedback_history(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> FeedbackHistoryResponse:
    # 查有 LLM 反馈的评估
    from sqlalchemy import func
    count_q = select(func.count(Evaluation.id)).where(
        Evaluation.user_id == current_user.id,
        Evaluation.llm_feedback != "",
    )
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(Evaluation)
        .where(
            Evaluation.user_id == current_user.id,
            Evaluation.llm_feedback != "",
        )
        .order_by(desc(Evaluation.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(q)
    items = [
        FeedbackHistoryItem(
            evaluation_id=str(e.id),
            feedback_preview=e.llm_feedback[:100] + ("..." if len(e.llm_feedback) > 100 else ""),
            model=e.llm_model,
            created_at=e.created_at,
        )
        for e in result.scalars().all()
    ]

    return FeedbackHistoryResponse(items=items, total=total)


@router.get(
    "/{evaluation_id}",
    response_model=FeedbackResponse,
    summary="拿某次评估的 LLM 反馈",
)
async def get_feedback(
    evaluation_id: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> FeedbackResponse:
    import uuid
    try:
        eid = uuid.UUID(evaluation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid evaluation_id")

    evaluation = await db.get(Evaluation, eid)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if evaluation.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your evaluation")
    if not evaluation.llm_feedback:
        raise HTTPException(
            status_code=404,
            detail="No feedback generated yet (call POST /api/v1/feedback first)",
        )

    return FeedbackResponse(
        evaluation_id=str(evaluation.id),
        feedback=evaluation.llm_feedback,
        model=evaluation.llm_model or "unknown",
        backend="unknown",  # 持久化时未存
        latency_ms=evaluation.llm_latency_ms,
        prompt_tokens=0,  # 未存
        completion_tokens=0,
        total_tokens=0,
        created_at=evaluation.updated_at,  # LLM 写回时更新
    )
