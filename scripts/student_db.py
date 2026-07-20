"""
student_db.py — 学生长期记忆(CoPiano v2.0 的 5.7)

让 AI 老师"记住"学生跨多次弹琴的进度。

数据结构(JSON,本地存储 ~/.copiano/student_<name>.db.json):
{
    "name": "yuefeng",
    "created_at": "2026-07-20",
    "updated_at": "2026-07-20",
    "total_sessions": 12,
    "total_pieces_played": 35,
    "evaluations": [
        {
            "date": "2026-07-15",
            "piece": "Minuet in G",
            "period": "Baroque",
            "score": 78.0,
            "pitch_accuracy": 0.80,
            "n_pitch_errors": 3,
            "errors": ["E4→D4", "G4→F#4"],
            "notes": "今天状态一般"
        },
        ...
    ],
    "mastered": ["Twinkle", "Beyer Op.101 No.1"],
    "in_progress": ["Bach Prelude in C", "Sonata K.545"],
    "milestones": [
        {"date": "2026-07-10", "event": "首次破 80 分", "piece": "Minuet in G"},
    ],
    "weak_areas": [
        {"area": "左手指法", "frequency": 0.3, "last_seen": "2026-07-15"},
    ],
    "practice_streak": 7,  # 连续练习天数
    "weekly_goal": {"pieces": 5, "target_score": 85},
    "weekly_progress": {"pieces_done": 3, "scores": [82, 88, 79]}
}

API:
    db = StudentDB(name="yuefeng")
    db.record_eval(eval_result, piece="Bach Prelude", period="Baroque", notes="...")
    db.mark_mastered("Minuet in G")
    db.add_milestone("首次破 90 分", piece="Bach Prelude")
    db.set_weekly_goal(pieces=5, target_score=85)
    summary = db.get_progress_summary()
    weak = db.get_weak_areas(top_n=3)
    db.save()

用法:
    from student_db import StudentDB
    db = StudentDB()  # 默认 ~/.copiano/student_default.json
    db.record_eval(...)
    db.save()
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

DEFAULT_DB_DIR = Path.home() / ".copiano"


class StudentDB:
    """学生进度数据库(JSON 持久化)"""

    def __init__(self, name: str = "default", db_dir: Optional[Path] = None):
        self.name = name
        self.db_dir = Path(db_dir) if db_dir else DEFAULT_DB_DIR
        self.db_path = self.db_dir / f"student_{name}.db.json"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.data = self._load_or_init()

    def _load_or_init(self) -> dict:
        if self.db_path.exists():
            try:
                return json.loads(self.db_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[db] 加载失败 ({e}),新建空 DB", file=sys.stderr)
        return self._empty_db()

    def _empty_db(self) -> dict:
        return {
            "name": self.name,
            "created_at": datetime.now().isoformat()[:10],
            "updated_at": datetime.now().isoformat()[:10],
            "total_sessions": 0,
            "total_pieces_played": 0,
            "evaluations": [],
            "mastered": [],
            "in_progress": [],
            "milestones": [],
            "weak_areas": [],
            "practice_streak": 0,
            "last_practice_date": None,
            "weekly_goal": {"pieces": 0, "target_score": 0},
            "weekly_progress": {"pieces_done": 0, "scores": []},
        }

    # ----- 写入 -----
    def record_eval(
        self,
        eval_result: dict,
        piece: str = "",
        period: str = "",
        notes: str = "",
    ) -> dict:
        """记录一次评估,返回新 entry"""
        entry = {
            "date": datetime.now().isoformat()[:10],
            "timestamp": datetime.now().isoformat(),
            "piece": piece or eval_result.get("piece", "Unknown"),
            "period": period or eval_result.get("period", eval_result.get("period_hint", "")),
            "score": eval_result.get("score", 0),
            "pitch_accuracy": eval_result.get("pitch_accuracy", 0),
            "timing_std_ms": eval_result.get("timing_std_ms", 0),
            "timing_mean_ms": eval_result.get("timing_mean_ms", 0),
            "velocity_correlation": eval_result.get("velocity_correlation", 0),
            "n_pitch_errors": eval_result.get("n_pitch_errors", 0),
            "errors": [
                f"{s.get('ref_note', s.get('ref_pitch', '?'))}→{s.get('user_note', s.get('user_pitch', '?'))}"
                for s in eval_result.get("pitch_error_samples", [])
            ],
            "notes": notes,
        }
        self.data["evaluations"].append(entry)
        self.data["total_pieces_played"] = len(self.data["evaluations"])
        self.data["updated_at"] = entry["date"]

        # 更新练习 streak
        self._update_streak(entry["date"])

        # 更新周进度
        self._update_weekly(entry["score"])

        # 更新 in_progress
        if entry["piece"] not in self.data["in_progress"] and entry["piece"] not in self.data["mastered"]:
            self.data["in_progress"].append(entry["piece"])

        # 自动检查里程碑
        self._check_milestones(entry)

        return entry

    def mark_mastered(self, piece: str):
        """标记掌握"""
        if piece not in self.data["mastered"]:
            self.data["mastered"].append(piece)
        if piece in self.data["in_progress"]:
            self.data["in_progress"].remove(piece)
        self.add_milestone(f"掌握 {piece}", piece=piece)

    def add_milestone(self, event: str, piece: str = "", score: float = 0):
        """加里程碑"""
        ms = {
            "date": datetime.now().isoformat()[:10],
            "event": event,
            "piece": piece,
            "score": score,
        }
        self.data["milestones"].append(ms)

    def set_weekly_goal(self, pieces: int = 5, target_score: float = 85.0):
        """设周目标"""
        self.data["weekly_goal"] = {"pieces": pieces, "target_score": target_score}

    # ----- 内部更新 -----
    def _update_streak(self, today: str):
        """更新连续练习天数"""
        last = self.data.get("last_practice_date")
        if last == today:
            return  # 同一天重复
        if last is None:
            self.data["practice_streak"] = 1
        else:
            try:
                last_date = datetime.fromisoformat(last)
                today_date = datetime.fromisoformat(today)
                diff_days = (today_date - last_date).days
                if diff_days == 1:
                    self.data["practice_streak"] += 1
                elif diff_days > 1:
                    self.data["practice_streak"] = 1
            except Exception:
                self.data["practice_streak"] = 1
        self.data["last_practice_date"] = today

    def _update_weekly(self, score: float):
        """更新周进度(简化版:最近 7 条)"""
        wp = self.data["weekly_progress"]
        wp["scores"].append(score)
        if len(wp["scores"]) > 7:
            wp["scores"] = wp["scores"][-7:]
        wp["pieces_done"] = len(wp["scores"])

    def _check_milestones(self, entry: dict):
        """自动检测里程碑"""
        score = entry["score"]
        piece = entry["piece"]

        # 首次破 80/85/90/95
        for threshold in [80, 85, 90, 95]:
            event = f"首次破 {threshold} 分"
            already = any(m["event"] == event for m in self.data["milestones"])
            if not already and score >= threshold:
                self.add_milestone(event, piece=piece, score=score)

    # ----- 查询 -----
    def get_progress_summary(self) -> str:
        """给 LLM / 展示用的进度摘要"""
        d = self.data
        if not d["evaluations"]:
            return "还没记录任何评估。"

        n = d["total_pieces_played"]
        avg = sum(e["score"] for e in d["evaluations"]) / n
        recent = d["evaluations"][-5:]
        recent_avg = sum(e["score"] for e in recent) / len(recent)

        # 趋势(最近 5 vs 之前 5)
        if len(d["evaluations"]) >= 10:
            last5 = [e["score"] for e in d["evaluations"][-5:]]
            prev5 = [e["score"] for e in d["evaluations"][-10:-5]]
            trend_diff = sum(last5) / 5 - sum(prev5) / 5
            trend = "improving" if trend_diff > 5 else "declining" if trend_diff < -5 else "stable"
        else:
            trend = "insufficient_data"

        lines = [
            f"学生 {d['name']} 的进度:",
            f"- 共弹 {n} 首,平均 {avg:.1f} 分",
            f"- 最近 5 首平均 {recent_avg:.1f} 分,趋势: {trend}",
            f"- 掌握 {len(d['mastered'])} 首,进行中 {len(d['in_progress'])} 首",
            f"- 连续练习 {d['practice_streak']} 天",
        ]
        if d["milestones"]:
            last_ms = d["milestones"][-1]
            lines.append(f"- 最近里程碑:{last_ms['date']} {last_ms['event']}({last_ms.get('piece', '')})")
        if d["weekly_goal"]["pieces"]:
            goal = d["weekly_goal"]
            wp = d["weekly_progress"]
            lines.append(f"- 本周目标:{goal['pieces']} 首 / {goal['target_score']} 分,目前 {wp['pieces_done']} 首 / {sum(wp['scores'])/max(1,len(wp['scores'])):.1f} 分")
        return "\n".join(lines)

    def get_weak_areas(self, top_n: int = 3) -> list[dict]:
        """分析历史,提取弱项(基于错音模式 + 低分项)"""
        if not self.data["evaluations"]:
            return []

        # 收集所有错音 note
        error_notes = Counter()
        low_score_pieces = []
        for e in self.data["evaluations"]:
            for err in e.get("errors", []):
                # 提取 ref_note(错音前)
                m = re.match(r"(\d+)→", err)
                if m:
                    error_notes[m.group(1)] += 1
            if e["score"] < 80:
                low_score_pieces.append((e["piece"], e["score"]))

        weak = []
        # 错音最频繁的音
        for note, cnt in error_notes.most_common(top_n):
            if cnt >= 2:
                weak.append({"area": f"音 {note}", "type": "pitch", "frequency": cnt})
        # 低分曲
        for piece, score in low_score_pieces[-top_n:]:
            weak.append({"area": piece, "type": "piece", "score": score})
        return weak[:top_n]

    def get_mastered_pieces(self) -> list[str]:
        return list(self.data["mastered"])

    def get_in_progress_pieces(self) -> list[str]:
        return list(self.data["in_progress"])

    def get_recent_evaluations(self, n: int = 5) -> list[dict]:
        return self.data["evaluations"][-n:]

    def get_practice_streak(self) -> int:
        return self.data["practice_streak"]

    # ----- 持久化 -----
    def save(self):
        self.data["updated_at"] = datetime.now().isoformat()[:10]
        self.db_path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def __repr__(self):
        return f"<StudentDB name={self.name} pieces={self.data['total_pieces_played']} streak={self.data['practice_streak']}>"


# ----- 集成 voice_dialog -----
def patch_voice_dialog_with_db(db: StudentDB, planner=None):
    """注入学生 DB + 教学引擎 + 可选课程规划到 voice_dialog

    正确 patch 顺序(从内到外):
    1. GPU LLM (innermost, fallback)
    2. Teaching engine (直答拦截)
    3. DB 摘要注入 (context)
    4. Curriculum (outermost, 拦截 "7 天计划" 等)

    Args:
        db: StudentDB 实例
        planner: 可选 CurriculumPlanner
    """
    import voice_dialog
    from teaching_engine import TeachingEngine, patch_voice_dialog
    from llm_gpu_client import patch_voice_dialog_with_gpu
    from curriculum import patch_voice_dialog_with_curriculum

    # 1. 教学引擎:从 DB 重建 history
    engine = TeachingEngine()
    if db.data["evaluations"]:
        engine.set_history([
            {
                "piece": e["piece"],
                "period": e["period"],
                "score": e["score"],
                "pitch_accuracy": e["pitch_accuracy"],
                "timing_std_ms": e["timing_std_ms"],
                "timing_mean_ms": e["timing_mean_ms"],
                "velocity_correlation": e["velocity_correlation"],
                "n_pitch_errors": e["n_pitch_errors"],
            }
            for e in db.data["evaluations"]
        ])
        last = db.data["evaluations"][-1]
        engine.set_latest_eval(last, piece_name=last["piece"], period=last["period"])

    # 2. 注入 GPU LLM(最内层)
    patch_voice_dialog_with_gpu()

    # 3. 注入教学引擎直答
    patch_voice_dialog(engine)

    # 4. 注入 DB 摘要到 system prompt
    original_build = voice_dialog.DialogState.build_messages

    def patched_build(self, max_turns=6):
        msgs = original_build(self, max_turns)
        if msgs and msgs[0]["role"] == "system":
            summary = db.get_progress_summary()
            weak = db.get_weak_areas(top_n=3)
            extra = f"\n\n## 学生长期记忆(跨会话)\n{summary}"
            if weak:
                extra += f"\n## 当前弱项\n" + "\n".join([f"- {w['area']}({w['type']})" for w in weak])
            msgs[0]["content"] = msgs[0]["content"] + extra
        return msgs

    voice_dialog.DialogState.build_messages = patched_build

    # 5. 注入课程规划(最外层)
    if planner is None:
        from curriculum import CurriculumPlanner
        planner = CurriculumPlanner(db, time_per_day_min=30, days=7)
    patch_voice_dialog_with_curriculum(planner)

    return engine, planner


# ----- CLI -----
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="default", help="学生名")
    parser.add_argument("--summary", action="store_true", help="显示进度摘要")
    parser.add_argument("--weak", action="store_true", help="显示弱项")
    parser.add_argument("--reset", action="store_true", help="重置 DB")
    args = parser.parse_args()

    if args.reset:
        path = DEFAULT_DB_DIR / f"student_{args.name}.db.json"
        if path.exists():
            path.unlink()
        print(f"✅ 重置 {path}")
        return

    db = StudentDB(name=args.name)
    if args.summary:
        print(db.get_progress_summary())
    elif args.weak:
        weak = db.get_weak_areas()
        print(json.dumps(weak, ensure_ascii=False, indent=2))
    else:
        print(repr(db))
        print(f"DB path: {db.db_path}")


if __name__ == "__main__":
    main()
