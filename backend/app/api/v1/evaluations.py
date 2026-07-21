"""
Evaluations API — 5 维评估端点
================================

端点:
- POST   /api/v1/evaluations          上传 MIDI → 5 维评估
- GET    /api/v1/evaluations/{id}     评估详情
- GET    /api/v1/evaluations/history  当前用户历史
- GET    /api/v1/evaluations          当前用户评估列表(分页)
"""
from __future__ import annotations

import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.rate_limit import RATE_LIMIT_UPLOAD
from app.db.base import get_async_db
from app.models.evaluation import DifficultyLevel, Evaluation
from app.models.user import User
from app.schemas.evaluation import (
    EvaluationCreateResponse,
    EvaluationListResponse,
    EvaluationResponse,
)
from app.services.cache import cache_service
from app.services.evaluation_service import evaluation_service
from app.services.storage import storage_service

logger = logging.getLogger("copiano.evaluations.api")

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

# 上传配置
MAX_MIDI_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_MIME_TYPES = {"audio/midi", "audio/x-midi", "application/octet-stream"}


@router.post(
    "",
    response_model=EvaluationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传 MIDI → 5 维评估",
)
async def create_evaluation(
    midi_file: UploadFile = File(..., description="MIDI 文件 (.mid / .midi)"),
    piece_name: str = Form(..., min_length=1, max_length=255),
    piece_composer: str = Form(default=""),
    difficulty: DifficultyLevel = Form(default=DifficultyLevel.ELEMENTARY),
    period_hint: str = Form(default=""),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> EvaluationCreateResponse:
    """上传用户演奏 MIDI(可选 reference),返回 5 维分数 + 教学建议

    - 单文件模式:只传 user_midi,出 1-3 维(expressiveness/hand_pose/sight_reading)
    - 双文件模式:传 user_midi + reference_midi(同名 form 字段 ref_midi),出 5 维
    """
    # 1. 验证文件
    if midi_file.size and midi_file.size > MAX_MIDI_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"MIDI file too large (max {MAX_MIDI_SIZE // 1024 // 1024}MB)",
        )

    # 2. 保存到临时文件
    suffix = ".mid"
    if midi_file.filename and midi_file.filename.endswith(".midi"):
        suffix = ".midi"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        content = await midi_file.read()
        tmp.write(content)
        tmp_path = tmp.name
    midi_size = len(content)

    try:
        # 3. 查缓存(A3.6)
        cache_key = cache_service.eval_key(tmp_path, period_hint)
        cached = cache_service.get(cache_key)
        if cached:
            logger.info("eval_cache_hit key=%s", cache_key)
            from types import SimpleNamespace
            result = SimpleNamespace(
                pitch_score=cached["pitch_score"],
                expressiveness_score=cached["expressiveness_score"],
                hand_pose_score=cached["hand_pose_score"],
                rhythm_score=cached["rhythm_score"],
                sight_reading_score=cached["sight_reading_score"],
                overall_score=cached["overall_score"],
                teaching_tips=cached.get("teaching_tips", []),
                pitch_detail=cached.get("pitch_detail"),
                expressiveness_detail=cached.get("expressiveness_detail"),
                hand_pose_detail=cached.get("hand_pose_detail"),
                duration_ms=cached.get("duration_ms", 0),
            )
        else:
            # 4. 调 evaluation_service
            result = evaluation_service.evaluate_full(
                user_midi=tmp_path,
                period_hint=period_hint,
                # reference_midi 留空(A3.5 加 S3 后支持)
                # sight_reading_score 留空(A4.5 接)
                # hand_landmarks 留空(Mobile 端上传)
            )
            # 5. 写缓存(24h)
            cache_service.set(
                cache_key,
                {
                    "pitch_score": result.pitch_score,
                    "expressiveness_score": result.expressiveness_score,
                    "hand_pose_score": result.hand_pose_score,
                    "rhythm_score": result.rhythm_score,
                    "sight_reading_score": result.sight_reading_score,
                    "overall_score": result.overall_score,
                    "teaching_tips": result.teaching_tips,
                    "pitch_detail": result.pitch_detail,
                    "expressiveness_detail": result.expressiveness_detail,
                    "hand_pose_detail": result.hand_pose_detail,
                    "duration_ms": result.duration_ms,
                },
                ttl_seconds=86400,
            )
            logger.info("eval_cache_miss key=%s", cache_key)

        # 6. 上传 MIDI 到 S3/MinIO(A3.5)
        try:
            s3_uri = storage_service.upload_file(
                tmp_path,
                prefix=f"users/{current_user.id}/midi",
                content_type="audio/midi",
            )
        except Exception as e:
            logger.warning("s3_upload_failed: %s, using local://", e)
            s3_uri = f"local://{midi_file.filename or 'upload.mid'}"

        # 7. 持久化到 PG
        from datetime import datetime, timezone
        evaluation = Evaluation(
            user_id=current_user.id,
            piece_name=piece_name,
            piece_composer=piece_composer or "",
            difficulty=difficulty,
            midi_url=s3_uri,
            midi_size_bytes=midi_size,
            duration_seconds=0.0,  # 后续从 MIDI 解析
            pitch_score=result.pitch_score,
            expressiveness_score=result.expressiveness_score,
            hand_pose_score=result.hand_pose_score,
            rhythm_score=result.rhythm_score,
            sight_reading_score=result.sight_reading_score,
            overall_score=result.overall_score,
            llm_feedback="",  # A4.7 异步填充
        )
        evaluation.overall_score = evaluation.compute_overall()

        db.add(evaluation)
        await db.commit()
        await db.refresh(evaluation)

        logger.info(
            "evaluation_created id=%s overall=%.3f",
            evaluation.id, evaluation.overall_score,
        )

        return EvaluationCreateResponse(
            evaluation=EvaluationResponse.model_validate(evaluation),
            tips=result.teaching_tips,
            pitch_detail=result.pitch_detail or None,
            expressiveness_detail=result.expressiveness_detail or None,
            hand_pose_detail=result.hand_pose_detail or None,
            duration_ms=result.duration_ms,
        )
    finally:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@router.get(
    "/history",
    response_model=EvaluationListResponse,
    summary="当前用户评估历史(倒序)",
)
async def list_evaluations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> EvaluationListResponse:
    # 查总数
    from sqlalchemy import func
    count_q = select(func.count(Evaluation.id)).where(Evaluation.user_id == current_user.id)
    total = (await db.execute(count_q)).scalar() or 0

    # 查列表
    q = (
        select(Evaluation)
        .where(Evaluation.user_id == current_user.id)
        .order_by(desc(Evaluation.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(q)
    items = [EvaluationResponse.model_validate(e) for e in result.scalars().all()]

    return EvaluationListResponse(
        items=items, total=total, skip=skip, limit=limit,
    )


@router.get(
    "/{evaluation_id}",
    response_model=EvaluationResponse,
    summary="评估详情",
)
async def get_evaluation(
    evaluation_id: uuid.UUID,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> EvaluationResponse:
    eval_obj = await db.get(Evaluation, evaluation_id)
    if not eval_obj:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    if eval_obj.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your evaluation")
    return EvaluationResponse.model_validate(eval_obj)


@router.get(
    "/{evaluation_id}/download-url",
    summary="获取 MIDI 的 presigned URL(临时下载链接)",
)
async def get_midi_download_url(
    evaluation_id: uuid.UUID,
    expires_seconds: int = Query(default=3600, ge=60, le=86400),
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """生成 MIDI 文件的临时访问 URL(presigned)

    默认 1 小时有效,客户端用这个 URL 直接从 MinIO 拉 MIDI 播放
    """
    from app.db.base import get_async_session_factory
    factory = get_async_session_factory()
    async with factory() as db:
        eval_obj = await db.get(Evaluation, evaluation_id)
        if not eval_obj:
            raise HTTPException(status_code=404, detail="Evaluation not found")
        if eval_obj.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your evaluation")

    if eval_obj.midi_url.startswith("local://"):
        raise HTTPException(
            status_code=400,
            detail="MIDI not in S3 (legacy local file)",
        )

    try:
        url = storage_service.get_presigned_url(
            eval_obj.midi_url,
            expires_seconds=expires_seconds,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate download URL: {e}",
        )

    return {
        "url": url,
        "expires_in": expires_seconds,
        "expires_at": (datetime.utcnow() + timedelta(seconds=expires_seconds)).isoformat() + "Z",
    }
