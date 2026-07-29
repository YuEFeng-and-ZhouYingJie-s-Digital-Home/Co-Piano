"""
Sight Reading API
==================

端点:
- POST /api/v1/sight-reading/session       开始新会话,返回第一题
- POST /api/v1/sight-reading/session/{id}/answer  提交答案 + 下一题
- GET  /api/v1/sight-reading/session/{id}  会话详情 + 统计
- POST /api/v1/sight-reading/session/{id}/end  结束会话(可选,timeout 自动结束)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.db.base import get_async_db
from app.models.sight_reading import (
    SightReadingSession,
)
from app.models.user import User
from app.schemas.sight_reading import (
    SightReadingAnswerRequest,
    SightReadingAnswerResponse,
    SightReadingQuestion,
    SightReadingSessionResponse,
    SightReadingSessionStats,
    SightReadingStartRequest,
    SightReadingStartResponse,
)
from app.services.sight_reading_service import sight_reading_service

logger = logging.getLogger("copiano.sight_reading.api")

router = APIRouter(prefix="/sight-reading", tags=["sight_reading"])

# 简单内存 session 状态(题目进度)
# 实际生产应该用 Redis 存,这里只是 demo
_SESSIONS: dict[str, dict] = {}

# 一次会话最多 20 题
MAX_QUESTIONS_PER_SESSION = 20


def _gen_question_payload(diff: str, mode: str) -> SightReadingQuestion:
    """生成一道题(从 service)"""
    q = sight_reading_service._generate_question(diff, mode)
    return SightReadingQuestion(
        method=q["method"],
        notes=q["notes"],
        note_names=q["note_names"],
        count=q["count"],
    )


@router.post(
    "/session",
    response_model=SightReadingStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="开始视奏会话",
)
async def start_session(
    body: SightReadingStartRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> SightReadingStartResponse:
    session = SightReadingSession(
        user_id=current_user.id,
        difficulty=body.difficulty,
        mode=body.mode,
        input_method=body.input_method,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    first_q = _gen_question_payload(body.difficulty.value, body.mode.value)

    # 内存 session state(实际生产用 Redis)
    _SESSIONS[str(session.id)] = {
        "current_question": first_q.model_dump(),
        "question_count": 0,
        "correct_count": 0,
        "streak_max": 0,
        "current_streak": 0,
    }

    logger.info(
        "sight_reading_started user=%s session=%s diff=%s mode=%s",
        current_user.id, session.id, body.difficulty, body.mode,
    )

    return SightReadingStartResponse(
        session_id=str(session.id),
        difficulty=body.difficulty,
        mode=body.mode,
        input_method=body.input_method,
        current_question=first_q,
        question_count=0,
    )


@router.post(
    "/session/{session_id}/answer",
    response_model=SightReadingAnswerResponse,
    summary="提交答案 + 下一题",
)
async def answer_question(
    session_id: uuid.UUID,
    body: SightReadingAnswerRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> SightReadingAnswerResponse:
    # 1. 查 session
    session = await db.get(SightReadingSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")
    if session.ended_at is not None:
        raise HTTPException(status_code=400, detail="Session already ended")

    # 2. 拿当前题
    sid = str(session_id)
    state = _SESSIONS.get(sid)
    if not state:
        raise HTTPException(status_code=400, detail="Session state lost (restart?)")
    current_q = SightReadingQuestion(**state["current_question"])

    # 3. 检查答案
    result = sight_reading_service.check_answer(
        current_q.model_dump(), body.user_notes
    )

    # 4. 更新 state
    state["question_count"] += 1
    if result["correct"]:
        state["correct_count"] += 1
        state["current_streak"] += 1
        state["streak_max"] = max(state["streak_max"], state["current_streak"])
    else:
        state["current_streak"] = 0

    # 5. 持久化到 DB(累加 total_questions / correct_count)
    session.total_questions = state["question_count"]
    session.correct_count = state["correct_count"]
    session.streak_max = state["streak_max"]

    # 6. 是否结束
    is_complete = state["question_count"] >= MAX_QUESTIONS_PER_SESSION
    if is_complete:
        session.ended_at = datetime.utcnow()
        if session.started_at:
            session.duration_seconds = (
                session.ended_at - session.started_at
            ).total_seconds()
        if session.duration_seconds > 0:
            session.notes_per_minute = (
                session.total_questions / session.duration_seconds * 60
            )
        session.accuracy = (
            session.correct_count / session.total_questions
            if session.total_questions > 0 else 0.0
        )
    await db.commit()

    # 7. 下一题
    next_q: SightReadingQuestion | None = None
    if not is_complete:
        next_q = _gen_question_payload(
            session.difficulty.value, session.mode.value
        )
        state["current_question"] = next_q.model_dump()

    logger.info(
        "sight_reading_answered session=%s correct=%s accuracy=%.2f",
        session_id, result["correct"], result["accuracy"],
    )

    return SightReadingAnswerResponse(
        session_id=sid,
        question=current_q,
        correct=result["correct"],
        accuracy=result["accuracy"],
        matched=result["matched"],
        total=result["total"],
        next_question=next_q,
        session_complete=is_complete,
    )


@router.get(
    "/session/{session_id}",
    response_model=SightReadingSessionResponse,
    summary="会话详情 + 统计",
)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> SightReadingSessionResponse:
    session = await db.get(SightReadingSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your session")

    stats = SightReadingSessionStats(
        total_questions=session.total_questions or 0,
        correct_count=session.correct_count or 0,
        accuracy=session.accuracy or 0.0,
        streak_max=session.streak_max or 0,
        notes_per_minute=session.notes_per_minute or 0.0,
        duration_seconds=session.duration_seconds or 0.0,
    )

    return SightReadingSessionResponse(
        session_id=str(session.id),
        user_id=str(session.user_id),
        difficulty=session.difficulty,
        mode=session.mode,
        input_method=session.input_method,
        started_at=session.started_at,
        ended_at=session.ended_at,
        stats=stats,
    )
