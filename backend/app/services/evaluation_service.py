"""
Evaluation Service — 5 维评估编排
==================================

从 v3.0 模块复用:
- eval_pitch: 音高 + 节奏 + 力度
- expressiveness: 9 维表现力
- hand_pose: 9 维手型(从视频/landmarks)
- sight_reading: 4 难度 × 3 模式视奏(此处只占位,A4.5 完整实现)
- senior_mode: 文本简化(银发模式)

返回 5 维分数字典 + 综合分 + 反馈建议
"""
from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.services import eval_pitch, expressiveness, hand_pose

# 用 stdlib logger(简单可靠,不出 structlog 兼容问题)
logger = logging.getLogger("copiano.eval")


# ──────────────────────────────────────────────
# 5 维权重 (与 v3.0 论文一致 + User 模型 WEIGHTS)
# ──────────────────────────────────────────────
WEIGHTS = {
    "pitch": 0.20,
    "expressiveness": 0.25,
    "hand_pose": 0.20,
    "rhythm": 0.20,        # rhythm 和 pitch 在 eval_pitch 里一起算
    "sight_reading": 0.15,  # 视奏分数(从 sight_reading 训练记录)
}


@dataclass
class EvaluationResult:
    """5 维评估结果"""
    # 5 维分数 (0-1)
    pitch_score: float = 0.0
    expressiveness_score: float = 0.0
    hand_pose_score: float = 0.0
    rhythm_score: float = 0.0
    sight_reading_score: float = 0.0

    # 综合分
    overall_score: float = 0.0

    # 详细数据(可选,前端展示用)
    pitch_detail: dict[str, Any] = field(default_factory=dict)
    expressiveness_detail: dict[str, Any] = field(default_factory=dict)
    hand_pose_detail: dict[str, Any] = field(default_factory=dict)

    # 反馈
    teaching_tips: list[str] = field(default_factory=list)

    # 元数据
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


# ──────────────────────────────────────────────
# Service 类
# ──────────────────────────────────────────────
class EvaluationService:
    """5 维评估服务"""

    def __init__(self) -> None:
        pass

    def evaluate_pitch(
        self,
        reference_midi: str | Path,
        user_midi: str | Path,
    ) -> dict[str, Any]:
        """D1 音高 + D4 节奏 + 力度(用 v3.0 eval_pitch)

        v3.0 返回 score/pitch_accuracy/timing_mean_ms/velocity_correlation 等
        这里映射为 0-1 标准化字段:
        - pitch_score: pitch_accuracy (1 - 错音率)
        - rhythm_score: 1 - normalized |timing_mean_ms| / 200
        - velocity_correlation: 0-1 (已经是)
        """
        start = time.perf_counter()
        raw = eval_pitch.evaluate(str(reference_midi), str(user_midi))
        duration_ms = int((time.perf_counter() - start) * 1000)

        pitch_accuracy = raw.get("pitch_accuracy", 0.0)
        timing_mean = abs(raw.get("timing_mean_ms", 0.0))
        # 节奏: 时偏 0ms 满分,200ms 零分
        rhythm_score = max(0.0, 1.0 - timing_mean / 200.0)
        # 力度: v3.0 给的是 -1~1 相关性,映射到 0~1
        vel_corr = raw.get("velocity_correlation", 0.0)
        vel_score = (vel_corr + 1) / 2  # -1→0, 0→0.5, 1→1

        result = {
            "pitch_score": round(pitch_accuracy, 4),
            "rhythm_score": round(rhythm_score, 4),
            "velocity_score": round(vel_score, 4),
            "raw": raw,
        }
        # stdlib 风格日志(避免 structlog 兼容问题)
        logger.info(
            "pitch_eval_done duration_ms=%d pitch=%.3f rhythm=%.3f",
            duration_ms, result["pitch_score"], result["rhythm_score"],
        )
        return result

    def evaluate_expressiveness(
        self,
        user_midi: str | Path,
        period_hint: str = "",
    ) -> dict[str, Any]:
        """D2 表现力(9 维)"""
        start = time.perf_counter()
        profile = expressiveness.analyze_expressiveness(
            user_midi, period_hint=period_hint
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("expressiveness_eval_done duration_ms=%d", duration_ms)

        # 转为 dict(ExpressivenessProfile 是 dataclass)
        # 注: v3.0 的 overall 是 0-100,这里保留原值
        return {
            "overall": profile.overall,
            "dimensions": {
                "velocity_mean": profile.velocity_mean,
                "velocity_std": profile.velocity_std,
                "dynamic_range": profile.dynamic_range,
                "ltv": profile.ltv,
                "voicing_balance": profile.voicing_balance,
                "melody_lead_ms": profile.melody_lead_ms,
                "touch_speed": profile.touch_speed,
                "articulation": profile.articulation,
                "release_var": profile.release_var,
            },
            "period_hint": period_hint,
        }

    def evaluate_hand_pose(
        self,
        landmarks: list[dict],
        left_landmarks: Optional[list[dict]] = None,
        right_landmarks: Optional[list[dict]] = None,
    ) -> dict[str, Any]:
        """D3 手型(9 维,从 MediaPipe 21 关键点)"""
        start = time.perf_counter()
        result = hand_pose.analyze_hand_pose(
            landmarks,
            left_landmarks=left_landmarks,
            right_landmarks=right_landmarks,
        )
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info("hand_pose_eval_done duration_ms=%d", duration_ms)
        return result

    def evaluate_full(
        self,
        reference_midi: Optional[str | Path] = None,
        user_midi: Optional[str | Path] = None,
        hand_landmarks: Optional[list[dict]] = None,
        sight_reading_score: Optional[float] = None,
        period_hint: str = "",
    ) -> EvaluationResult:
        """完整 5 维评估(可部分维度)

        Args:
            reference_midi: 参考演奏 MIDI
            user_midi: 用户演奏 MIDI
            hand_landmarks: MediaPipe 21 关键点(可选)
            sight_reading_score: 视奏分(从 sight_reading 训练记录读)
            period_hint: 风格提示(baroque/classical/romantic)

        Returns:
            EvaluationResult 完整 5 维 + 综合分 + 教学建议
        """
        start = time.perf_counter()
        result = EvaluationResult()

        # 1. Pitch + Rhythm
        if reference_midi and user_midi:
            try:
                pitch_data = self.evaluate_pitch(reference_midi, user_midi)
                result.pitch_score = pitch_data.get("pitch_score", 0.0)
                result.rhythm_score = pitch_data.get("rhythm_score", 0.0)
                result.pitch_detail = pitch_data
            except Exception as e:
                logger.exception("pitch_eval_failed: %s", e)

        # 2. Expressiveness (overall 0-100 → 0-1)
        if user_midi:
            try:
                exp_data = self.evaluate_expressiveness(user_midi, period_hint)
                result.expressiveness_score = exp_data.get("overall", 0.0) / 100.0
                result.expressiveness_detail = exp_data
            except Exception as e:
                logger.exception("expressiveness_eval_failed: %s", e)

        # 3. Hand pose
        if hand_landmarks:
            try:
                hp_data = self.evaluate_hand_pose(hand_landmarks)
                result.hand_pose_score = hp_data.get("overall", 0.0) / 100.0
                result.hand_pose_detail = hp_data
            except Exception as e:
                logger.exception("hand_pose_eval_failed: %s", e)

        # 4. Sight reading (从外部传入)
        if sight_reading_score is not None:
            result.sight_reading_score = sight_reading_score

        # 5. 综合分
        result.overall_score = round(
            result.pitch_score * WEIGHTS["pitch"]
            + result.expressiveness_score * WEIGHTS["expressiveness"]
            + result.hand_pose_score * WEIGHTS["hand_pose"]
            + result.rhythm_score * WEIGHTS["rhythm"]
            + result.sight_reading_score * WEIGHTS["sight_reading"],
            4,
        )

        # 6. 教学建议
        result.teaching_tips = self._generate_tips(result)

        result.duration_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "full_eval_done overall=%.3f duration_ms=%d",
            result.overall_score, result.duration_ms,
        )

        return result

    @staticmethod
    def _generate_tips(result: EvaluationResult) -> list[str]:
        """根据 5 维分数生成简短建议"""
        tips = []
        if result.pitch_score < 0.7:
            tips.append("错音较多,建议先慢练,逐句核对音高")
        if result.rhythm_score < 0.7:
            tips.append("节奏不稳,建议配合节拍器练习")
        if result.expressiveness_score < 0.6:
            tips.append("表现力可以更丰富,试试渐强渐弱、呼吸感")
        if result.hand_pose_score < 0.6:
            tips.append("注意手型放松,手腕不要压太低")
        if result.sight_reading_score < 0.6:
            tips.append("视奏能力有提升空间,建议多练 sight reading")
        if not tips:
            tips.append("整体表现优秀,继续保持!")
        return tips


# Singleton
evaluation_service = EvaluationService()
