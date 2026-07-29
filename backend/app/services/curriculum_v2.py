"""
curriculum_v2.py — CoPiano 7 天多模态自适应课程

Cycle 7 Stage 2 实现:
- 6 类练习块 (warmup_pitch / warmup_hand / expressiveness / sight_reading / main_piece / review / weakness / cooldown)
- 5 维模块整合 (音高 + 表现力 + 手型 + 银发 + 视奏)
- Spaced Repetition (类 SM-2 简化算法: 1/3/7/14/30 天间隔)
- WeaknessDetector (从 5 维分数检测 top 3 弱项)
- AdaptivePlanner (7 天计划 + 每日目标 + 难度自适应)
- voice_dialog 集成 ("我的课程" / "今天练什么" / "标记完成")

调研依据: notes/market_knowledge_cycle7.md
对位: SAMICK / Simply Piano / Flowkey / Anki SM-2
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

# === 6 类练习块定义 ===

BLOCK_TYPES = {
    'warmup_pitch': {
        'name': '音准热身',
        'name_en': 'Pitch Warmup',
        'default_minutes': (3, 5),
        'module': 'eval_pitch',
        'description': '音阶/琶音/C 大调 5-finger 模式,激活手指 + 耳朵',
        'icon': '🎵',
    },
    'warmup_hand': {
        'name': '手型热身',
        'name_en': 'Hand Pose Warmup',
        'default_minutes': (2, 3),
        'module': 'hand_pose_analyzer',
        'description': '放松手腕 + 慢速触键,纠正手型',
        'icon': '✋',
    },
    'expressiveness': {
        'name': '表现力专练',
        'name_en': 'Expressiveness Drill',
        'default_minutes': (5, 8),
        'module': 'expressiveness_analyzer',
        'description': '针对 9 维表现力 (timing/dynamics/articulation/pedal) 单项专练',
        'icon': '🎨',
    },
    'sight_reading': {
        'name': '视奏训练',
        'name_en': 'Sight Reading',
        'default_minutes': (5, 10),
        'module': 'sight_reading_trainer',
        'description': '电脑键 1-7 / MIDI / 虚拟键盘,4 难度渐进',
        'icon': '👀',
    },
    'main_piece': {
        'name': '主曲打磨',
        'name_en': 'Main Piece',
        'default_minutes': (15, 20),
        'module': 'midi_analyzer',
        'description': '目标曲目深度打磨,5 维评分',
        'icon': '🎹',
    },
    'review_piece': {
        'name': '间隔复习',
        'name_en': 'Spaced Review',
        'default_minutes': (5, 10),
        'module': 'midi_analyzer',
        'description': 'SM-2 间隔复习,巩固已学曲子',
        'icon': '🔁',
    },
    'weakness_drill': {
        'name': '弱项专练',
        'name_en': 'Weakness Drill',
        'default_minutes': (3, 5),
        'module': 'multi',
        'description': '针对 top 3 弱项领域专练',
        'icon': '🎯',
    },
    'cooldown_relax': {
        'name': '放松',
        'name_en': 'Cooldown',
        'default_minutes': (2, 3),
        'module': 'free_play',
        'description': '自由弹奏,享受音乐',
        'icon': '🌙',
    },
}


# === 5 维评分定义 (从 v3.0 模块整合) ===

DIMENSION_NAMES = ['pitch', 'expressiveness', 'hand_pose', 'rhythm', 'sight_reading']
# pitch: 音准/错音 (eval_pitch)
# expressiveness: 9 维表现力 (C3)
# hand_pose: 9 维手型 (C4)
# rhythm: 节奏稳定性
# sight_reading: 视奏准确率 (C6)


# === 数据类 ===

@dataclass
class BlockSpec:
    """单一练习块"""
    block_type: str  # BLOCK_TYPES key
    minutes: int
    target: str = ''  # 块目标, e.g. "Bach Prelude m.4-8 错音 < 1"
    piece: str = ''   # 关联曲目 (可选)
    module: str = ''  # 关联模块 (从 BLOCK_TYPES 自动取)
    notes: str = ''   # 备注
    score: float = 0.0  # 完成度评分 0-100 (可选)

    def __post_init__(self):
        if not self.module and self.block_type in BLOCK_TYPES:
            self.module = BLOCK_TYPES[self.block_type]['module']

    @property
    def name(self) -> str:
        return BLOCK_TYPES.get(self.block_type, {}).get('name', self.block_type)

    def to_dict(self):
        return asdict(self)


@dataclass
class DayPlanV2:
    """一天的计划 (v2 扩展)"""
    day_num: int  # 1-7
    date: str
    theme: str
    duration_min: int
    blocks: list[BlockSpec] = field(default_factory=list)
    daily_goals: list[str] = field(default_factory=list)
    difficulty: str = 'beginner'  # 当日整体难度
    senior_mode: bool = False  # 是否启用银发模式
    notes: str = ''  # 备注

    def to_dict(self):
        return {
            **asdict(self),
            'blocks': [b.to_dict() for b in self.blocks],
        }

    def total_minutes(self) -> int:
        return sum(b.minutes for b in self.blocks)

    def block_summary(self) -> str:
        """返回 1 行摘要"""
        icons = ''.join(BLOCK_TYPES.get(b.block_type, {}).get('icon', '•') for b in self.blocks)
        return f"Day {self.day_num} ({self.theme}): {self.total_minutes()}min [{icons}]"


@dataclass
class WeekPlanV2:
    """7 天计划"""
    start_date: str
    days: list[DayPlanV2] = field(default_factory=list)
    weekly_goals: list[str] = field(default_factory=list)
    weakness_focus: list[str] = field(default_factory=list)  # 本周专攻弱项
    avg_score: float = 0.0  # 学生当前平均分
    difficulty_progression: list[str] = field(default_factory=list)  # 7 天难度档

    def to_dict(self):
        return {
            **asdict(self),
            'days': [d.to_dict() for d in self.days],
        }


# === 间隔重复 (类 SM-2 简化) ===

SPACED_INTERVALS = [1, 3, 7, 14, 30, 60]  # 天


class SpacedRepetition:
    """简化 SM-2 算法 — 钢琴曲子专用

    核心:
    - 每次评估 (0-100) → 调整 ease factor
    - ease < 0.6 → 重置间隔到 1 天
    - ease >= 0.6 → 按 SPACED_INTERVALS 推进
    - 答得好 (≥85) → interval *= ease
    """

    def __init__(self):
        # piece_name → {'last_review': date_str, 'ease': 1.5, 'interval_idx': 0, 'last_score': 0}
        self.pieces: dict[str, dict] = {}

    def get_next_review(self, piece_name: str) -> dict | None:
        """获取下次复习时间 (None = 还没学过)"""
        if piece_name not in self.pieces:
            return None
        state = self.pieces[piece_name]
        interval = SPACED_INTERVALS[state['interval_idx']]
        last = datetime.strptime(state['last_review'], "%Y-%m-%d")
        next_date = (last + timedelta(days=interval)).strftime("%Y-%m-%d")
        return {
            'piece': piece_name,
            'next_review': next_date,
            'days_until': (datetime.strptime(next_date, "%Y-%m-%d") - datetime.now()).days,
            'ease': round(state['ease'], 2),
            'interval_idx': state['interval_idx'],
            'last_score': state.get('last_score', 0),
        }

    def record_review(self, piece_name: str, score: float, date_str: str = None):
        """记录一次复习结果 (0-100)"""
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        if piece_name not in self.pieces:
            self.pieces[piece_name] = {
                'last_review': date_str,
                'ease': 1.5,
                'interval_idx': 0,
                'last_score': score,
            }
            return

        state = self.pieces[piece_name]
        # 答得好 (>= 85) → 推 interval_idx
        if score >= 85:
            state['interval_idx'] = min(state['interval_idx'] + 1, len(SPACED_INTERVALS) - 1)
            # ease 提升 (上限 2.5)
            state['ease'] = min(state['ease'] + 0.1, 2.5)
        # 答得差 (< 60) → 重置 interval,ease 下降
        elif score < 60:
            state['interval_idx'] = 0
            state['ease'] = max(state['ease'] - 0.2, 1.3)
        # 60-85 → 保持 interval,ease 略降
        else:
            state['ease'] = max(state['ease'] - 0.05, 1.3)

        state['last_review'] = date_str
        state['last_score'] = score

    def get_due_pieces(self, max_count: int = 3) -> list[dict]:
        """获取今日需要复习的曲子 (按 days_until 升序)"""
        all_due = []
        for piece in self.pieces:
            nr = self.get_next_review(piece)
            if nr and nr['days_until'] <= 0:
                all_due.append(nr)
        all_due.sort(key=lambda x: x['days_until'])
        return all_due[:max_count]

    def to_dict(self):
        return {
            'pieces': self.pieces,
            'intervals': SPACED_INTERVALS,
        }


# === 弱项检测 ===

class WeaknessDetector:
    """从 5 维分数检测 top 弱项"""

    def __init__(self, dim_scores: dict[str, float] = None):
        # 默认 5 维分数 0-100
        self.dim_scores = dim_scores or {
            'pitch': 75.0,
            'expressiveness': 70.0,
            'hand_pose': 80.0,
            'rhythm': 85.0,
            'sight_reading': 60.0,
        }

    def detect(self, top_n: int = 3) -> list[dict]:
        """返回 top_n 弱项 (分数最低优先)"""
        sorted_dims = sorted(self.dim_scores.items(), key=lambda x: x[1])
        weak = []
        for i, (dim, score) in enumerate(sorted_dims[:top_n]):
            severity = 'high' if score < 60 else ('medium' if score < 75 else 'low')
            weak.append({
                'rank': i + 1,
                'dimension': dim,
                'score': score,
                'severity': severity,
                'block_type': self._weakness_to_block(dim),
                'focus': self._weakness_to_focus(dim),
            })
        return weak

    @staticmethod
    def _weakness_to_block(dim: str) -> str:
        """弱项 → 推荐练习块类型"""
        mapping = {
            'pitch': 'warmup_pitch',
            'expressiveness': 'expressiveness',
            'hand_pose': 'warmup_hand',
            'rhythm': 'main_piece',
            'sight_reading': 'sight_reading',
        }
        return mapping.get(dim, 'weakness_drill')

    @staticmethod
    def _weakness_to_focus(dim: str) -> str:
        """弱项 → 教学重点"""
        return {
            'pitch': '音准/错音:慢速单手 + 分手练',
            'expressiveness': '表现力:timing + dynamics 对比',
            'hand_pose': '手型:手腕放松 + 5-finger 慢抬',
            'rhythm': '节奏:节拍器 + 16th notes 等分',
            'sight_reading': '视奏:Landmark 法 + 3 教学法',
        }.get(dim, '综合练习')

    @staticmethod
    def from_student_db(db) -> 'WeaknessDetector':
        """从 student_db 构造 (尝试读取 5 维数据,失败用默认)"""
        try:
            evals = db.data.get('evaluations', [])
            if not evals:
                return WeaknessDetector()
            # 取最近 5 次平均
            recent = evals[-5:] if len(evals) >= 5 else evals
            # 这里简化:用 pitch_accuracy 推算 5 维 (实际 v3 数据如果有更好)
            avg_pitch = sum(e.get('pitch_accuracy', 0.75) * 100 for e in recent) / len(recent)
            dim_scores = {
                'pitch': avg_pitch,
                'expressiveness': avg_pitch - 5,  # 表现力通常比音准低
                'hand_pose': 75.0,  # 默认
                'rhythm': min(avg_pitch + 5, 95),
                'sight_reading': 65.0,  # 默认
            }
            return WeaknessDetector(dim_scores)
        except Exception:
            return WeaknessDetector()


# === 难度档位 ===

DIFFICULTY_PROGRESSION = ['beginner', 'beginner', 'elementary', 'elementary',
                          'intermediate', 'intermediate', 'advanced']


def get_difficulty_for_day(day_num: int, avg_score: float = 0) -> str:
    """根据 day_num 和平均分返回难度档

    avg_score 0 = 用默认 progression
    avg_score > 0 = 升档
    """
    if avg_score <= 0:
        return DIFFICULTY_PROGRESSION[max(0, min(6, day_num - 1))]
    # 升档:avg >= 90 → +2 提前, >= 80 → +1 提前, < 80 → 不变
    if avg_score >= 90:
        idx = min(day_num - 1 + 2, 6)  # +2 天提前
    elif avg_score >= 80:
        idx = min(day_num - 1 + 1, 6)  # +1 天提前
    else:
        idx = max(0, day_num - 1 - 1)  # 滞后
    return DIFFICULTY_PROGRESSION[idx]


# === 自适应规划器 ===

class AdaptivePlanner:
    """7 天自适应规划器 (v2 整合 5 维 + 间隔复习 + 银发)"""

    def __init__(self, db=None, age: int | None = None, time_per_day_min: int = 30, days: int = 7):
        self.db = db
        self.age = age
        self.time_per_day = time_per_day_min
        self.days = days
        # 初始化模块 (Optional,失败不影响 plan 生成)
        self.weakness_detector = WeaknessDetector.from_student_db(db) if db else WeaknessDetector()
        self.spaced_rep = SpacedRepetition()
        # 银发自动检测
        self.senior_mode_active = (age is not None and age >= 60)
        # 学生整体水平
        self.avg_score = self._compute_avg_score() if db else 0

    def _compute_avg_score(self) -> float:
        """从 student_db 算平均分"""
        try:
            evals = self.db.data.get('evaluations', [])
            if not evals:
                return 0
            return sum(e.get('score', 75) for e in evals) / len(evals)
        except Exception:
            return 0

    def generate_week_plan(self) -> WeekPlanV2:
        """生成 7 天计划"""
        weakness = self.weakness_detector.detect(top_n=3)
        weekly_goals = self._build_weekly_goals(weakness)
        difficulty_progression = [
            get_difficulty_for_day(d, self.avg_score) for d in range(1, self.days + 1)
        ]

        days = []
        for d in range(1, self.days + 1):
            day_plan = self._build_day(d, weakness, difficulty_progression[d - 1])
            days.append(day_plan)

        return WeekPlanV2(
            start_date=datetime.now().strftime("%Y-%m-%d"),
            days=days,
            weekly_goals=weekly_goals,
            weakness_focus=[w['focus'] for w in weakness],
            avg_score=self.avg_score,
            difficulty_progression=difficulty_progression,
        )

    def _build_weekly_goals(self, weakness: list[dict]) -> list[str]:
        """构建本周 3 个目标"""
        goals = []
        for w in weakness[:2]:
            goals.append(f"{w['dimension']} 提分: {w['score']:.0f} → {min(w['score'] + 10, 95):.0f}")
        # 第 3 个目标:总时长
        goals.append(f"总练习 {self.days} 天 × {self.time_per_day}min = {self.days * self.time_per_day}min")
        return goals

    def _build_day(self, day_num: int, weakness: list[dict], difficulty: str) -> DayPlanV2:
        """构建 1 天计划 (6-8 块)"""
        # 银发模式:每天多 5min,块更少
        time_budget = self.time_per_day + 5 if self.senior_mode_active else self.time_per_day

        # 7 天渐进主题
        themes = ['新起点 + 音准', '表现力探索', '视奏起步', '主曲打磨', '弱项专攻',
                  '组合 + 表现力', '总复习 + 展望']
        theme = themes[min(day_num - 1, 6)]

        # 块数:6 块 (warmup × 2 + 表现力/视奏 + 主曲 + 复习 + 弱项 + cooldown)
        blocks = []

        # 1. 音准热身 (3-5min)
        blocks.append(BlockSpec(
            block_type='warmup_pitch',
            minutes=5 if not self.senior_mode_active else 4,
            target='C/G/D 大调音阶 + 5-finger 模式',
            piece='',
        ))

        # 2. 手型热身 (2-3min)
        blocks.append(BlockSpec(
            block_type='warmup_hand',
            minutes=3,
            target='手腕放松 + 慢速触键,手型 ≥ 80 分',
            piece='',
        ))

        # 3. 表现力或视奏 (5-8min) — 隔天切换
        if day_num % 2 == 0:
            blocks.append(BlockSpec(
                block_type='expressiveness',
                minutes=6,
                target='主曲表现力 ≥ 75/100',
                piece=self._get_target_piece(day_num),
            ))
        else:
            blocks.append(BlockSpec(
                block_type='sight_reading',
                minutes=7,
                target=f'视奏 {difficulty} 难度, accuracy ≥ {70 if day_num <= 3 else 80}%',
                piece='',
            ))

        # 4. 主曲打磨 (15-20min)
        blocks.append(BlockSpec(
            block_type='main_piece',
            minutes=time_budget - 20,
            target=f'主曲: {self._get_target_piece(day_num)} → 目标 90 分',
            piece=self._get_target_piece(day_num),
        ))

        # 5. 间隔复习 (5-8min) — 第 3/5/7 天
        if day_num in (3, 5, 7):
            review_pieces = self.spaced_rep.get_due_pieces(max_count=2)
            if review_pieces:
                rp = review_pieces[0]
                blocks.append(BlockSpec(
                    block_type='review_piece',
                    minutes=8,
                    target=f'复习 {rp["piece"]} (上次 {rp["last_score"]:.0f} 分, 间隔 {rp["ease"]})',
                    piece=rp['piece'],
                ))

        # 6. 弱项专练 (3-5min) — 每 2 天
        if day_num % 2 == 1 and weakness:
            w = weakness[0]
            blocks.append(BlockSpec(
                block_type='weakness_drill',
                minutes=5,
                target=w['focus'],
                piece=self._get_target_piece(day_num),
                notes=f'针对弱项 #{w["rank"]} ({w["severity"]})',
            ))

        # 7. 放松 (2-3min)
        blocks.append(BlockSpec(
            block_type='cooldown_relax',
            minutes=3,
            target='自由弹奏 1 段熟悉曲子',
            piece=self._get_mastered_piece(),
        ))

        # 每日目标
        daily_goals = self._build_daily_goals(day_num, weakness, blocks)

        return DayPlanV2(
            day_num=day_num,
            date=(datetime.now() + timedelta(days=day_num - 1)).strftime("%Y-%m-%d"),
            theme=theme,
            duration_min=time_budget,
            blocks=blocks,
            daily_goals=daily_goals,
            difficulty=difficulty,
            senior_mode=self.senior_mode_active,
            notes=self._build_day_notes(day_num),
        )

    def _build_daily_goals(self, day_num: int, weakness: list[dict], blocks: list[BlockSpec]) -> list[str]:
        """构建每日 3-5 个目标"""
        goals = []
        # 主曲目标
        for b in blocks:
            if b.block_type == 'main_piece' and b.piece:
                goals.append(f"{b.piece} ≥ 90 分")
                break
        # 错音
        goals.append('错音 < 2 个')
        # 弱项
        if weakness:
            goals.append(f"重点: {weakness[0]['dimension']} ≥ {weakness[0]['score'] + 5:.0f}")
        # 节奏
        goals.append('节奏波动 < 15ms')
        # 银发:加鼓励
        if self.senior_mode_active:
            goals.append('保持好心情,慢慢来')
        return goals

    def _build_day_notes(self, day_num: int) -> str:
        notes = []
        if day_num == 1:
            notes.append('先通读乐谱,不求完美')
        if day_num == 7:
            notes.append('7 天总结,准备下周计划')
        if self.senior_mode_active:
            notes.append('银发模式已激活')
        return ' / '.join(notes)

    def _get_target_piece(self, day_num: int) -> str:
        """根据 day_num 选目标曲目 (简化:轮转 4 首)"""
        pieces = ['Bach Prelude in C', 'Minuet in G', 'Sonata K.545', 'Für Elise']
        return pieces[(day_num - 1) % len(pieces)]

    def _get_mastered_piece(self) -> str:
        """从 student_db 取已掌握曲目"""
        try:
            if self.db and hasattr(self.db, 'data'):
                mastered = self.db.data.get('mastered', [])
                if mastered:
                    return mastered[0]
        except Exception:
            pass
        return 'Twinkle Twinkle'

    def format_plan(self, plan: WeekPlanV2) -> str:
        """格式化为可读文本"""
        lines = [
            f"# 🎹 你的 {len(plan.days)} 天 AI 自适应课程 (v3.0 多模态)",
            f"_生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
            f"_当前水平: {plan.avg_score:.0f} 分_"
            + (" | 👴 银发模式" if self.senior_mode_active else ""),
            "",
            "## 📊 本周目标",
        ]
        for g in plan.weekly_goals:
            lines.append(f"- {g}")
        if plan.weakness_focus:
            lines.append("\n## 🎯 弱项专攻")
            for w in plan.weakness_focus:
                lines.append(f"- {w}")
        lines.append("\n## 📅 每日计划")
        for day in plan.days:
            lines.append(f"\n### Day {day.day_num} ({day.date}) — {day.theme}")
            lines.append(f"**难度: {day.difficulty} | 总时长: {day.total_minutes()}min**")
            for b in day.blocks:
                icon = BLOCK_TYPES.get(b.block_type, {}).get('icon', '•')
                lines.append(f"  {icon} **{b.name}** ({b.minutes}min) — {b.target}")
            if day.daily_goals:
                lines.append("  **目标**:")
                for g in day.daily_goals:
                    lines.append(f"    - {g}")
        return '\n'.join(lines)


# === voice_dialog 集成 ===

def patch_voice_dialog_with_curriculum(dialog_module=None, planner: AdaptivePlanner = None):
    """注入 voice_dialog,识别课程相关意图

    关键词:
    - "我的课程" / "今天练什么" / "查看计划" → 读出当天计划
    - "标记完成" / "练完了" / "完成" → 标记 + 下一天
    - "跳过" / "换一首" → 调整
    """
    state = {
        'planner': planner,
        'week_plan': planner.generate_week_plan() if planner else None,
        'current_day_idx': 0,
    }

    def handle_curriculum_request(text: str) -> str | None:
        text_lower = text.lower()
        on_kw = ['我的课程', '今天练什么', '查看计划', '课程', '练什么', '看课程']
        done_kw = ['标记完成', '练完了', '完成', 'done', 'finish']
        skip_kw = ['跳过', '换一首', 'skip']

        # 读出当天计划
        if any(kw in text_lower for kw in on_kw):
            if state['week_plan'] is None:
                return "还没有课程计划。请先生成一个 7 天计划。"
            day = state['week_plan'].days[state['current_day_idx']]
            lines = [f"Day {day.day_num} {day.theme},共 {day.total_minutes()} 分钟。"]
            for b in day.blocks[:4]:  # 只读前 4 块,避免太长
                icon = BLOCK_TYPES.get(b.block_type, {}).get('icon', '•')
                lines.append(f"{icon}{b.name} {b.minutes} 分钟")
            if len(day.blocks) > 4:
                lines.append(f"还有 {len(day.blocks) - 4} 块,共 {day.total_minutes()} 分钟")
            return '。'.join(lines)

        # 标记完成
        if any(kw in text_lower for kw in done_kw) and state['week_plan']:
            if state['current_day_idx'] < len(state['week_plan'].days) - 1:
                state['current_day_idx'] += 1
                next_day = state['week_plan'].days[state['current_day_idx']]
                return f"好的,Day {state['current_day_idx']} 标记完成。明天是 Day {next_day.day_num} {next_day.theme}。"
            else:
                return "已经是第 7 天了,7 天计划全部完成!恭喜!"

        # 跳过
        if any(kw in text_lower for kw in skip_kw) and state['week_plan']:
            if state['current_day_idx'] < len(state['week_plan'].days) - 1:
                state['current_day_idx'] += 1
                return f"好的,跳到 Day {state['current_day_idx'] + 1}。"

        return None

    if dialog_module is None:
        return handle_curriculum_request, state

    # 捕获原始 (避免递归)
    _orig_call_llm = dialog_module.call_llm if hasattr(dialog_module, 'call_llm') else None

    if hasattr(dialog_module, 'process_query'):
        def patched_process_query(text, *args, **kwargs):
            handled = handle_curriculum_request(text)
            if handled:
                return handled
            return dialog_module.call_llm([{'role': 'user', 'content': text}], *args, **kwargs)
        dialog_module.process_query = patched_process_query

    return True


# === CLI ===

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--age', type=int, default=None, help='学生年龄 (>=60 自动银发)')
    p.add_argument('--time', type=int, default=30, help='每天练习分钟')
    p.add_argument('--days', type=int, default=7, help='天数')
    p.add_argument('--demo', action='store_true', help='演示生成')
    p.add_argument('--json', action='store_true', help='JSON 输出')
    p.add_argument('--dim', default=None, help='JSON 格式 5 维分数 (e.g. {"pitch": 70, "expressiveness": 65})')
    args = p.parse_args()

    if args.demo or args.dim:
        if args.dim:
            dim_scores = json.loads(args.dim)
        else:
            dim_scores = None
        weakness = WeaknessDetector(dim_scores)
        spaced = SpacedRepetition()
        planner = AdaptivePlanner(age=args.age, time_per_day_min=args.time, days=args.days)
        planner.weakness_detector = weakness
        planner.spaced_rep = spaced
        plan = planner.generate_week_plan()
        if args.json:
            print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(planner.format_plan(plan))
    else:
        planner = AdaptivePlanner(age=args.age, time_per_day_min=args.time, days=args.days)
        plan = planner.generate_week_plan()
        if args.json:
            print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(planner.format_plan(plan))


if __name__ == '__main__':
    main()
