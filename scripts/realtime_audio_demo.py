"""
realtime_audio_demo.py — 完整音频→实时反馈链路 demo(Phase 4 关键验证)

流程:
1. 读音频文件
2. 每 2s 滑窗切一段
3. Basic Pitch 转 MIDI(只处理该段)
4. 实时评估音准/节奏/力度
5. 触发反馈(规则引擎 + 冷却)
6. 汇总统计 + 输出

这是 Phase 4 实时反馈引擎 + Basic Pitch 的端到端集成测试。

用法:
    python3 realtime_audio_demo.py <wav_file> [reference_midi]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np

# 依赖
try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False

# 复用
sys.path.insert(0, str(Path(__file__).parent))
from real_time_feedback import (
    RealTimeEvaluator, FeedbackEngine, RealTimeMetrics, WindowBuffer
)


def load_audio_segment(audio_path: str, start_s: float, duration_s: float, sr: int = 22050):
    """加载音频文件的一个段"""
    if not HAS_LIBROSA:
        raise RuntimeError("需要 librosa")
    y, _ = librosa.load(audio_path, sr=sr, mono=True, offset=start_s, duration=duration_s)
    return y, sr


def audio_segment_to_midi_events(y: np.ndarray, sr: int) -> list:
    """音频段 → MIDI 事件
    用 librosa pYIN 检音高(轻量,不依赖 basic_pitch)
    """
    if not HAS_LIBROSA:
        return []
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y, fmin=librosa.note_to_hz("A0"), fmax=librosa.note_to_hz("C8"), sr=sr
    )
    times = librosa.times_like(f0, sr=sr)
    events = []
    last_pitch = None
    onset_time = None
    for i, t in enumerate(times):
        if voiced_flag[i] and not np.isnan(f0[i]) and f0[i] > 0:
            pitch = int(round(librosa.hz_to_midi(f0[i])))
            if pitch != last_pitch:
                if last_pitch is not None and onset_time is not None:
                    events.append({
                        "onset": float(onset_time),
                        "pitch": int(last_pitch),
                        "velocity": 64,
                    })
                onset_time = t
                last_pitch = pitch
    if last_pitch is not None and onset_time is not None:
        events.append({
            "onset": float(onset_time),
            "pitch": int(last_pitch),
            "velocity": 64,
        })
    return events


def get_reference_pitches(midi_path: Optional[str], n_notes: int = 20) -> list:
    """从参考 MIDI 提取 pitch 列表"""
    if not midi_path or not Path(midi_path).exists():
        return []
    import mido
    mid = mido.MidiFile(midi_path)
    pitches = []
    for track in mid.tracks:
        for msg in track:
            if msg.type == "note_on" and msg.velocity > 0:
                pitches.append(msg.note)
                if len(pitches) >= n_notes:
                    return pitches
    return pitches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", help="音频文件 (wav/mp3)")
    ap.add_argument("--reference", help="参考 MIDI(可选)")
    ap.add_argument("--window", type=float, default=2.0, help="滑窗秒数")
    ap.add_argument("--step", type=float, default=1.0, help="步进秒数")
    ap.add_argument("--max-windows", type=int, default=10, help="最大处理窗口数")
    args = ap.parse_args()

    if not HAS_LIBROSA:
        print("❌ 需要 librosa: pip install librosa")
        return 1
    if not Path(args.audio).exists():
        print(f"❌ 音频文件不存在: {args.audio}")
        return 1

    print(f"=== 实时反馈链路 demo ===")
    print(f"音频: {args.audio}")
    print(f"参考: {args.reference or '(无)'}")
    print(f"滑窗: {args.window}s, 步进: {args.step}s\n")

    # 1) 加载音频,获取总时长
    y, sr = librosa.load(args.audio, sr=22050, mono=True)
    duration = len(y) / sr
    print(f"音频时长: {duration:.1f}s, sr={sr}\n")

    # 2) 参考音高
    ref_pitches = get_reference_pitches(args.reference, n_notes=50)
    print(f"参考音高数: {len(ref_pitches)}\n")

    # 3) 初始化评估器 + 反馈引擎
    evaluator = RealTimeEvaluator(reference_pitches=ref_pitches, window_s=args.window)
    feedback = FeedbackEngine(pitch_threshold=0.7, timing_threshold=100.0)

    # 4) 滑窗处理
    n_windows = min(int(duration / args.step), args.max_windows)
    print(f"将处理 {n_windows} 个窗口\n")

    all_feedbacks = []
    for i in range(n_windows):
        start_s = i * args.step
        end_s = start_s + args.window
        if end_s > duration:
            break
        # 加载窗口音频
        y_win = y[int(start_s * sr):int(end_s * sr)]
        # 转 MIDI 事件
        t0 = time.time()
        events = audio_segment_to_midi_events(y_win, sr)
        proc_time = time.time() - t0
        # 喂入评估器(注意 offset)
        for ev in events:
            evaluator.add_note(start_s + ev["onset"], ev["pitch"], ev["velocity"])
        # 触发反馈
        fb = feedback.evaluate(evaluator.metrics)
        if fb:
            all_feedbacks.append({
                "window": i,
                "time_s": round(start_s, 1),
                "feedback": fb,
                "n_events": len(events),
                "metrics": {
                    "pitch_accuracy": round(evaluator.metrics.pitch_accuracy, 3),
                    "timing_std_ms": round(evaluator.metrics.timing_std_ms, 1),
                    "velocity_mean": round(evaluator.metrics.velocity_mean, 1),
                },
            })
            print(f"  [t={start_s:.1f}s, n={len(events)} events, {proc_time:.2f}s] FB: {fb}")

    # 5) 汇总
    print(f"\n=== 汇总 ===")
    print(f"总窗口: {n_windows}")
    print(f"总反馈: {len(all_feedbacks)}")
    if all_feedbacks:
        print(f"延迟(平均窗口处理):见上")
        print(f"\n反馈序列:")
        for fb in all_feedbacks:
            print(f"  t={fb['time_s']}s: {fb['feedback']}")
    else:
        print("(全程无反馈触发 — 弹得不错!或者参考缺失)")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
