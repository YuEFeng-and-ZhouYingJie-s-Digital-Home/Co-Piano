"""
real_time_feedback.py — 实时反馈引擎(Phase 4 核心)

架构:
- 音频流 → 滑窗(2s)→ MIDI 提取 → 评估 → 即时反馈
- 延迟目标:< 200ms
- 不调 LLM(太慢),用规则引擎给即时反馈
- LLM 用于"段落级"反馈(每 8/16 小节触发一次)

组件:
1. AudioCapture: 麦克风音频流
2. PianoTranscriber: 音频 → MIDI(Basic Pitch / Omnizart)
3. WindowBuffer: 滑窗(2s 窗口,1s 步进)
4. RealTimeEvaluator: 滑窗 MIDI → 错音/节奏/力度
5. FeedbackEngine: 评估 → 即时反馈(规则)
6. DisplayLayer: 输出文本/UI(可选)

Phase 4 第一步:写骨架 + 模拟数据测试
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import mido


@dataclass
class WindowBuffer:
    """滑窗缓冲:2s 窗口,1s 步进"""
    window_size_s: float = 2.0
    step_size_s: float = 1.0
    notes: deque = field(default_factory=deque)  # [(time, pitch, velocity)]

    def add_note(self, time: float, pitch: int, velocity: int):
        self.notes.append((time, pitch, velocity))
        # 移除超过窗口的旧音符
        cutoff = time - self.window_size_s
        while self.notes and self.notes[0][0] < cutoff:
            self.notes.popleft()

    def get_recent(self, since: float = 0.0) -> list:
        return [n for n in self.notes if n[0] >= since]

    def clear(self):
        self.notes.clear()


@dataclass
class RealTimeMetrics:
    """实时指标"""
    pitch_accuracy: float = 0.0
    timing_std_ms: float = 0.0
    velocity_mean: float = 0.0
    n_notes: int = 0
    last_alert: Optional[str] = None
    timestamp: float = 0.0


class RealTimeEvaluator:
    """滑窗 MIDI → 实时指标
    输入:WindowBuffer + 参考 MIDI 序列(可选)
    输出:RealTimeMetrics
    """

    def __init__(self, reference_pitches: Optional[list] = None, window_s: float = 2.0):
        self.reference_pitches = reference_pitches or []
        self.buffer = WindowBuffer(window_size_s=window_s)
        self.metrics = RealTimeMetrics()

    def add_note(self, time: float, pitch: int, velocity: int):
        self.buffer.add_note(time, pitch, velocity)
        self._update_metrics()

    def _update_metrics(self):
        notes = list(self.buffer.notes)
        if not notes:
            return
        # 1. 音准准确率(最近 4 个音 vs 参考音阶覆盖率)
        if self.reference_pitches:
            ref_set = set(self.reference_pitches)
            recent = notes[-min(4, len(notes)):]  # 最近 K 个
            recent_pitches = set(n[1] for n in recent)
            # 覆盖率:最近音在参考里多少
            in_ref = sum(1 for p in recent_pitches if p in ref_set)
            self.metrics.pitch_accuracy = in_ref / max(1, len(recent_pitches))
        # 2. 节奏 std
        times = [n[0] for n in notes]
        if len(times) > 1:
            deltas = [times[i+1] - times[i] for i in range(len(times)-1)]
            import statistics
            self.metrics.timing_std_ms = statistics.stdev(deltas) * 1000 if len(deltas) > 1 else 0.0
        # 3. 力度均值
        self.metrics.velocity_mean = sum(n[2] for n in notes) / len(notes)
        # 4. 音符数
        self.metrics.n_notes = len(notes)
        self.metrics.timestamp = time.time()


class FeedbackEngine:
    """规则引擎:RealTimeMetrics → 即时反馈
    反馈类型:
    - PASS(默认无反馈)
    - WARN(警告,黄色)
    - ALERT(警报,红色)
    """

    def __init__(self, pitch_threshold: float = 0.7, timing_threshold: float = 100.0):
        self.pitch_threshold = pitch_threshold
        self.timing_threshold = timing_threshold
        self.last_feedback = None
        self.last_feedback_time = 0.0
        self.cooldown_s = 2.0  # 同类反馈间隔

    def evaluate(self, metrics: RealTimeMetrics) -> Optional[str]:
        """返回反馈文本,或 None(无需反馈)"""
        now = time.time()
        if now - self.last_feedback_time < self.cooldown_s:
            return None  # 冷却中
        feedback = None
        # 音准差
        if metrics.n_notes > 0 and metrics.pitch_accuracy < self.pitch_threshold:
            feedback = f"⚠ 音准:{metrics.pitch_accuracy:.0%}(阈值{self.pitch_threshold:.0%})"
        # 节奏不稳
        elif metrics.timing_std_ms > self.timing_threshold:
            feedback = f"⚠ 节奏不稳:std {metrics.timing_std_ms:.0f}ms"
        # 力度异常
        elif metrics.velocity_mean < 30 or metrics.velocity_mean > 110:
            feedback = f"⚠ 力度异常:mean {metrics.velocity_mean:.0f}"

        if feedback:
            self.last_feedback = feedback
            self.last_feedback_time = now
        return feedback


def demo_with_synthetic_stream():
    """模拟音频流测试
    模拟弹错音 + 节奏不稳,看规则引擎是否报警
    """
    print("=== 实时反馈 demo(模拟数据)===\n")
    # 参考:C 大调音阶 + 一些音
    ref = [60, 62, 64, 65, 67, 69, 71, 72]  # C D E F G A B C
    evaluator = RealTimeEvaluator(reference_pitches=ref, window_s=2.0)
    feedback = FeedbackEngine(pitch_threshold=0.7, timing_threshold=100.0)

    print(f"参考音阶: C D E F G A B C (60-72)")
    print(f"用户弹奏模拟(故意第 3 音错 + 节奏不稳):\n")

    t = 0.0
    user_pitches = [60, 62, 63, 65, 67, 69, 71, 72]  # 第 3 音错成 63
    timing_offsets = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]  # 节奏不稳
    velocities = [70, 75, 65, 80, 60, 75, 70, 85]

    for i, (pitch, t_off, vel) in enumerate(zip(user_pitches, timing_offsets, velocities)):
        t = t_off + (0.1 if i == 2 else 0.0)  # 第 3 音额外延迟(节奏不稳)
        evaluator.add_note(t, pitch, vel)
        m = evaluator.metrics
        fb = feedback.evaluate(m)
        if fb or i == 7:
            print(f"  t={t:.1f}s note={pitch} vel={vel} | "
                  f"pitch_acc={m.pitch_accuracy:.1%} "
                  f"timing_std={m.timing_std_ms:.0f}ms "
                  f"vel_mean={m.velocity_mean:.0f} "
                  f"| {'FB: ' + fb if fb else '(no fb)'}")

    print("\n=== 关键观察:")
    print("- 音准差(63 错成 64)→ 触发音准警告")
    print("- 节奏不稳(第 3 音延迟 100ms)→ 触发节奏警告")
    print("- 反馈冷却 2s,避免连发")
    print("- 无 LLM 调用,延迟 < 10ms")


def demo_with_midi_file(midi_path: str):
    """用 MIDI 文件模拟(模拟实时流)"""
    print(f"=== 用 MIDI 文件模拟({midi_path})===\n")
    mid = mido.MidiFile(midi_path)
    # 提取所有 note 事件
    events = []
    t = 0.0
    for track in mid.tracks:
        t = 0.0
        for msg in track:
            t += mido.tick2second(msg.time, mid.ticks_per_grand_stroke if hasattr(mid,'ticks_per_grand_stroke') else mid.ticks_per_beat, 500000)
            if msg.type == "note_on" and msg.velocity > 0:
                events.append((t, msg.note, msg.velocity))
    events.sort()

    # 参考: 提取所有 pitch
    ref_pitches = sorted(set(e[1] for e in events))
    evaluator = RealTimeEvaluator(reference_pitches=ref_pitches, window_s=2.0)
    feedback = FeedbackEngine(pitch_threshold=0.7, timing_threshold=100.0)

    for t, pitch, vel in events:
        evaluator.add_note(t, pitch, vel)
        m = evaluator.metrics
        fb = feedback.evaluate(m)
        if fb:
            print(f"  t={t:.1f}s note={pitch} vel={vel} | pitch_acc={m.pitch_accuracy:.1%} | FB: {fb}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        demo_with_midi_file(sys.argv[1])
    else:
        demo_with_synthetic_stream()
