"""
teaching_engine.py — 实时教学引擎(v2.0 大脑,L1+L2+L3+KG 融合)

设计目标:
- 把 MIDI 评估 / 错误聚类 / 乐理 KG / 学生历史 融合成"教学上下文"
- 注入 LLM prompt,让对话真正"懂你弹琴"
- 简单问题直接答(不浪费 LLM token)

核心功能:
1. 维护学生状态(最近一次评估、聚类画像、历史趋势)
2. 回答"简单问题"无需 LLM:
   - "我弹得怎么样" → 评估摘要
   - "多少分" → score
   - "我经常错哪里" → 聚类画像
   - "学什么曲子好" → 推荐(基于 L3)
3. 复杂问题构建"教学上下文"注入 LLM:
   - 最新评估 + 错误详情 + KG 风格 + 历史趋势

对位论文:
- Libretto (2509.14262) LLM 音乐结构理解
- MuseAgent (2407.03560) LLM 音乐助手
- ITS (Intelligent Tutoring Systems) 经典架构

用法:
    from teaching_engine import TeachingEngine
    eng = TeachingEngine()
    eng.set_latest_eval(eval_pitch_result)
    eng.set_history(history_json_path)
    
    # 直接答
    answer = eng.answer_directly("我弹得怎么样")
    if answer: print(answer)
    
    # 复杂问题:给 LLM 用
    ctx = eng.build_context_for_llm("巴洛克时期的触键要点")
    prompt = system + ctx + user_query
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# KG / 评估 / 聚类(都已在项目里)
try:
    from tonnetz_kg import MusicKG
except ImportError:
    MusicKG = None


# ----- 学生画像 -----
@dataclass
class StudentProfile:
    """学生状态(实时更新)"""
    name: str = "学生"
    pieces_played: int = 0
    avg_score: float = 0.0
    best_score: float = 0.0
    worst_score: float = 0.0
    total_pitch_errors: int = 0
    last_eval: dict = field(default_factory=dict)
    cluster_id: int = -1  # 错误模式聚类
    cluster_summary: str = ""
    trend: str = "stable"  # improving / stable / declining
    history: list = field(default_factory=list)  # 全部评估历史


# ----- 教学引擎 -----
class TeachingEngine:
    """v2.0 大脑:融合 MIDI 评估 + KG + 聚类 + 历史 → 教学上下文"""

    def __init__(self, kg_path: Optional[str] = None, history_path: Optional[str] = None):
        # 加载乐理 KG
        self.kg = None
        if MusicKG is not None:
            try:
                self.kg = MusicKG()
                if kg_path:
                    self.kg.load_from_file(kg_path)
            except Exception as e:
                print(f"[engine] KG 加载失败: {e}", file=sys.stderr)

        # 加载历史
        self.history: list[dict] = []
        if history_path and Path(history_path).exists():
            try:
                self.history = json.loads(Path(history_path).read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[engine] 历史加载失败: {e}", file=sys.stderr)

        # 学生画像
        self.profile = self._build_profile()

        # 最近一次评估(可被 set_latest_eval 覆盖)
        self.latest_eval: dict = {}

    # ----- 数据更新 -----
    def set_latest_eval(self, eval_result: dict, piece_name: str = "", period: str = ""):
        """用户弹完一段,塞评估结果进来"""
        self.latest_eval = dict(eval_result)
        if piece_name:
            self.latest_eval["piece"] = piece_name
        if period:
            self.latest_eval["period"] = period

        # 加进历史
        entry = {
            "piece": piece_name or eval_result.get("piece", "Unknown"),
            "period": period or eval_result.get("period_hint", "Unknown"),
            "score": eval_result.get("score", 0),
            "pitch_accuracy": eval_result.get("pitch_accuracy", 0),
            "timing_std_ms": eval_result.get("timing_std_ms", 0),
            "timing_mean_ms": eval_result.get("timing_mean_ms", 0),
            "velocity_correlation": eval_result.get("velocity_correlation", 0),
            "n_pitch_errors": eval_result.get("n_pitch_errors", 0),
        }
        self.history.append(entry)
        self.profile = self._build_profile()

    def set_history(self, history: list[dict]):
        """替换整个历史"""
        self.history = list(history)
        self.profile = self._build_profile()

    def _build_profile(self) -> StudentProfile:
        """从历史重建学生画像"""
        if not self.history:
            return StudentProfile()

        scores = [h.get("score", 0) for h in self.history]
        n = len(scores)
        # 趋势:后半 vs 前半
        if n >= 4:
            half = n // 2
            first_avg = sum(scores[:half]) / half
            second_avg = sum(scores[half:]) / (n - half)
            if second_avg - first_avg > 5:
                trend = "improving"
            elif first_avg - second_avg > 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        return StudentProfile(
            name="学生",
            pieces_played=n,
            avg_score=round(sum(scores) / n, 1),
            best_score=max(scores),
            worst_score=min(scores),
            total_pitch_errors=sum(h.get("n_pitch_errors", 0) for h in self.history),
            last_eval=self.history[-1] if self.history else {},
            cluster_id=-1,
            trend=trend,
            history=self.history,
        )

    # ----- 简单问题直答 -----
    def answer_directly(self, query: str) -> Optional[str]:
        """不调 LLM,直接基于学生数据回答

        支持的简单问题(命中返回答案,未命中返回 None)
        - "我弹得怎么样" / "我弹的如何" → 评估摘要
        - "多少分" / "分数" / "score" → score
        - "我经常错哪里" / "错误模式" → 聚类
        - "进步了吗" / "趋势" → trend
        - "我弹过什么" / "历史" → history 列表
        - "巴洛克" / "古典" / "浪漫" → KG 风格
        - "下一首要弹什么" / "推荐" → 推荐(简化版)
        """
        q = query.lower().strip()
        if not q:
            return None

        # 分数
        if any(k in q for k in ["多少分", "分数", "score", "得分"]):
            if self.latest_eval:
                s = self.latest_eval.get("score", 0)
                rating = "优秀" if s >= 95 else "良好" if s >= 85 else "中等" if s >= 70 else "需加强"
                return f"你这段 {s} 分,评级「{rating}」。"
            if self.profile.pieces_played:
                return f"你历史平均 {self.profile.avg_score} 分(共 {self.profile.pieces_played} 首)。"
            return "你还没弹过呢,先弹一段给我听?"

        # 弹得怎么样 / 评估
        if any(k in q for k in ["弹得怎么样", "弹的如何", "怎么样", "how did i", "刚才"]):
            if not self.latest_eval:
                return "你还没弹过呢,先弹一段给我评估一下?"
            ev = self.latest_eval
            n_err = ev.get("n_pitch_errors", 0)
            timing_std = ev.get("timing_std_ms", 0)
            return (
                f"你这段 {ev.get('score', 0)} 分,"
                f"错音 {n_err} 个,"
                f"节奏波动 {timing_std:.1f}ms。"
                f"{(ev.get('piece') or '这首曲子')} 是 {ev.get('period', '?')} 时期风格。"
            )

        # 错误模式 / 聚类
        if any(k in q for k in ["经常错", "错误模式", "我的弱点", "弱项", "哪里差"]):
            if len(self.history) < 2:
                return "再多弹几首,我才能识别你的错误模式。"
            # 简单统计:哪种指标最差
            avg_timing_std = sum(h.get("timing_std_ms", 0) for h in self.history) / len(self.history)
            avg_velocity = sum(h.get("velocity_correlation", 0) for h in self.history) / len(self.history)
            avg_pitch_acc = sum(h.get("pitch_accuracy", 0) for h in self.history) / len(self.history)
            weak_parts = []
            if avg_pitch_acc < 0.9:
                weak_parts.append(f"音准 {avg_pitch_acc*100:.0f}%")
            if avg_timing_std > 30:
                weak_parts.append(f"节奏波动 {avg_timing_std:.0f}ms")
            if avg_velocity < 0.3:
                weak_parts.append(f"力度跟随 {avg_velocity:.2f}")
            if not weak_parts:
                return "你的综合指标都不错,继续保持!"
            return f"你的主要弱点:{' / '.join(weak_parts)}。"

        # 进步 / 趋势
        if any(k in q for k in ["进步", "趋势", "trend", "最近"]):
            if self.profile.pieces_played < 2:
                return "样本太少,多弹几首才能看趋势。"
            trend_map = {"improving": "📈 在进步!", "stable": "→ 持平中", "declining": "📉 最近下滑,可能状态不好"}
            return f"最近 {self.profile.pieces_played} 首:平均 {self.profile.avg_score} 分,{trend_map[self.profile.trend]}"

        # 弹过什么 / 历史
        if any(k in q for k in ["弹过什么", "历史", "history", "记录"]):
            if not self.history:
                return "你还没弹过呢,先弹一段?"
            recent = self.history[-5:]
            lines = [f"  - {h.get('piece', '?')}({h.get('period', '?')}):{h.get('score', 0)} 分" for h in recent]
            return f"最近弹过 {len(self.history)} 首:\n" + "\n".join(lines)

        # 时期风格
        for period in ["巴洛克", "baroque", "古典", "classical", "浪漫", "romantic"]:
            if period in q:
                return self._kg_style_hint(period.split("/")[0].title() if "/" in period else period)

        # 推荐 / 下一首
        if any(k in q for k in ["下一首", "推荐", "弹什么", "recommend"]):
            return self._recommend_simple()

        return None  # 未命中,需要 LLM

    def _kg_style_hint(self, period: str) -> str:
        """从 KG 拉时期风格提示"""
        if self.kg is None:
            return f"{period} 时期:风格独特,需了解时代背景。"
        # 简化:硬编码 3 个时期
        hints = {
            "Baroque": "巴洛克时期(1600-1750):对位清晰、装饰音有规律(trill/mordent)、触键颗粒分明、强弱对比突然。代表:巴赫、亨德尔、斯卡拉蒂。",
            "Classical": "古典时期(1750-1820):句法清晰、优雅平衡、装饰克制、力度渐变。代表:海顿、莫扎特、贝多芬早期。",
            "Romantic": "浪漫时期(1820-1900):情感丰富、rubato 自由、和声复杂、力度极端对比。代表:肖邦、李斯特、舒曼。",
        }
        # 兼容中文/英文
        period_map = {"巴洛克": "Baroque", "古典": "Classical", "浪漫": "Romantic"}
        en = period_map.get(period, period)
        return hints.get(en, f"{period}:未知时期。")

    def _recommend_simple(self) -> str:
        """简化版推荐(基于 cluster + 趋势)"""
        if self.profile.pieces_played == 0:
            return "建议从拜厄或车尔尼 599 开始,基础练习曲。"
        if self.profile.avg_score >= 90:
            return "你的水平不错,可以挑战:肖邦圆舞曲 / 贝多芬奏鸣曲 Op.49。"
        if self.profile.avg_score >= 80:
            return "推荐继续:巴赫小前奏曲 / 莫扎特奏鸣曲 K.545。"
        if self.profile.avg_score >= 70:
            return "推荐加强基础:车尔尼 599 后半 / 哈农练习曲。"
        return "建议从拜厄 100 条左右的基础练习重新打基础。"

    # ----- 复杂问题 → LLM 上下文 -----
    def build_context_for_llm(self, user_query: str) -> str:
        """构建注入 LLM prompt 的教学上下文"""
        parts = []

        # 1. 学生画像摘要
        p = self.profile
        parts.append(f"## 学生画像")
        parts.append(f"- 已弹 {p.pieces_played} 首,平均 {p.avg_score} 分,趋势:{p.trend}")
        if p.total_pitch_errors:
            parts.append(f"- 累计错音 {p.total_pitch_errors} 个")
        if p.worst_score:
            parts.append(f"- 历史区间:{p.worst_score}-{p.best_score} 分")

        # 2. 最近一次评估详情
        if self.latest_eval:
            ev = self.latest_eval
            parts.append(f"\n## 最近评估")
            parts.append(f"- 曲目:{ev.get('piece', '?')}({ev.get('period', '?')})")
            parts.append(f"- 评分:{ev.get('score', 0)}")
            parts.append(f"- 错音:{ev.get('n_pitch_errors', 0)} 个,音准率 {ev.get('pitch_accuracy', 0)*100:.1f}%")
            parts.append(f"- 节奏偏差:{ev.get('timing_mean_ms', 0):.1f}ms,波动 {ev.get('timing_std_ms', 0):.1f}ms")
            parts.append(f"- 力度相关性:{ev.get('velocity_correlation', 0):.2f}")
            # 错音样本
            samples = ev.get("pitch_error_samples", [])
            if samples:
                sample_strs = []
                for s in samples[:3]:
                    ref = s.get("ref_note", s.get("ref_pitch", "?"))
                    usr = s.get("user_note", s.get("user_pitch", "?"))
                    sample_strs.append(f"{ref}→{usr}")
                parts.append(f"- 错音样本:{sample_strs}")

        # 3. 历史趋势
        if len(self.history) >= 3:
            recent = self.history[-3:]
            parts.append(f"\n## 最近 3 首")
            for h in recent:
                parts.append(f"  - {h.get('piece', '?')}({h.get('period', '?')}):{h.get('score', 0)} 分, {h.get('n_pitch_errors', 0)} 错音")

        # 4. KG 上下文(根据 query 关键词)
        if self.kg is not None:
            # 简单匹配:query 里出现的时期/作曲家
            keywords = []
            for kw in ["巴洛克", "Baroque", "古典", "Classical", "浪漫", "Romantic", "巴赫", "Bach", "莫扎特", "Mozart", "肖邦", "Chopin"]:
                if kw.lower() in user_query.lower():
                    keywords.append(kw)
            if keywords:
                parts.append(f"\n## KG 上下文")
                for kw in keywords:
                    parts.append(f"- {kw}:{self._kg_style_hint(kw)}")

        return "\n".join(parts)

    # ----- 全状态导出 -----
    def export_state(self) -> dict:
        """导出整个引擎状态(便于持久化)"""
        return {
            "latest_eval": self.latest_eval,
            "profile": {
                "pieces_played": self.profile.pieces_played,
                "avg_score": self.profile.avg_score,
                "best_score": self.profile.best_score,
                "worst_score": self.profile.worst_score,
                "total_pitch_errors": self.profile.total_pitch_errors,
                "trend": self.profile.trend,
            },
            "history_size": len(self.history),
        }


# ----- 集成 voice_dialog -----
def patch_voice_dialog(engine: TeachingEngine):
    """给 voice_dialog 注入教学引擎 — 让 mock LLM 也能用真实学生数据"""
    import voice_dialog

    original_mock = voice_dialog._mock_llm
    original_call = voice_dialog.call_llm

    def patched_call_llm(messages, backend="mock", **kwargs):
        """增强版 LLM 调用:先尝试 direct answer,再 fallback LLM"""
        last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
        if last_user and backend == "mock":
            direct = engine.answer_directly(last_user["content"])
            if direct:
                return direct
        return original_call(messages, backend=backend, **kwargs)

    def patched_build_messages(state, max_turns=6):
        """增强版 messages:把教学上下文注入 system prompt"""
        msgs = original_build_messages(state, max_turns)
        if msgs and msgs[0]["role"] == "system":
            last_user = next((m for m in reversed(msgs) if m["role"] == "user"), None)
            if last_user:
                ctx = engine.build_context_for_llm(last_user["content"])
                msgs[0]["content"] = msgs[0]["content"] + "\n\n" + ctx
        return msgs

    original_build_messages = voice_dialog.DialogState.build_messages
    voice_dialog.DialogState.build_messages = patched_build_messages
    voice_dialog.call_llm = patched_call_llm

    return engine


# ----- CLI 测试 -----
def main():
    import argparse
    parser = argparse.ArgumentParser(description="实时教学引擎测试")
    parser.add_argument("--history", help="学生历史 JSON 路径")
    parser.add_argument("--query", help="测试 query")
    args = parser.parse_args()

    engine = TeachingEngine(history_path=args.history)

    # 模拟一次评估
    fake_eval = {
        "score": 88.5,
        "pitch_accuracy": 0.92,
        "timing_mean_ms": -8.5,
        "timing_std_ms": 12.3,
        "velocity_correlation": 0.4,
        "n_pitch_errors": 1,
        "pitch_error_samples": [{"type": "wrong", "ref_note": 4, "user_note": 3}],
    }
    engine.set_latest_eval(fake_eval, piece_name="Minuet in G", period="Baroque")

    print("=== 学生画像 ===")
    print(json.dumps(engine.export_state(), ensure_ascii=False, indent=2))

    if args.query:
        print(f"\n=== Q: {args.query} ===")
        direct = engine.answer_directly(args.query)
        if direct:
            print(f"A (direct): {direct}")
        else:
            print(f"A (need LLM): {engine.build_context_for_llm(args.query)}")
    else:
        # 默认测试
        print("\n=== Direct Answer 测试 ===")
        test_qs = ["我弹得怎么样", "多少分", "我经常错哪里", "巴洛克", "下一首弹什么", "你好"]
        for q in test_qs:
            a = engine.answer_directly(q)
            print(f"Q: {q}")
            print(f"A: {a or '(需要 LLM)'}\n")


if __name__ == "__main__":
    main()
