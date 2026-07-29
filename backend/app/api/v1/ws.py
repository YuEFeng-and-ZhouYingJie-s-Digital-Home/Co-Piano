"""
WebSocket 端点 — LLM 流式响应
==================================

端点:
- WS /api/v1/ws/llm?token=<JWT>&evaluation_id=<uuid>

协议:
1. 客户端连接 (带 JWT token query param + evaluation_id)
2. 服务端验证 token + 评估归属
3. 服务端调 LLM,流式 send 文本片段
4. 最后 send done 表示结束
5. 客户端 close

消息格式(JSON):
  {"type": "chunk", "content": "..."}
  {"type": "done", "model": "qwen2.5-7b-instruct", "backend": "qwen", "total_tokens": 80}
  {"type": "error", "message": "..."}

注: 这里用简化版 streaming(整段返回 → 分块推送),完整 SSE 流由前端 WebSocket 处理
"""
from __future__ import annotations

import logging
import uuid

import jwt
from fastapi import (
    APIRouter,
    Query,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.models.evaluation import Evaluation
from app.models.user import User
from app.services.llm_service import llm_service

logger = logging.getLogger("copiano.ws")

router = APIRouter()


async def _authenticate_ws(token: str, db: AsyncSession) -> User | None:
    """WebSocket 鉴权(从 query param 拿 JWT)"""
    try:
        payload = decode_token(token, expected_type="access")
    except jwt.PyJWTError as e:
        logger.warning("ws_auth_failed: %s", e)
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        return None
    return user


async def _verify_evaluation(
    db: AsyncSession, evaluation_id: str, user: User
) -> Evaluation | None:
    """验证评估存在 + 归属"""
    try:
        eid = uuid.UUID(evaluation_id)
    except ValueError:
        return None
    evaluation = await db.get(Evaluation, eid)
    if not evaluation or evaluation.user_id != user.id:
        return None
    return evaluation


@router.websocket("/ws/llm")
async def websocket_llm(
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
    evaluation_id: str = Query(..., description="评估 ID"),
    prefer: str = Query(default="qwen", description="qwen | openai | auto"),
):
    """WebSocket LLM 流式反馈端点"""
    await websocket.accept()

    # 用 FastAPI dependency 注入 DB session(可被 test 覆盖)
    from app.db.base import get_async_session_factory
    factory = get_async_session_factory()

    # 注:WebSocket 不能用 FastAPI Depends,只能手动管理 session
    # 鉴权阶段
    async with factory() as db:
        user = await _authenticate_ws(token, db)
        if not user:
            await websocket.send_json({
                "type": "error",
                "message": "Unauthorized: invalid or expired token",
            })
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 验证 evaluation
        evaluation = await _verify_evaluation(db, evaluation_id, user)
        if not evaluation:
            await websocket.send_json({"type": "error", "message": "Evaluation not found or not yours"})
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # 准备 LLM 输入
        eval_dict = {
            "piece_name": evaluation.piece_name,
            "pitch_score": evaluation.pitch_score,
            "expressiveness_score": evaluation.expressiveness_score,
            "hand_pose_score": evaluation.hand_pose_score,
            "rhythm_score": evaluation.rhythm_score,
            "sight_reading_score": evaluation.sight_reading_score,
            "overall_score": evaluation.overall_score,
        }
        eid = evaluation.id

    # 流式生成 LLM
    try:
        llm_resp = await llm_service.generate_feedback(
            eval_dict, user_age=user.age
        )
        full_content = llm_resp.content

        # 分块推送(每 20 字符一块)
        chunk_size = 20
        for i in range(0, len(full_content), chunk_size):
            chunk = full_content[i:i + chunk_size]
            await websocket.send_json({
                "type": "chunk",
                "content": chunk,
            })

        # 持久化到 PG
        async with factory() as db:
            evaluation = await db.get(Evaluation, eid)
            if evaluation:
                evaluation.llm_feedback = full_content
                evaluation.llm_model = llm_resp.model
                evaluation.llm_latency_ms = llm_resp.latency_ms
                await db.commit()

        # 发送 done
        await websocket.send_json({
            "type": "done",
            "model": llm_resp.model,
            "backend": llm_resp.backend,
            "total_tokens": llm_resp.total_tokens,
            "latency_ms": llm_resp.latency_ms,
        })

        logger.info(
            "ws_feedback_done user=%s evaluation=%s backend=%s",
            user.id, eid, llm_resp.backend,
        )

    except WebSocketDisconnect:
        logger.info("ws_disconnected")
        return
    except Exception as e:
        logger.exception("ws_error: %s", e)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
