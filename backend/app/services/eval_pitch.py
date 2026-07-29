"""
eval_pitch.py — 错音 / 节奏 / 力度 三维评估(MIDI 对齐版)

输入:
    - reference_midi: 参考演奏(教师/标准)
    - user_midi: 用户演奏
    - alignment: 对齐方式(可选,默认 DTW)

输出:
    - JSON: 错音率 / 节奏偏差 / 力度相关性 / 详细对齐
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

import mido
import numpy as np


@dataclass
class Note:
    pitch: int
    onset: float  # seconds
    offset: float
    velocity: int


def midi_to_notes(midi_path: str) -> list[Note]:
    """把 MIDI 文件转成 Note 列表(单乐器,合并同音连击)"""
    mid = mido.MidiFile(midi_path)
    notes: list[Note] = []
    t = 0.0
    active: dict[tuple[int, int], float] = {}  # (channel,pitch) -> onset time
    tempo = 500000  # default 120 BPM
    for track in mid.tracks:
        t = 0.0
        for msg in track:
            t += mido.tick2second(msg.time, mid.ticks_per_grand_stroke if hasattr(mid,'ticks_per_grand_stroke') else mid.ticks_per_beat, tempo)
            if msg.type == "set_tempo":
                tempo = msg.tempo
            if msg.type == "note_on" and msg.velocity > 0:
                active[(msg.channel, msg.note)] = t
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active:
                    notes.append(Note(pitch=msg.note, onset=active[key], offset=t, velocity=64))
                    del active[key]
    notes.sort(key=lambda n: (n.onset, n.pitch))
    return notes


def align_dtw(ref_pitches: list[int], user_pitches: list[int]) -> list[tuple[int, int]]:
    """极简 DTW 对齐(只对齐 pitch 序列)"""
    n, m = len(ref_pitches), len(user_pitches)
    if n == 0 or m == 0:
        return []
    dp = np.full((n + 1, m + 1), np.inf)
    dp[0, 0] = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref_pitches[i-1] == user_pitches[j-1] else 1
            dp[i, j] = cost + min(dp[i-1, j-1], dp[i-1, j], dp[i, j-1])
    # 回溯
    pairs = []
    i, j = n, m
    while i > 0 and j > 0:
        if dp[i, j] == dp[i-1, j-1] + (0 if ref_pitches[i-1] == user_pitches[j-1] else 1):
            pairs.append((i-1, j-1))
            i -= 1; j -= 1
        elif dp[i, j] == dp[i-1, j] + 1:
            pairs.append((i-1, -1))  # 漏音
            i -= 1
        else:
            pairs.append((-1, j-1))  # 多音
            j -= 1
    pairs.reverse()
    return pairs


def evaluate(ref_midi: str, user_midi: str) -> dict:
    ref_notes = midi_to_notes(ref_midi)
    user_notes = midi_to_notes(user_midi)
    ref_pitches = [n.pitch for n in ref_notes]
    user_pitches = [n.pitch for n in user_notes]
    pairs = align_dtw(ref_pitches, user_pitches)
    if not pairs:
        return {"error": "empty alignment"}

    # 1) 错音率
    matched = 0
    correct = 0
    pitch_errors = []
    for i, j in pairs:
        if i == -1:
            pitch_errors.append({"type": "extra", "user_pitch": user_notes[j].pitch})
            continue
        if j == -1:
            pitch_errors.append({"type": "missing", "ref_pitch": ref_notes[i].pitch})
            continue
        matched += 1
        if ref_notes[i].pitch == user_notes[j].pitch:
            correct += 1
        else:
            pitch_errors.append({
                "type": "wrong",
                "ref_pitch": ref_notes[i].pitch,
                "user_pitch": user_notes[j].pitch,
                "ref_note": ref_notes[i].pitch % 12,
                "user_note": user_notes[j].pitch % 12,
            })
    pitch_accuracy = correct / max(1, matched)
    note_completeness = matched / max(1, len(ref_pitches))

    # 2) 节奏偏差(对每个匹配对,看 onset 差)
    timing_errors = []
    for i, j in pairs:
        if i >= 0 and j >= 0:
            dt = user_notes[j].onset - ref_notes[i].onset
            timing_errors.append(dt)
    timing_errors = np.array(timing_errors) if timing_errors else np.array([0.0])
    timing_mean_ms = float(np.mean(timing_errors) * 1000)
    timing_std_ms = float(np.std(timing_errors) * 1000)

    # 3) 力度相关性(只用匹配对的 velocity)
    vel_pairs = [(ref_notes[i].velocity, user_notes[j].velocity) for i, j in pairs if i >= 0 and j >= 0]
    if vel_pairs:
        ref_v = np.array([p[0] for p in vel_pairs], dtype=float)
        user_v = np.array([p[1] for p in vel_pairs], dtype=float)
        if np.std(ref_v) > 0 and np.std(user_v) > 0:
            velocity_corr = float(np.corrcoef(ref_v, user_v)[0, 1])
        else:
            velocity_corr = 0.0
    else:
        velocity_corr = 0.0

    # 4) 综合分数(0-100)
    score = (
        50 * pitch_accuracy
        + 30 * note_completeness
        + 20 * max(0, 1 - abs(timing_mean_ms) / 500)  # 0.5s 偏差 = 0 分
    )
    score = max(0, min(100, score))

    return {
        "score": round(score, 2),
        "pitch_accuracy": round(pitch_accuracy, 3),
        "note_completeness": round(note_completeness, 3),
        "timing_mean_ms": round(timing_mean_ms, 1),
        "timing_std_ms": round(timing_std_ms, 1),
        "velocity_correlation": round(velocity_corr, 3),
        "n_ref": len(ref_notes),
        "n_user": len(user_notes),
        "n_matched": matched,
        "n_pitch_errors": len([e for e in pitch_errors if e["type"] in ("wrong", "missing")]),
        "pitch_error_samples": pitch_errors[:5],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref_midi")
    ap.add_argument("user_midi")
    args = ap.parse_args()
    result = evaluate(args.ref_midi, args.user_midi)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
