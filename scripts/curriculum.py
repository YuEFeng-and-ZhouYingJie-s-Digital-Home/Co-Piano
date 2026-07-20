"""
curriculum.py — 自适应课程规划(CoPiano v2.0 的 5.8)

基于学生 DB + KG + L3 bandit,生成多天练习计划。

设计:
- 输入:学生 DB(水平/弱项/掌握/进行中)+ 可用时间(分钟/天)+ 天数
- 算法:
  1. 分析学生当前水平(从 DB 平均分)
  2. 选 N 首目标曲目(从 KG 候选 + DB in_progress 平衡)
  3. 排成 N 天 schedule(渐进难度 + 间隔复习)
  4. 每天 = 热身 + 主曲 + 弱项专练 + 复习
- 输出:7 天计划(含每日目标、推荐曲目、时长、技术点)

对位论文:
- 2501.10222 Integrated Expressive Piano(自适应)
- 2509.08800 PianoVAM(多模态数据集)
- 经典 ITS 智能辅导系统(练习序列优化)

用法:
    from curriculum import CurriculumPlanner
    from student_db import StudentDB
    
    db = StudentDB('yuefeng')
    planner = CurriculumPlanner(db, time_per_day_min=30)
    plan = planner.generate_week_plan(days=7)
    print(plan.format())
"""
from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from tonnetz_kg import MusicKG
except ImportError:
    MusicKG = None

try:
    from student_db import StudentDB
except ImportError:
    StudentDB = None


# ----- 数据结构 -----
@dataclass
class DayPlan:
    """一天的计划"""
    day_num: int  # 1-7
    date: str  # YYYY-MM-DD
    theme: str  # "复习日" / "新曲日" / "弱项日" / "休息"
    duration_min: int
    warmup: dict = field(default_factory=dict)  # {"piece": "Hanon No.1", "minutes": 5, "focus": "手指独立"}
    main_piece: dict = field(default_factory=dict)  # {"piece": "Bach Prelude", "minutes": 15, "target_score": 90, "focus": "音 4 / 音 7 准确性"}
    review: dict = field(default_factory=dict)  # {"piece": "Minuet in G", "minutes": 8, "notes": "重点改 m.1 第 4 拍"}
    cooldown: dict = field(default_factory=dict)  # {"piece": "Twinkle", "minutes": 2, "notes": "放松"}
    daily_goals: list = field(default_factory=list)  # ["达到 90 分", "零错音", "legato 流畅"]


# ----- 候选曲目库(基于 KG 简化的 5 难度档)-----
REPERTOIRE_BY_LEVEL = {
    # level: (score 范围, 时期, 难度, 代表曲目)
    "beginner": [
        {"piece": "Beyer Op.101 No.1", "period": "Baroque", "difficulty": 1, "key_focus": ["finger independence", "5-finger position"]},
        {"piece": "Twinkle Twinkle Little Star", "period": "Romantic", "difficulty": 1, "key_focus": ["basic rhythm", "even notes"]},
        {"piece": "Hanon Exercise No.1", "period": "Classical", "difficulty": 2, "key_focus": ["finger strength", "5-finger pattern"]},
    ],
    "elementary": [
        {"piece": "Minuet in G (Bach)", "period": "Baroque", "difficulty": 2, "key_focus": ["two-voice", "evenness"]},
        {"piece": "Sonatina Op.36 No.1 (Clementi)", "period": "Classical", "difficulty": 3, "key_focus": ["sonata form", "scale passages"]},
        {"piece": "Für Elise (Beethoven)", "period": "Classical", "difficulty": 3, "key_focus": "expressiveness"},
    ],
    "intermediate": [
        {"piece": "Bach Prelude in C (BWV 846)", "period": "Baroque", "difficulty": 4, "key_focus": ["16th notes", "voice independence"]},
        {"piece": "Sonata K.545 1st mvt (Mozart)", "period": "Classical", "difficulty": 4, "key_focus": ["Alberti bass", "light touch"]},
        {"piece": "Chopin Nocturne Op.9 No.2", "period": "Romantic", "difficulty": 5, "key_focus": ["rubato", "chord voicing"]},
    ],
    "advanced": [
        {"piece": "Beethoven Sonata Op.27 No.2 (Moonlight)", "period": "Classical", "difficulty": 6, "key_focus": ["pedaling", "expressive dynamics"]},
        {"piece": "Chopin Etude Op.10 No.3 (Tristesse)", "period": "Romantic", "difficulty": 7, "key_focus": ["legato", "emotional flow"]},
        {"piece": "Liszt Liebestraum No.3", "period": "Romantic", "difficulty": 8, "key_focus": ["octaves", "rubato"]},
    ],
}

# 关键词 → 曲目映射(根据学生问的或弱项)
KEYWORD_TO_FOCUS = {
    "对位": "voice independence",
    "装饰音": "ornamentation",
    "legato": "legato",
    "staccato": "staccato",
    "rubato": "rubato",
    "踏板": "pedaling",
    "音阶": "scales",
    "琶音": "arpeggios",
    "八度": "octaves",
    "trill": "ornamentation",
    "巴洛克": "ornamentation",
    "古典": "Alberti bass",
    "浪漫": "rubato",
}


def _level_from_score(avg_score: float) -> str:
    if avg_score < 75:
        return "beginner"
    if avg_score < 85:
        return "elementary"
    if avg_score < 92:
        return "intermediate"
    return "advanced"


# ----- 规划器 -----
class CurriculumPlanner:
    """自适应课程规划器"""

    def __init__(self, db=None, time_per_day_min: int = 30, days: int = 7):
        self.db = db
        self.time_per_day = time_per_day_min
        self.days = days
        self.kg = MusicKG() if MusicKG else None

    # ----- 主入口 -----
    def generate_plan(self) -> list[DayPlan]:
        """生成 N 天计划"""
        if not self.db or not self.db.data["evaluations"]:
            return self._default_plan()

        # 1. 分析学生状态
        student_level = self._student_level()
        weak_areas = self.db.get_weak_areas(top_n=3)
        in_progress = self.db.get_in_progress_pieces()
        mastered = self.db.get_mastered_pieces()

        # 2. 选目标曲目
        target_pieces = self._select_target_pieces(student_level, in_progress)

        # 3. 排 7 天
        return self._schedule_days(target_pieces, weak_areas, in_progress, mastered)

    def _default_plan(self) -> list[DayPlan]:
        """无数据时的默认计划"""
        plan = []
        for d in range(1, self.days + 1):
            plan.append(DayPlan(
                day_num=d,
                date=(datetime.now() + timedelta(days=d - 1)).strftime("%Y-%m-%d"),
                theme="新起点" if d == 1 else "基础练习",
                duration_min=self.time_per_day,
                warmup={"piece": "Hanon No.1", "minutes": 5, "focus": "5-finger 模式"},
                main_piece={"piece": "Beyer Op.101 No.1", "minutes": 15, "target_score": 75, "focus": "音准 + 节奏"},
                review={"piece": "—", "minutes": 0},
                cooldown={"piece": "音阶 C 大调", "minutes": 5, "notes": "双手 2 个八度"},
                daily_goals=["熟悉键位", "保持手腕放松", "慢速 60 BPM"],
            ))
        return plan

    def _student_level(self) -> str:
        avg = sum(e["score"] for e in self.db.data["evaluations"]) / self.db.data["total_pieces_played"]
        return _level_from_score(avg)

    def _select_target_pieces(self, level: str, in_progress: list[str]) -> list[dict]:
        """选 3-4 首目标曲目:in_progress 优先 + 难度阶梯"""
        candidates = list(REPERTOIRE_BY_LEVEL[level])
        # 加相邻难度
        levels = list(REPERTOIRE_BY_LEVEL.keys())
        idx = levels.index(level)
        if idx + 1 < len(levels):
            candidates.extend(REPERTOIRE_BY_LEVEL[levels[idx + 1]][:1])
        if idx > 0:
            candidates.extend(REPERTOIRE_BY_LEVEL[levels[idx - 1]][:1])

        # in_progress 优先(如果还在库里)
        result = []
        for piece_dict in candidates:
            if piece_dict["piece"] in in_progress or len(result) < 2:
                result.append(piece_dict)
        # 凑够 4 首
        if len(result) < 4:
            for piece_dict in candidates:
                if piece_dict not in result:
                    result.append(piece_dict)
                if len(result) >= 4:
                    break
        return result[:4]

    def _schedule_days(
        self,
        target_pieces: list[dict],
        weak_areas: list[dict],
        in_progress: list[str],
        mastered: list[str],
    ) -> list[DayPlan]:
        """把目标曲目排到 N 天"""
        plan = []
        themes = ["新曲导入", "技术专攻", "巩固", "休息/复习", "组合", "表现力", "总复习"]
        # 3-4 首曲 + 弱项专练 + 复习 in_progress

        # 抽 in_progress 1-2 首作为复习
        review_pieces = [p for p in in_progress[:2]] if in_progress else []
        weak_text = ", ".join([w["area"] for w in weak_areas[:2]]) if weak_areas else "音准"

        for d in range(1, self.days + 1):
            theme = themes[(d - 1) % len(themes)]
            date_str = (datetime.now() + timedelta(days=d - 1)).strftime("%Y-%m-%d")

            # 主曲
            if d <= len(target_pieces):
                main = target_pieces[d - 1]
                main_dict = {
                    "piece": main["piece"],
                    "minutes": self.time_per_day - 12,
                    "target_score": 88,
                    "focus": f"{main['key_focus']} ({main['period']} 风格)",
                }
            else:
                # 用第一首继续打磨
                main = target_pieces[0] if target_pieces else {"piece": "Hanon", "period": "Classical", "key_focus": "基础"}
                main_dict = {
                    "piece": main["piece"],
                    "minutes": self.time_per_day - 12,
                    "target_score": 92,
                    "focus": f"深化 {main['key_focus']}",
                }

            # 复习(在第 3-4 天,或弱项日)
            review_dict = {"piece": "—", "minutes": 0}
            if d in [3, 5] and review_pieces:
                review_dict = {
                    "piece": review_pieces[0],
                    "minutes": 8,
                    "notes": f"重点改上次错音(弱项:{weak_text})",
                }

            # 热身(根据 day theme)
            warmup_piece = "Hanon No.1" if d != 1 else "五指音阶"
            warmup_dict = {
                "piece": warmup_piece,
                "minutes": 5,
                "focus": "手指热身 + 慢速",
            }

            # 弱项专练(每隔 2 天)
            if d % 2 == 0 and weak_areas:
                # 把弱项专练塞进 main 之前
                warmup_dict = {
                    "piece": f"弱项专练:{'/'.join([w['area'] for w in weak_areas[:2]])}",
                    "minutes": 5,
                    "focus": f"针对错音:{weak_text}",
                }

            # 放松
            cooldown_dict = {
                "piece": mastered[0] if mastered else "音阶",
                "minutes": 5,
                "notes": "放松 + 享受",
            }

            # 每日目标
            daily_goals = [
                f"{main['piece']} 达 {main_dict['target_score']} 分",
                f"错音 < 2 个",
                f"节奏波动 < 15ms",
            ]
            if d == 1:
                daily_goals.append("先通读乐谱,不求完美")
            if d == 7:
                daily_goals.append("7 天总结,准备下周计划")

            plan.append(DayPlan(
                day_num=d,
                date=date_str,
                theme=theme,
                duration_min=self.time_per_day,
                warmup=warmup_dict,
                main_piece=main_dict,
                review=review_dict,
                cooldown=cooldown_dict,
                daily_goals=daily_goals,
            ))
        return plan

    def format_plan(self, plan: list[DayPlan]) -> str:
        """格式化为可读文本"""
        lines = [
            f"# 🎹 你的 {len(plan)} 天练习计划",
            f"_生成时间:{datetime.now().strftime('%Y-%m-%d %H:%M')} | 每天 {self.time_per_day} 分钟_",
            "",
        ]
        for day in plan:
            lines.extend([
                f"## Day {day.day_num} ({day.date}) — {day.theme}",
                f"**总时长**:{day.duration_min} 分钟",
                "",
                f"### 🟢 热身 ({day.warmup.get('minutes', 0)}min)",
                f"- **{day.warmup.get('piece', '—')}**",
                f"- 重点:{day.warmup.get('focus', '—')}",
                "",
                f"### 🎯 主曲 ({day.main_piece.get('minutes', 0)}min)",
                f"- **{day.main_piece.get('piece', '—')}**",
                f"- 目标分:{day.main_piece.get('target_score', '?')}",
                f"- 重点:{day.main_piece.get('focus', '—')}",
                "",
            ])
            if day.review.get("piece", "—") != "—":
                lines.extend([
                    f"### 🔄 复习 ({day.review.get('minutes', 0)}min)",
                    f"- **{day.review.get('piece', '—')}**",
                    f"- 备注:{day.review.get('notes', '—')}",
                    "",
                ])
            lines.extend([
                f"### 🌙 收尾 ({day.cooldown.get('minutes', 0)}min)",
                f"- **{day.cooldown.get('piece', '—')}**",
                f"- 备注:{day.cooldown.get('notes', '—')}",
                "",
                f"### ✅ 今日目标",
            ])
            for g in day.daily_goals:
                lines.append(f"- {g}")
            lines.append("")
        return "\n".join(lines)


# ----- 集成 voice_dialog -----
def patch_voice_dialog_with_curriculum(planner: CurriculumPlanner):
    """注入课程规划到 voice_dialog"""
    import voice_dialog
    from teaching_engine import patch_voice_dialog

    # 加重试"7 天计划"的直答
    original_call = voice_dialog.call_llm

    def with_curriculum(messages, backend="mock", **kwargs):
        if backend == "mock":
            # 拦截"7 天计划"类问题
            last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
            if last_user:
                txt = last_user["content"]
                if any(k in txt for k in ["7 天", "一周计划", "练什么", "课程", "plan"]):
                    plan = planner.generate_plan()
                    return planner.format_plan(plan)
        return original_call(messages, backend=backend, **kwargs)

    voice_dialog.call_llm = with_curriculum
    return planner


# ----- CLI -----
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--name", default="yuefeng")
    args = parser.parse_args()

    try:
        from student_db import StudentDB
        db = StudentDB(args.name)
    except Exception as e:
        print(f"⚠️  DB 加载失败: {e},用默认计划", file=sys.stderr)
        db = None

    planner = CurriculumPlanner(db=db, time_per_day_min=args.minutes, days=args.days)
    plan = planner.generate_plan()
    print(planner.format_plan(plan))


if __name__ == "__main__":
    main()
