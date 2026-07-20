"""
audio_to_midi.py — 音频转 MIDI(Basic Pitch 集成)

Spotify Basic Pitch:
- 轻量钢琴转 MIDI(Spotify 开源,Apache 2.0)
- 跑在 CPU/GPU/MPS 上
- 实时友好(单次转录 < 100ms)

用法:
    python3 audio_to_midi.py <wav_or_mp3> <output.mid> [onset_threshold]

Phase 4 用法:
    实时音频流 → Basic Pitch(每 2s)→ MIDI 事件 → 评估 → 反馈
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


def audio_to_midi(input_path: str, output_path: str, onset_threshold: float = 0.5) -> dict:
    """音频转 MIDI
    Returns: {n_notes, duration, processing_time_s}
    """
    from basic_pitch.inference import predict
    import numpy as np

    t0 = time.time()
    # predict 返回 (midi_data, note_events, note_probs)
    # 注: Basic Pitch 用 tensorflow,需要安装
    try:
        model_output, midi_data, note_events = predict(
            input_path,
            onset_threshold=onset_threshold,
            frame_threshold=0.3,
            minimum_note_length=0.05,  # 50ms 最短音
            minimum_frequency=None,
            maximum_frequency=None,
        )
    except Exception as e:
        # 退而求其次:用 librosa 做粗略音高检测
        return audio_to_midi_fallback(input_path, output_path)

    # 保存 MIDI
    midi_data.write(str(output_path))

    dt = time.time() - t0
    n_notes = len(note_events) if note_events is not None else 0
    duration = midi_data.get_end_time() if midi_data else 0

    return {
        "input": input_path,
        "output": output_path,
        "n_notes": n_notes,
        "duration_s": round(duration, 2),
        "processing_time_s": round(dt, 2),
        "method": "basic_pitch",
    }


def audio_to_midi_fallback(input_path: str, output_path: str) -> dict:
    """Fallback: 用 librosa + pretty_midi 做粗略音高检测
    (不依赖 tensorflow)
    """
    import librosa
    import pretty_midi
    import numpy as np

    t0 = time.time()
    # 加载音频
    y, sr = librosa.load(input_path, sr=22050, mono=True)
    duration = len(y) / sr

    # 音高检测(pYIN)
    f0, voiced_flag, voiced_prob = librosa.pyin(
        y, fmin=librosa.note_to_hz("A0"), fmax=librosa.note_to_hz("C8"), sr=sr
    )
    # 转 MIDI 音符号
    times = librosa.times_like(f0, sr=sr)
    f0_clean = f0[voiced_flag & (f0 > 0)]

    # 用 pretty_midi 写
    pm = pretty_midi.PrettyMIDI()
    inst = pretty_midi.Instrument(program=0)
    last_pitch = None
    onset_time = None
    for i, t in enumerate(times):
        if voiced_flag[i] and not np.isnan(f0[i]) and f0[i] > 0:
            pitch = int(round(librosa.hz_to_midi(f0[i])))
            if pitch != last_pitch:
                # 关闭上一个
                if last_pitch is not None and onset_time is not None:
                    note = pretty_midi.Note(
                        velocity=64, pitch=last_pitch,
                        start=onset_time, end=t
                    )
                    inst.notes.append(note)
                onset_time = t
                last_pitch = pitch
    # 关闭最后一个
    if last_pitch is not None and onset_time is not None:
        note = pretty_midi.Note(
            velocity=64, pitch=last_pitch,
            start=onset_time, end=duration
        )
        inst.notes.append(note)
    pm.instruments.append(inst)
    pm.write(output_path)

    dt = time.time() - t0
    return {
        "input": input_path,
        "output": output_path,
        "n_notes": len(inst.notes),
        "duration_s": round(duration, 2),
        "processing_time_s": round(dt, 2),
        "method": "librosa_pyin_fallback",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="输入音频 (wav/mp3)")
    ap.add_argument("output", help="输出 MIDI")
    ap.add_argument("--onset-threshold", type=float, default=0.5, help="Basic Pitch onset 阈值")
    args = ap.parse_args()

    if not Path(args.input).exists():
        print(f"❌ 输入文件不存在: {args.input}")
        return 1

    print(f"[audio_to_midi] {args.input} → {args.output}")
    result = audio_to_midi(args.input, args.output, args.onset_threshold)
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
