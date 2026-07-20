"""
style_analyzer.py — MIDI 风格自动分析(L2 评估增强)

对位论文:
- 2606.20198 Pitch Spelling / Key Estimation(调性检测)
- 2605.06627 PianoCoRe(表演风格)
- 2504.18502 Music Tempo Estimation(速度)
- 2501.10222 Integrated Expressive Piano(表现力综合)

功能(纯 music21,无外部 ML):
1. Key detection(调性 / 大小调)
2. Tempo estimation(速度)
3. Time signature(拍号)
4. Note density(音符密度)
5. Pitch range(音域)
6. Dynamics range(力度范围)
7. Period hint(时期线索:基于调性 + 织体 + 密度启发式)
8. Style hint(风格提示:织体简单/复杂、连奏/断奏)

输出:JSON 风格画像,直接喂给 LLM
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import music21
from music21 import converter, tempo, meter, key, pitch


# === 时期线索启发式 ===
# 基于调性 + 密度 + 平均音域 粗略判断时期
def detect_period_hint(analysis: dict) -> tuple[str, float]:
    """返回 (时期, 置信度 0-1)
    启发式:
    - 巴洛克:密度低,音域窄,调性简单(多大小调),速度稳
    - 古典:密度中,音域宽,织体多声部(alberti bass / 分解和弦)
    - 浪漫:密度高,音域很宽,变化多,和声色彩丰富
    """
    density = analysis.get("note_density_per_sec", 0)
    pitch_range = analysis.get("pitch_range_semitones", 0)
    n_chords_simul = analysis.get("avg_simultaneous_notes", 1)

    # 启发式评分
    baroque = 0
    classical = 0
    romantic = 0

    if density < 4:
        baroque += 0.3
    elif density < 8:
        classical += 0.3
    else:
        romantic += 0.3

    if pitch_range < 25:
        baroque += 0.2
    elif pitch_range < 40:
        classical += 0.2
    else:
        romantic += 0.2

    if n_chords_simul < 1.5:
        baroque += 0.2
    elif n_chords_simul < 3:
        classical += 0.2
    else:
        romantic += 0.2

    scores = {"Baroque": baroque, "Classical": classical, "Romantic": romantic}
    period = max(scores, key=scores.get)
    confidence = scores[period] / 0.7  # 0-1
    return period, min(1.0, confidence)


def analyze_midi(midi_path: str) -> dict:
    """主函数:MIDI 风格分析"""
    score = converter.parse(midi_path)

    # 1. 调性
    try:
        k = score.analyze("key")
        key_name = k.tonic.name + (" " + k.mode if k.mode != "major" else "")
    except Exception:
        key_name = "C major"  # fallback

    # 2. 拍号
    ts_list = score.recurse().getElementsByClass(meter.TimeSignature)
    if ts_list:
        # 提取干净的 "4/4" 形式(去掉 music21 包装)
        time_sig = ts_list[0].ratioString
    else:
        time_sig = "4/4"

    # 3. 速度(取前几个)
    tempos = score.recurse().getElementsByClass(tempo.MetronomeMark)
    bpm = tempos[0].number if tempos else 120

    # 4. 音符统计
    notes = list(score.recurse().notes)
    n_notes = len(notes)
    duration_s = score.highestTime if score.highestTime > 0 else 1
    note_density = n_notes / duration_s

    # 5. 音域
    pitches = [n.pitch.ps for n in notes if hasattr(n, "pitch")]
    if pitches:
        pitch_min = min(pitches)
        pitch_max = max(pitches)
        pitch_range = pitch_max - pitch_min
        pitch_center = (pitch_max + pitch_min) / 2
    else:
        pitch_min = pitch_max = pitch_range = pitch_center = 0

    # 6. 力度
    velocities = [n.volume.velocity for n in notes if hasattr(n, "volume") and n.volume.velocity]
    if velocities:
        vel_min = min(velocities)
        vel_max = max(velocities)
        vel_mean = sum(velocities) / len(velocities)
        vel_std = (sum((v - vel_mean) ** 2 for v in velocities) / len(velocities)) ** 0.5
    else:
        vel_min = vel_max = vel_mean = vel_std = 0

    # 7. 同时发声音数(织体)
    if n_notes > 0:
        # 简化:取所有开始时间的平均同时发声音数
        from collections import Counter
        onset_times = [n.offset for n in notes]
        bins = Counter(int(t * 4) / 4 for t in onset_times)  # 0.25s bin
        max_simul = max(bins.values()) if bins else 1
        avg_simul = sum(bins.values()) / max(1, len(bins))
    else:
        max_simul = avg_simul = 0

    # 8. 时期线索
    analysis = {
        "note_density_per_sec": round(note_density, 2),
        "pitch_range_semitones": round(pitch_range, 1),
        "avg_simultaneous_notes": round(avg_simul, 2),
        "max_simultaneous_notes": max_simul,
    }
    period_hint, period_conf = detect_period_hint(analysis)

    # 9. 风格提示(基于分析)
    style_hints = []
    if note_density < 4:
        style_hints.append("音符稀疏,可能为巴洛克时期或练习曲")
    if note_density > 10:
        style_hints.append("音符密集,可能为浪漫时期或炫技作品")
    if pitch_range > 50:
        style_hints.append("音域宽(>50 半音),多用于浪漫派")
    if pitch_range < 20:
        style_hints.append("音域窄(<20 半音),练习曲或简单旋律")
    if avg_simul > 3:
        style_hints.append("多声部织体,对位或浪漫派风格")
    if avg_simul < 1.2:
        style_hints.append("单声部,旋律清晰,适合教学")
    if vel_std > 20:
        style_hints.append("力度变化大,表现力强")
    if vel_std < 8:
        style_hints.append("力度均匀,机械式弹奏")

    return {
        "midi_path": str(midi_path),
        "duration_s": round(duration_s, 2),
        "n_notes": n_notes,
        "key": key_name,
        "time_signature": time_sig,
        "tempo_bpm": round(bpm, 1),
        "pitch": {
            "min": round(pitch_min, 1),
            "max": round(pitch_max, 1),
            "center": round(pitch_center, 1),
            "range_semitones": round(pitch_range, 1),
        },
        "velocity": {
            "min": vel_min,
            "max": vel_max,
            "mean": round(vel_mean, 1),
            "std": round(vel_std, 1),
        },
        "texture": {
            "note_density_per_sec": round(note_density, 2),
            "avg_simultaneous_notes": round(avg_simul, 2),
            "max_simultaneous_notes": max_simul,
        },
        "period_hint": period_hint,
        "period_confidence": round(period_conf, 2),
        "style_hints": style_hints,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: style_analyzer.py <midi_path>", file=sys.stderr)
        return 1
    result = analyze_midi(sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
