"""
align_score.py — 乐谱-演奏对齐(对位 2605.20014 Precise Audio-to-Score Alignment 思路)

实现要点:
- 输入:乐谱(MIDI,节拍精确) + 演奏(MIDI,时间略漂移)
- 算法:
  1. 把乐谱和演奏都转成 chroma 特征(12 维向量,每 50ms 一帧)
  2. 用 DTW 在 chroma 序列上找最优路径
  3. 输出:每个乐谱小节对应的演奏时间戳(用于后续评估和反馈)
- 输出:JSON / 可视化

简化版(够用,精度比论文 2605.20014 略低但能跑):
- 不做 HMM/Normalized DTW
- 用 librosa 的 DTW(标准实现)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import mido
import librosa


def midi_to_chroma(midi_path: str, hop_ms: int = 50) -> tuple[np.ndarray, np.ndarray]:
    """把 MIDI 转成 chroma 特征矩阵
    返回: (chroma[T,12], times[T])
    """
    mid = mido.MidiFile(midi_path)
    duration = mid.length
    hop = hop_ms / 1000.0
    n_frames = int(np.ceil(duration / hop)) + 1
    chroma = np.zeros((n_frames, 12), dtype=np.float32)

    t = 0.0
    active: dict[tuple[int, int], tuple[float, int]] = {}
    tempo = 500000
    for track in mid.tracks:
        t = 0.0
        for msg in track:
            t += mido.tick2second(msg.time, mid.ticks_per_grand_stroke if hasattr(mid,'ticks_per_grand_stroke') else mid.ticks_per_beat, tempo)
            if msg.type == "set_tempo":
                tempo = msg.tempo
            if msg.type == "note_on" and msg.velocity > 0:
                active[(msg.channel, msg.note)] = (t, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active:
                    onset, vel = active[key]
                    pitch_class = msg.note % 12
                    start_frame = int(onset / hop)
                    end_frame = int(t / hop)
                    for f in range(start_frame, min(end_frame, n_frames)):
                        chroma[f, pitch_class] = max(chroma[f, pitch_class], vel / 127.0)
                    del active[key]
    times = np.arange(n_frames) * hop
    # 归一化
    norm = chroma.sum(axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    chroma = chroma / norm
    return chroma, times


def align_score_performance(score_midi: str, perf_midi: str) -> dict:
    """主函数:乐谱-演奏对齐"""
    s_chroma, s_times = midi_to_chroma(score_midi)
    p_chroma, p_times = midi_to_chroma(perf_midi)

    # librosa DTW
    # subsequence DTW: 演奏匹配乐谱的一部分(允许演奏有前奏/余韵)
    # 用 chroma 12 维 + euclidean 距离
    D, wp = librosa.sequence.dtw(
        X=s_chroma.T,  # [12, T_score]
        Y=p_chroma.T,  # [12, T_perf]
        subseq=True,   # 子序列匹配
        metric="euclidean",
    )

    # 提取对齐路径:score_frame -> perf_time
    score_to_perf_time = {}
    perf_segments = []  # (score_start, score_end, perf_start, perf_end)
    if len(wp) > 0:
        wp = wp[::-1]  # DTW 返回 [T_perf, 2], 反转成时间顺序
        for score_idx, perf_idx in wp:
            if score_idx not in score_to_perf_time:
                score_to_perf_time[int(score_idx)] = float(p_times[int(perf_idx)])

    # 把对齐结果转成可读形式(每 5 个 score 帧报一个点)
    alignment_points = []
    for s_idx in sorted(score_to_perf_time.keys())[::5]:
        alignment_points.append({
            "score_time_s": round(float(s_times[s_idx]), 3),
            "perf_time_s": round(score_to_perf_time[s_idx], 3),
        })

    return {
        "score_duration_s": round(float(s_times[-1]), 2),
        "perf_duration_s": round(float(p_times[-1]), 2),
        "n_alignment_points": len(alignment_points),
        "alignment_quality": round(float(D[-1, -1]) / max(1, len(wp)), 4),
        "first_5_alignment": alignment_points[:5],
        "last_5_alignment": alignment_points[-5:],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("score_midi")
    ap.add_argument("perf_midi")
    args = ap.parse_args()
    result = align_score_performance(args.score_midi, args.perf_midi)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
