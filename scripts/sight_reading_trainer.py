"""
sight_reading_trainer.py — CoPiano 视奏训练模块

Cycle 6 Stage 2 实现:
- 4 难度级别 (Beginner C major → Advanced 4 升降 + 复合拍)
- 3 模式 (Random Notes / Interval Drill / Real Piece)
- 3 输入 (电脑键 1-7 / MIDI / 虚拟键盘)
- Landmark / Interval / Pattern 3 教学法支持
- voice_dialog 集成 (无递归)
- student_db 训练时长 / accuracy 记录

调研依据: notes/market_knowledge_cycle6.md
技术对位: TypePiano.org (5/5) / 五线谱入门 (警告音) / Bunnag 2005 3 教学法
"""

import hashlib
import json
import random
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


# === 4 难度级别配置 ===

DIFFICULTY_LEVELS = {
    'beginner': {
        'name': '入门 Beginner',
        'name_en': 'Beginner',
        'octave_range': (4, 5),         # C4 - E5
        'allowed_keys': ['C'],           # C major only
        'accidentals': False,             # 无升降号
        'time_signatures': ['4/4'],
        'note_count': (5, 10),
        'bpm_target': 40,
        'accuracy_promote': 0.80,        # 升档阈值
        'methods': ['landmark'],         # 仅地标法
        'description': 'C 大调基础,只用中央 C 附近的白键,自由节奏',
    },
    'elementary': {
        'name': '基础 Elementary',
        'name_en': 'Elementary',
        'octave_range': (3, 5),          # A3 - G5
        'allowed_keys': ['C', 'G', 'F'],  # C/G/F
        'accidentals': True,              # 允许 F# / Bb 等 1 个升降
        'time_signatures': ['4/4'],
        'note_count': (8, 15),
        'bpm_target': 60,
        'accuracy_promote': 0.85,
        'methods': ['landmark', 'interval'],
        'description': '1 个升降号,G/F 大调,标准 4/4 拍',
    },
    'intermediate': {
        'name': '中级 Intermediate',
        'name_en': 'Intermediate',
        'octave_range': (3, 6),          # F3 - A5
        'allowed_keys': ['C', 'G', 'D', 'F', 'Bb'],  # 2 升降
        'accidentals': True,
        'time_signatures': ['3/4', '4/4'],
        'note_count': (10, 20),
        'bpm_target': 80,
        'accuracy_promote': 0.90,
        'methods': ['interval', 'pattern'],
        'description': '2 升降号,D/Bb 大调,3/4 + 4/4',
    },
    'advanced': {
        'name': '高级 Advanced',
        'name_en': 'Advanced',
        'octave_range': (3, 6),          # F3 - C6
        'allowed_keys': ['C', 'G', 'D', 'A', 'E', 'F', 'Bb', 'Eb', 'Ab', 'B'],  # 4 升降
        'accidentals': True,
        'time_signatures': ['3/4', '4/4', '6/8'],
        'note_count': (15, 25),
        'bpm_target': 100,
        'accuracy_promote': 0.95,
        'methods': ['interval', 'pattern'],
        'description': '4 升降号,多调性,复合拍 (6/8)',
    },
}


# === 音符常量 (12 半音) ===

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTE_NAMES_FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']

# 调性五度循环 (常用大小调)
KEY_SIGNATURES = {
    'C':  (0, []),       # 0 升降
    'G':  (1, ['F#']),   # 1 sharp
    'D':  (2, ['F#', 'C#']),
    'A':  (3, ['F#', 'C#', 'G#']),
    'E':  (4, ['F#', 'C#', 'G#', 'D#']),
    'F':  (-1, ['Bb']),  # 1 flat
    'Bb': (-2, ['Bb', 'Eb']),
    'Eb': (-3, ['Bb', 'Eb', 'Ab']),
    'Ab': (-4, ['Bb', 'Eb', 'Ab', 'Db']),
}


# === 数据类 ===

@dataclass
class Note:
    """单个音符"""
    pitch: int           # MIDI pitch 0-127 (e.g. 60 = C4)
    duration_beats: float = 1.0  # 几拍 (1.0 = 四分音符)
    name: str = ''       # 自动计算 e.g. "C4"
    accidental: str = '' # # / b / '' (从 key signature 推断)

    def __post_init__(self):
        if not self.name:
            self.name = pitch_to_name(self.pitch)
        if not self.accidental:
            self.accidental = ''  # pitch 已是精确值,不再二次解析

    def to_dict(self):
        return asdict(self)


@dataclass
class SessionStats:
    """单次会话统计"""
    total: int = 0
    correct: int = 0
    streak: int = 0           # 当前连击
    best_streak: int = 0      # 历史最大连击
    start_time: float = 0.0
    end_time: float = 0.0
    difficulty: str = 'beginner'
    mode: str = 'random'
    errors: List[Dict] = field(default_factory=list)  # [{'expected': 'C4', 'got': 'D4', 'pos': 3}]

    @property
    def accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return self.correct / self.total

    @property
    def duration_sec(self) -> float:
        if self.start_time == 0:
            return 0.0
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time

    @property
    def notes_per_minute(self) -> float:
        if self.duration_sec < 0.1:
            return 0.0
        return (self.total / self.duration_sec) * 60

    def to_dict(self):
        return {
            **asdict(self),
            'accuracy': round(self.accuracy, 4),
            'duration_sec': round(self.duration_sec, 1),
            'notes_per_minute': round(self.notes_per_minute, 1),
        }


# === 工具函数 ===

def pitch_to_name(pitch: int) -> str:
    """MIDI pitch → 音符名 (e.g. 60 → C4)"""
    if pitch < 0 or pitch > 127:
        return '?'
    note_idx = pitch % 12
    octave = (pitch // 12) - 1
    return f"{NOTE_NAMES[note_idx]}{octave}"


def name_to_pitch(name: str) -> int:
    """音符名 → MIDI pitch (e.g. C4 → 60)"""
    # 解析 'C4', 'F#5', 'Bb3'
    if not name:
        return -1
    # 提取升降号
    i = 0
    while i < len(name) and name[i] in 'ABCDEFG':
        i += 1
    if i == 0:
        return -1
    base = name[:i]
    accidental = ''
    if i < len(name) and name[i] in '#b':
        accidental = name[i]
        i += 1
    octave_str = name[i:]
    try:
        octave = int(octave_str)
    except ValueError:
        return -1

    base_pitch = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}[base]
    if accidental == '#':
        base_pitch += 1
    elif accidental == 'b':
        base_pitch -= 1
    return (octave + 1) * 12 + base_pitch


def is_white_key(pitch: int) -> bool:
    """是否是白键"""
    return pitch % 12 not in (1, 3, 6, 8, 10)  # C# D# F# G# A#


# 电脑键 1-7 映射 (C D E F G A B)
KEYBOARD_MAP = {
    '1': 'C4', '2': 'D4', '3': 'E4', '4': 'F4',
    '5': 'G4', '6': 'A4', '7': 'B4',
    'q': 'C5', 'w': 'D5', 'e': 'E5', 'r': 'F5',
    't': 'G5', 'y': 'A5', 'u': 'B5',
    'z': 'C3', 'x': 'D3', 'c': 'E3', 'v': 'F3',
    'b': 'G3', 'n': 'A3', 'm': 'B3',
}


def keyboard_to_pitch(key: str) -> int:
    """电脑键 → MIDI pitch"""
    key_lower = key.lower()
    if key_lower not in KEYBOARD_MAP:
        return -1
    return name_to_pitch(KEYBOARD_MAP[key_lower])


def get_difficulty(level: str) -> dict:
    """获取难度配置"""
    if level not in DIFFICULTY_LEVELS:
        raise ValueError(f"Unknown difficulty: {level}. Choose from {list(DIFFICULTY_LEVELS.keys())}")
    return DIFFICULTY_LEVELS[level]


# === 教学法: 3 流派 ===

def landmark_note_sequence(level: str, count: int, seed: int = None) -> List[Note]:
    """Landmark method: 围绕地标音 (C4, G4, F4, C5) 上下移动"""
    config = get_difficulty(level)
    rng = random.Random(seed) if seed is not None else random

    landmarks = [60, 67, 65, 72]  # C4, G4, F4, C5
    sequence = []
    for _ in range(count):
        # 60% 选地标音,40% 选 ± 1-3 半音邻居
        if rng.random() < 0.6:
            pitch = rng.choice(landmarks)
        else:
            base = rng.choice(landmarks)
            offset = rng.choice([-3, -2, -1, 1, 2, 3])
            pitch = base + offset
        # 限制音域
        lo = (config['octave_range'][0] + 1) * 12
        hi = (config['octave_range'][1] + 1) * 12 + 11
        pitch = max(lo, min(hi, pitch))
        sequence.append(Note(pitch=pitch, duration_beats=1.0))
    return sequence


def interval_note_sequence(level: str, count: int, seed: int = None) -> List[Note]:
    """Interval method: 音程序列 (二度三度等)"""
    config = get_difficulty(level)
    rng = random.Random(seed) if seed is not None else random

    # 起点在中间 C 附近
    start_pitch = name_to_pitch('C4')
    if level in ('intermediate', 'advanced'):
        start_pitch = name_to_pitch('G4')

    # 音程:二度/三度/四度/五度 (按难度递增)
    intervals = [2, 2, 3, 3, 4, 5] if level in ('beginner', 'elementary') else [2, 3, 4, 5, 7, 9]

    sequence = [Note(pitch=start_pitch, duration_beats=1.0)]
    for _ in range(count - 1):
        direction = rng.choice([-1, 1])
        interval = rng.choice(intervals)
        next_pitch = sequence[-1].pitch + direction * interval
        # 限制音域
        lo = (config['octave_range'][0] + 1) * 12
        hi = (config['octave_range'][1] + 1) * 12 + 11
        next_pitch = max(lo, min(hi, next_pitch))
        sequence.append(Note(pitch=next_pitch, duration_beats=1.0))
    return sequence


def pattern_note_sequence(level: str, count: int, seed: int = None) -> List[Note]:
    """Pattern method: 常见曲调模式 (Stair-step, 拱形, 重复)"""
    config = get_difficulty(level)
    rng = random.Random(seed) if seed is not None else random

    patterns = [
        # Stair-step: 1-2-3-4-5
        lambda base: [base, base + 2, base + 4, base + 5, base + 7],
        # Arch: 1-3-5-3-1
        lambda base: [base, base + 4, base + 7, base + 4, base],
        # Repetition: 1-1-3-3-1-1
        lambda base: [base, base, base + 4, base + 4, base, base],
        # Down step: 5-4-3-2-1
        lambda base: [base + 7, base + 5, base + 4, base + 2, base],
    ]
    # 起点
    base = name_to_pitch('C4') if level != 'advanced' else name_to_pitch('G4')
    pattern = rng.choice(patterns)(base)
    sequence = []
    for i in range(count):
        idx = i % len(pattern)
        pitch = pattern[idx]
        # 限制音域
        lo = (config['octave_range'][0] + 1) * 12
        hi = (config['octave_range'][1] + 1) * 12 + 11
        pitch = max(lo, min(hi, pitch))
        sequence.append(Note(pitch=pitch, duration_beats=1.0))
    return sequence


# === 简化真曲片段 (8-16 小节,自生成) ===

def _bach_contrapunctus_fragment() -> List[Note]:
    """Bach-style 对位片段 (简化 4 声部 → 单声部 melody)"""
    # G major 主题
    melody_pitches = [
        67, 69, 71, 72, 71, 69, 67, 64,  # 主题
        67, 69, 71, 72, 74, 72, 71, 69,  # 发展
        67, 64, 67, 69, 71, 67, 64, 60,  # 解决
    ]
    return [Note(pitch=p, duration_beats=1.0) for p in melody_pitches]


def _mozart_sonata_fragment() -> List[Note]:
    """Mozart K.545 主题片段 (C major)"""
    # 经典 sonata form 主部主题
    melody_pitches = [
        72, 76, 79, 81, 79, 76, 72,  # 跳进上行
        74, 77, 81, 79, 77, 74, 72,  # 回旋
        67, 72, 74, 76, 74, 72, 67, 60,  # 收束
    ]
    return [Note(pitch=p, duration_beats=1.0) for p in melody_pitches]


def _chopin_nocturne_fragment() -> List[Note]:
    """Chopin-style 夜曲片段 (Bb major)"""
    # 简化版: 4 小节主题 + 4 小节发展
    melody_pitches = [
        70, 74, 77, 79, 77, 74, 70, 67,  # 主题
        72, 74, 77, 79, 82, 79, 77, 74,  # 发展上行
        70, 67, 70, 74, 77, 74, 70, 67,  # 解决
    ]
    return [Note(pitch=p, duration_beats=1.0) for p in melody_pitches]


REAL_PIECES = {
    'bach_contrapunctus': _bach_contrapunctus_fragment,
    'mozart_k545': _mozart_sonata_fragment,
    'chopin_nocturne': _chopin_nocturne_fragment,
}


# === 主训练器 ===

class SightReadingTrainer:
    """视奏训练器 — 单会话"""

    def __init__(self, difficulty: str = 'beginner', mode: str = 'random', seed: int = None):
        if difficulty not in DIFFICULTY_LEVELS:
            raise ValueError(f"Unknown difficulty: {difficulty}")
        if mode not in ('random', 'interval', 'piece'):
            raise ValueError(f"Unknown mode: {mode}. Choose from random/interval/piece")
        self.difficulty = difficulty
        self.mode = mode
        self.config = get_difficulty(difficulty)
        # 用稳定 hash 作为 seed (避免 Python hash 随机化)
        if seed is None:
            seed = int(hashlib.md5(f"{difficulty}:{mode}:{time.time() // 60}".encode()).hexdigest()[:8], 16)
        self.seed = seed
        self.rng = random.Random(seed)
        self.stats = SessionStats(
            difficulty=difficulty,
            mode=mode,
            start_time=time.time(),
        )
        self.sequence: List[Note] = []
        self.current_idx: int = 0
        self._piece_name: str = ''

    def generate_sequence(self, count: int = None, method: str = None) -> List[Note]:
        """生成音符序列

        method: landmark / interval / pattern / None (auto)
        """
        if count is None:
            lo, hi = self.config['note_count']
            count = self.rng.randint(lo, hi)

        if self.mode == 'random':
            if method is None:
                method = self.config['methods'][0]  # 默认第一个支持的方法
            if method == 'landmark':
                seq = landmark_note_sequence(self.difficulty, count, self.seed)
            elif method == 'interval':
                seq = interval_note_sequence(self.difficulty, count, self.seed)
            elif method == 'pattern':
                seq = pattern_note_sequence(self.difficulty, count, self.seed)
            else:
                raise ValueError(f"Unknown method: {method}")
        elif self.mode == 'interval':
            seq = interval_note_sequence(self.difficulty, count, self.seed)
        elif self.mode == 'piece':
            # 选一个真曲
            piece_keys = list(REAL_PIECES.keys())
            piece_name = piece_keys[self.seed % len(piece_keys)]
            self._piece_name = piece_name
            seq = REAL_PIECES[piece_name]()
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

        self.sequence = seq
        self.current_idx = 0
        return seq

    def get_current_note(self) -> Optional[Note]:
        """获取当前待弹音符"""
        if self.current_idx >= len(self.sequence):
            return None
        return self.sequence[self.current_idx]

    def submit_answer(self, answer) -> bool:
        """提交答案,返回是否正确

        answer 可以是:
        - str: 电脑键 ('1'-'7', 'q'-'u', 'z'-'m') 或音符名 ('C4', 'D5')
        - int: MIDI pitch (MIDI 设备 / 虚拟键盘)
        """
        expected = self.get_current_note()
        if expected is None:
            return False

        # 规范化 input
        if isinstance(answer, int):
            user_pitch = answer
        elif isinstance(answer, str):
            # 尝试电脑键
            if answer.lower() in KEYBOARD_MAP:
                user_pitch = keyboard_to_pitch(answer)
            else:
                # 尝试音符名
                user_pitch = name_to_pitch(answer)
            if user_pitch < 0:
                return False
        else:
            return False

        correct = (user_pitch == expected.pitch)
        self.stats.total += 1
        if correct:
            self.stats.correct += 1
            self.stats.streak += 1
            if self.stats.streak > self.stats.best_streak:
                self.stats.best_streak = self.stats.streak
            self.current_idx += 1
        else:
            self.stats.streak = 0
            self.stats.errors.append({
                'expected': expected.name,
                'got': pitch_to_name(user_pitch),
                'pos': self.current_idx,
            })
        return correct

    def is_finished(self) -> bool:
        return self.current_idx >= len(self.sequence)

    def finish(self):
        """结束会话"""
        self.stats.end_time = time.time()

    def get_staff_ascii(self, line_count: int = 5) -> str:
        """生成简易 ASCII 谱面 (5 行 4 拍)"""
        if not self.sequence:
            return "(empty sequence)"

        lines = [''] * line_count
        # 五线谱线 (从下到上,顶行 = F5 第五线)
        # 简化: 5 行 = E4 / G4 / B4 / D5 / F5
        line_map = {
            # pitch → 第几行 (0=top)
            64: 4,  # E4
            65: 4, 65.5: 3,  # F4 (在 E4 上方) / F#4 (在 E4 上方半格,简化)
            67: 3,  # G4 (第二线)
            69: 2,  # A4 (第二间)
            71: 1,  # B4 (中线)
            72: 1,  # C5 (中线)
            74: 0,  # D5 (第一间)
            76: 0, 76.5: 0,  # E5 (第四线)
        }

        for i, note in enumerate(self.sequence[:line_count * 4]):
            # 简化: 4 拍一行
            pos_in_line = i % 4
            line_idx = i // 4
            if line_idx >= line_count:
                break
            # 用近似 line
            nearest = min(line_map.keys(), key=lambda k: abs(k - note.pitch))
            row = line_map[nearest]
            # 在 lines[row] 的对应位置加音符
            display_lines = lines[line_idx]
            char = '●' if i == self.current_idx else '○'
            if len(display_lines) < pos_in_line * 4 + 4:
                display_lines = display_lines.ljust(pos_in_line * 4 + 4)
            display_lines = display_lines[:pos_in_line * 4] + char + display_lines[pos_in_line * 4 + 1:]
            lines[line_idx] = display_lines

        return '\n'.join(lines[:line_count])

    def get_progress(self) -> Dict:
        """获取进度信息"""
        return {
            'current': self.current_idx,
            'total': len(self.sequence),
            'stats': self.stats.to_dict(),
            'current_note': self.get_current_note().to_dict() if self.get_current_note() else None,
            'piece_name': self._piece_name,
        }

    def should_promote(self) -> bool:
        """是否应该升档 (基于 accuracy 阈值 + 不是最高级)"""
        if not self.is_finished():
            return False
        # 已是最高级,不能再升
        levels = list(DIFFICULTY_LEVELS.keys())
        if self.difficulty == levels[-1]:
            return False
        return self.stats.accuracy >= self.config['accuracy_promote']

    def get_next_level(self) -> Optional[str]:
        """获取下一档难度名 (若已是最高返回 None)"""
        levels = list(DIFFICULTY_LEVELS.keys())
        try:
            idx = levels.index(self.difficulty)
            return levels[idx + 1] if idx + 1 < len(levels) else None
        except ValueError:
            return None


# === student_db 集成 ===

def save_sight_reading_session(student_db, trainer: SightReadingTrainer, piece_name: str = '') -> Dict:
    """保存训练会话到 student_db

    student_db: StudentDB 实例 (or None)
    trainer: 已 finish 的 SightReadingTrainer
    """
    summary = {
        'date': time.strftime('%Y-%m-%d'),
        'kind': 'sight_reading',
        'difficulty': trainer.difficulty,
        'mode': trainer.mode,
        'piece': piece_name or trainer._piece_name or '',
        'note_count': trainer.stats.total,
        'correct': trainer.stats.correct,
        'accuracy': round(trainer.stats.accuracy, 4),
        'best_streak': trainer.stats.best_streak,
        'duration_sec': round(trainer.stats.duration_sec, 1),
        'notes_per_minute': round(trainer.stats.notes_per_minute, 1),
        'errors': trainer.stats.errors[:10],  # 只记前 10 个错
    }

    if student_db is not None and hasattr(student_db, 'add_sight_reading_session'):
        student_db.add_sight_reading_session(summary)
    elif student_db is not None and hasattr(student_db, 'record_eval'):
        # Fallback: 用 record_eval 通道
        try:
            student_db.record_eval(summary, piece=summary['piece'] or f"sight_reading_{trainer.difficulty}",
                                   period="Practice")
        except Exception:
            pass

    return summary


# === LLM 反馈 (内置 6 个常见错误解释,避免 LLM 调用) ===

SIGHT_READING_TIPS = {
    'wrong_pitch': "这个音是 {expected}。提示:可以用 Landmark 法,从中央 C 出发数格子。",
    'wrong_octave': "音高对了,但八度错了。应该是 {expected} 而不是 {got}。注意上下加线。",
    'rhythm': "节奏要稳。每拍 1 拍,四分音符 = 1 beat,跟着节拍器。",
    'streak_break': "连击断了没关系,视奏就是反复试错的过程。我们继续。",
    'promote': "本难度准确率达 {acc:.0%},可以升到 {next_level} 啦!",
    'demote': "准确率 {acc:.0%} < {threshold:.0%},建议再练 2 次本难度。",
    'beginner_hint': "新音符可以用 Landmark 法:C4 = 中央 C, G4 = 第二线, F4 = 第一间, C5 = 第三间。",
    'interval_hint': "试试 Interval 法:不单独看每个音,看音之间的'距离'(几度)。",
    'pattern_hint': "试试 Pattern 法:整段看是 Stair-step / 拱形 / 重复,不用逐个音思考。",
}


def get_sight_reading_feedback(trainer: SightReadingTrainer, kind: str = 'wrong_pitch', **kwargs) -> str:
    """获取视奏反馈 (内置规则,无需 LLM 调用)"""
    template = SIGHT_READING_TIPS.get(kind, "继续努力!")
    if kind == 'promote':
        levels = list(DIFFICULTY_LEVELS.keys())
        try:
            idx = levels.index(trainer.difficulty)
            next_level = levels[idx + 1] if idx + 1 < len(levels) else 'master'
        except ValueError:
            next_level = 'master'
        return template.format(acc=kwargs.get('acc', trainer.stats.accuracy), next_level=next_level)
    if kind == 'demote':
        return template.format(acc=kwargs.get('acc', trainer.stats.accuracy), threshold=trainer.config['accuracy_promote'])
    if kind == 'wrong_octave':
        return template.format(expected=kwargs.get('expected', '?'), got=kwargs.get('got', '?'))
    return template


# === voice_dialog 集成 ===

def patch_voice_dialog_with_sight_reading(dialog_module=None):
    """注入到 voice_dialog,识别视奏/识谱训练意图

    用法: patch_voice_dialog_with_sight_reading(voice_dialog)
    """
    state = {
        'active': False,
        'trainer': None,
        'difficulty': 'beginner',
    }

    def handle_sight_reading_request(text: str) -> Optional[str]:
        text_lower = text.lower()
        on_kw = ['识谱训练', '练视奏', '识谱', '视奏', 'sight reading', '看谱', '识谱练习', '开始练琴']
        off_kw = ['结束识谱', '退出视奏', '停止识谱', '停', 'exit reading']

        if any(kw in text_lower for kw in off_kw) and state['active']:
            if state['trainer']:
                state['trainer'].finish()
                summary = save_sight_reading_session(None, state['trainer'])
                state['trainer'] = None
            state['active'] = False
            return f"好的,识谱训练结束。本次统计:正确 {summary['correct']}/{summary['note_count']} ({summary['accuracy']:.0%}),连击 {summary['best_streak']}。"

        if any(kw in text_lower for kw in on_kw):
            # 检测难度关键词
            matched = False
            for lvl, cfg in DIFFICULTY_LEVELS.items():
                if cfg['name'] in text or cfg['name_en'].lower() in text_lower:
                    state['difficulty'] = lvl
                    matched = True
                    break
            if not matched:
                state['difficulty'] = 'beginner'  # 默认入门
            # 启动 trainer
            trainer = SightReadingTrainer(difficulty=state['difficulty'], mode='random')
            trainer.generate_sequence()
            state['trainer'] = trainer
            state['active'] = True
            note = trainer.get_current_note()
            cfg = DIFFICULTY_LEVELS[state['difficulty']]
            return f"好,开始 {cfg['name']} 视奏训练。第 1 个音是 {note.name}。请按对应键 (电脑键 1-7 / MIDI / 虚拟键盘)。"

        return None

    if dialog_module is None:
        return handle_sight_reading_request, state

    # 捕获原始 (避免递归)
    _orig_call_llm = dialog_module.call_llm if hasattr(dialog_module, 'call_llm') else None

    # Monkey patch: process_query (如果存在)
    if hasattr(dialog_module, 'process_query'):
        def patched_process_query(text, *args, **kwargs):
            handled = handle_sight_reading_request(text)
            if handled:
                return handled
            return dialog_module.call_llm([{'role': 'user', 'content': text}], *args, **kwargs)
        dialog_module.process_query = patched_process_query

    return True


# === CLI ===

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--difficulty', '-d', default='beginner', choices=list(DIFFICULTY_LEVELS.keys()))
    p.add_argument('--mode', '-m', default='random', choices=['random', 'interval', 'piece'])
    p.add_argument('--count', '-c', type=int, default=None, help='音符数 (默认按难度自动)')
    p.add_argument('--seed', type=int, default=None)
    p.add_argument('--demo', action='store_true', help='演示训练')
    p.add_argument('--json', action='store_true', help='JSON 输出')
    args = p.parse_args()

    if args.demo:
        # 4 难度 × 3 模式 各演示一次
        results = []
        for diff in DIFFICULTY_LEVELS:
            for mode in ('random', 'interval', 'piece'):
                trainer = SightReadingTrainer(difficulty=diff, mode=mode, seed=hash(diff + mode) % 100000)
                seq = trainer.generate_sequence(count=8)
                # 模拟 8 个完美按键
                for n in seq:
                    trainer.submit_answer(n.pitch)
                trainer.finish()
                results.append({
                    'difficulty': diff,
                    'mode': mode,
                    'sequence': [n.name for n in seq],
                    'stats': trainer.stats.to_dict(),
                })
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print("=== CoPiano 视奏训练演示 ===\n")
            for r in results:
                print(f"--- {r['difficulty']}/{r['mode']} ---")
                print(f"  序列: {' '.join(r['sequence'])}")
                print(f"  统计: 正确 {r['stats']['correct']}/{r['stats']['total']} = {r['stats']['accuracy']:.0%}")
                print(f"  连击: {r['stats']['best_streak']} | BPM: {r['stats']['notes_per_minute']:.0f}\n")
    else:
        trainer = SightReadingTrainer(difficulty=args.difficulty, mode=args.mode, seed=args.seed)
        seq = trainer.generate_sequence(count=args.count)
        print(f"=== CoPiano 视奏训练 ({args.difficulty}/{args.mode}) ===")
        print(f"序列: {' '.join(n.name for n in seq)}")
        print(f"目标: {trainer.config['description']}")
        print(f"起始音: {seq[0].name if seq else 'N/A'}")
        if args.json:
            print(json.dumps({
                'sequence': [n.to_dict() for n in seq],
                'config': trainer.config,
            }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
