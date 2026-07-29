"""
expressiveness_analyzer.py — 钢琴表现力多维分析器(Cycle 3 实践)

对位研究:
- Werner Goebl 2001 melody lead 30ms
- Repp 1996 velocity difference 解释 melody lead
- KTH Rule System 6 大规则
- 行业空白:多声部<70% 识别, 表现力评估弱

9 维度分析(全 MIDI 可算):
1. velocity_mean           整体力度
2. velocity_std            力度变化
3. dynamic_range           pp→ff 跨度
4. ltv (Local Tempo Var)   rubato
5. voicing_balance         旋律 vs 伴奏力度差
6. melody_lead_ms          旋律提前 ms
7. touch_speed             onset→peak 推算触键速度
8. articulation            staccato/legato 比例
9. release_var             释放变化

输出:0-100 综合分 + 风格匹配建议(巴洛克/古典/浪漫)+ voice_dialog 集成

用法:
    python3 expressiveness_analyzer.py /path/to/file.mid
    python3 expressiveness_analyzer.py /path/to/file.mid --period baroque
    python3 expressiveness_analyzer.py /path/to/file.mid --report /tmp/report.md

    from expressiveness_analyzer import patch_voice_dialog_with_expressiveness
    patch_voice_dialog_with_expressiveness()
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


# ----- 数据结构 -----
@dataclass
class ExpressivenessProfile:
    """9 维表现力评分"""
    velocity_mean: float = 0.0      # 平均 velocity (0-127)
    velocity_std: float = 0.0       # 力度标准差
    dynamic_range: float = 0.0      # 力度范围 (max-min)
    ltv: float = 0.0                # 局部速度变化系数 (%)
    voicing_balance: float = 0.0    # 旋律 vs 伴奏力度比 (%)
    melody_lead_ms: float = 0.0     # 旋律提前毫秒
    touch_speed: float = 0.0        # 触键速度(0-10)
    articulation: float = 0.0       # articulation 评分 (0-10)
    release_var: float = 0.0        # 释放变化 (0-10)
    overall: float = 0.0            # 综合分 (0-100)
    n_notes: int = 0
    n_simultaneous_max: int = 0
    detected_articulation: str = "?"  # staccato/legato/mixed


# ----- MIDI 解析辅助 -----
def _load_midi_notes(midi_path: str | Path) -> list[dict]:
    """加载 MIDI 为统一格式: list of {pitch, onset, offset, velocity}"""
    import mido
    mid = mido.MidiFile(str(midi_path))
    notes = []
    # 合并所有 track
    for track in mid.tracks:
        t = 0
        active = {}  # pitch -> (onset_tick, velocity)
        for msg in track:
            t += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                active[msg.note] = (t, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                if msg.note in active:
                    onset_tick, vel = active.pop(msg.note)
                    notes.append({
                        "pitch": msg.note,
                        "onset_tick": onset_tick,
                        "offset_tick": t,
                        "velocity": vel,
                    })
    # 转 seconds
    ticks_per_beat = mid.ticks_per_beat
    tempo = 500000  # default 120 BPM
    # 找 tempo
    for track in mid.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                tempo = msg.tempo
                break
    for n in notes:
        n["onset_s"] = mido.tick2second(n["onset_tick"], ticks_per_beat, tempo)
        n["offset_s"] = mido.tick2second(n["offset_tick"], ticks_per_beat, tempo)
        n["duration_s"] = n["offset_s"] - n["onset_s"]
    notes.sort(key=lambda x: x["onset_s"])
    return notes


def _detect_simultaneous_groups(notes: list[dict], tolerance: float = 0.05) -> list[list[dict]]:
    """检测同时发声的和弦(onset 在 tolerance 内)"""
    if not notes:
        return []
    groups = []
    current = [notes[0]]
    for n in notes[1:]:
        if abs(n["onset_s"] - current[0]["onset_s"]) < tolerance:
            current.append(n)
        else:
            groups.append(current)
            current = [n]
    groups.append(current)
    return groups


# ----- 9 维分析 -----
def analyze_expressiveness(midi_path: str | Path, period_hint: str = "") -> ExpressivenessProfile:
    """主分析函数:9 维表现力"""
    notes = _load_midi_notes(midi_path)
    if not notes:
        return ExpressivenessProfile(detected_articulation="no_notes")

    profile = ExpressivenessProfile()
    profile.n_notes = len(notes)
    velocities = [n["velocity"] for n in notes]

    # 1. velocity_mean
    profile.velocity_mean = round(sum(velocities) / len(velocities), 1)

    # 2. velocity_std
    mean_v = profile.velocity_mean
    profile.velocity_std = round(
        (sum((v - mean_v) ** 2 for v in velocities) / len(velocities)) ** 0.5, 2
    )

    # 3. dynamic_range
    profile.dynamic_range = max(velocities) - min(velocities)

    # 4. LTV (Local Tempo Variation) = IOI 标准差 / 平均
    ioi = [notes[i+1]["onset_s"] - notes[i]["onset_s"] for i in range(len(notes) - 1)
           if notes[i+1]["onset_s"] > notes[i]["onset_s"]]
    if ioi:
        mean_ioi = sum(ioi) / len(ioi)
        if mean_ioi > 0:
            std_ioi = (sum((x - mean_ioi) ** 2 for x in ioi) / len(ioi)) ** 0.5
            profile.ltv = round(std_ioi / mean_ioi * 100, 2)

    # 5-6. Voicing & melody lead
    # 把同时发声的 notes 视为同一和弦
    groups = _detect_simultaneous_groups(notes, tolerance=0.05)
    profile.n_simultaneous_max = max(len(g) for g in groups) if groups else 0

    melody_leads = []
    vel_diffs = []
    if profile.n_simultaneous_max >= 2:
        # 对每个和弦:最高音视为旋律,其他视为伴奏
        for g in groups:
            if len(g) >= 2:
                g_sorted = sorted(g, key=lambda n: n["pitch"])
                melody = g_sorted[-1]  # 最高音
                accomps = g_sorted[:-1]
                # melody lead
                if accomps:
                    lead_s = melody["onset_s"] - min(a["onset_s"] for a in accomps)
                    melody_leads.append(lead_s * 1000)  # ms
                # velocity diff
                if accomps:
                    vel_diff = melody["velocity"] - sum(a["velocity"] for a in accomps) / len(accomps)
                    vel_diffs.append(vel_diff)
        if melody_leads:
            profile.melody_lead_ms = round(sum(melody_leads) / len(melody_leads), 2)
        if vel_diffs:
            avg_diff = sum(vel_diffs) / len(vel_diffs)
            mean_melody_v = sum(velocities) / len(velocities) if velocities else 1
            if mean_melody_v > 0:
                profile.voicing_balance = round(avg_diff / mean_melody_v * 100, 2)

    # 7. touch_speed (用 IOI 推算,0-10 score)
    # 越短 IOI = 越快 = 速度大
    if ioi:
        mean_ioi = sum(ioi) / len(ioi)
        # 假设 0.5s 为中等速度, 0.1s 为快
        if mean_ioi > 0:
            speed_score = max(0, min(10, 10 - (mean_ioi - 0.3) * 10))
            profile.touch_speed = round(speed_score, 2)

    # 8. articulation (staccato/legato based on note gaps)
    # gap < 0.05s = legato, gap > 0.2s = staccato
    staccato_count = sum(1 for g in ioi if g > 0.2)
    legato_count = sum(1 for g in ioi if g < 0.05)
    if ioi:
        total = len(ioi)
        staccato_ratio = staccato_count / total
        legato_ratio = legato_count / total
        # articulation 评分:多样 > 单一
        if staccato_ratio > 0.5:
            profile.detected_articulation = "staccato"
            profile.articulation = 7  # staccato 有控制
        elif legato_ratio > 0.5:
            profile.detected_articulation = "legato"
            profile.articulation = 7
        else:
            profile.detected_articulation = "mixed"
            profile.articulation = 9  # 多样更好
    # 修正:打分还要看 variation
    if ioi and len(ioi) > 4:
        cv_ioi = (sum((x - sum(ioi)/len(ioi))**2 for x in ioi) / len(ioi)) ** 0.5 / (sum(ioi)/len(ioi))
        profile.articulation = round(min(10, 5 + cv_ioi * 30), 2)

    # 9. release_var (note duration 变化)
    durations = [n["duration_s"] for n in notes if n["duration_s"] > 0]
    if durations:
        mean_dur = sum(durations) / len(durations)
        if mean_dur > 0:
            std_dur = (sum((d - mean_dur) ** 2 for d in durations) / len(durations)) ** 0.5
            cv_dur = std_dur / mean_dur
            profile.release_var = round(min(10, cv_dur * 30), 2)

    # 综合分:加权平均
    profile.overall = _compute_overall(profile, period_hint)

    return profile


def _compute_overall(profile: ExpressivenessProfile, period_hint: str = "") -> float:
    """计算 0-100 综合分,按时期给不同权重"""
    # 默认权重
    weights = {
        "dynamic_range": 1.0,
        "velocity_std": 1.0,
        "ltv": 0.8,
        "voicing_balance": 1.2,
        "melody_lead": 0.8,
        "touch_speed": 0.6,
        "articulation": 1.0,
        "release_var": 0.6,
    }

    # 时期调整
    period_lower = period_hint.lower()
    if "baroque" in period_lower or "classical" in period_lower:
        # 巴洛克/古典:rubato 受限, 强规律
        weights["ltv"] = 0.3
        weights["dynamic_range"] = 0.8
        weights["voicing_balance"] = 1.5  # 对位清晰
        weights["melody_lead"] = 1.0
    elif "romantic" in period_lower:
        # 浪漫:rubato 自由, 强对比
        weights["ltv"] = 1.5
        weights["dynamic_range"] = 1.5
        weights["voicing_balance"] = 1.0
        weights["melody_lead"] = 0.6

    # 各项归一化到 0-10
    norm = {
        "dynamic_range": min(10, profile.dynamic_range / 12.7),  # 0-127 -> 0-10
        "velocity_std": min(10, profile.velocity_std),
        "ltv": _norm_ltv(profile.ltv, period_lower),
        "voicing_balance": min(10, abs(profile.voicing_balance) / 3),  # 30% diff = 满分
        "melody_lead": _norm_melody_lead(profile.melody_lead_ms),
        "touch_speed": profile.touch_speed,
        "articulation": profile.articulation,
        "release_var": profile.release_var,
    }

    total = sum(norm[k] * weights[k] for k in weights)
    max_total = sum(10 * weights[k] for k in weights)
    return round(total / max_total * 100, 1)


def _norm_ltv(ltv: float, period: str) -> float:
    """LTV 归一化:不同时期有不同理想范围"""
    if "baroque" in period or "classical" in period:
        # 古典:理想 < 5%
        if ltv < 5: return 10
        if ltv < 10: return 7
        if ltv < 20: return 4
        return 2
    elif "romantic" in period:
        # 浪漫:理想 10-20%
        if 8 <= ltv <= 20: return 10
        if 5 <= ltv <= 25: return 7
        return 4
    else:
        # 默认
        return min(10, ltv * 0.5)


def _norm_melody_lead(ms: float) -> float:
    """melody lead 归一化:30ms = 满分(Goebl 经典值)"""
    abs_ms = abs(ms)
    if abs_ms < 5: return 3  # 不够明显
    if 20 <= abs_ms <= 40: return 10  # 理想范围
    if 10 <= abs_ms <= 50: return 7
    return 4


# ----- 报告生成 -----
def format_report(profile: ExpressivenessProfile, period: str = "") -> str:
    md = [
        "# 表现力分析报告",
        "",
        f"**音符数**: {profile.n_notes}  |  **最大同时发声音**: {profile.n_simultaneous_max}  |  **Articulation**: {profile.detected_articulation}",
        f"**时期**: {period or '未指定'}",
        "",
        "---",
        "",
        f"## 综合评分: **{profile.overall} / 100**",
        "",
        "## 9 维度细分",
        "",
        "| # | 维度 | 原始值 | 评分(0-10) | 说明 |",
        "|---|------|--------|------------|------|",
        f"| 1 | velocity_mean | {profile.velocity_mean} | — | 平均力度 |",
        f"| 2 | velocity_std | {profile.velocity_std} | {min(10, profile.velocity_std):.1f} | 力度变化(越高 = 越有表现) |",
        f"| 3 | dynamic_range | {profile.dynamic_range} | {min(10, profile.dynamic_range/12.7):.1f} | pp→ff 跨度(127=全幅) |",
        f"| 4 | LTV (rubato) | {profile.ltv}% | (按时期间归一化) | 速度变化系数 |",
        f"| 5 | voicing_balance | {profile.voicing_balance}% | {min(10, abs(profile.voicing_balance)/3):.1f} | 旋律 vs 伴奏力度差 |",
        f"| 6 | melody_lead | {profile.melody_lead_ms}ms | {_norm_melody_lead(profile.melody_lead_ms):.1f} | 旋律提前(Goebl 经典 30ms) |",
        f"| 7 | touch_speed | — | {profile.touch_speed:.1f} | 推算触键速度 |",
        f"| 8 | articulation | {profile.detected_articulation} | {profile.articulation:.1f} | 连断奏比例 |",
        f"| 9 | release_var | — | {profile.release_var:.1f} | 释放变化 |",
        "",
        "## 教学建议",
        "",
    ]
    md.extend(_generate_teaching_tips(profile, period))
    md.extend([
        "",
        "---",
        "",
        "_基于 Goebl 2001 / Repp 1996 / KTH Rule System 等研究_",
    ])
    return "\n".join(md)


def _generate_teaching_tips(profile: ExpressivenessProfile, period: str) -> list[str]:
    """根据 9 维度给具体教学建议"""
    tips = []
    period_lower = period.lower()

    if profile.melody_lead_ms < 10 and profile.n_simultaneous_max >= 2:
        tips.append("- **声部平衡**:旋律 vs 伴奏差异不明显(提前 < 10ms),建议加强主旋律提前 20-30ms 突出主题")
    elif 20 <= profile.melody_lead_ms <= 40:
        tips.append(f"- ✅ **声部平衡**优秀(旋律提前 {profile.melody_lead_ms}ms,Goebl 经典值 30ms)")

    if profile.voicing_balance < 10 and profile.n_simultaneous_max >= 2:
        tips.append(f"- **力度对比**:主旋律力度仅比伴奏大 {profile.voicing_balance}%,建议提升到 25-30%")

    if profile.dynamic_range < 30:
        tips.append(f"- **动态范围**:仅 {profile.dynamic_range}(满分 127),整体力度单一,加入 pp / ff 强对比")
    elif profile.dynamic_range > 60:
        tips.append(f"- ✅ **动态范围**优秀({profile.dynamic_range}),戏剧性对比到位")

    if "baroque" in period_lower or "classical" in period_lower:
        if profile.ltv > 10:
            tips.append(f"- **风格匹配**:时期是{period or '古典'},但 LTV={profile.ltv}% 偏自由,建议收紧 rubato")
    elif "romantic" in period_lower:
        if profile.ltv < 5:
            tips.append(f"- **风格匹配**:时期是{period or '浪漫'},但 LTV={profile.ltv}% 偏机械,加入更多 rubato")
        elif 8 <= profile.ltv <= 20:
            tips.append(f"- ✅ **rubato** 符合浪漫派风格(LTV={profile.ltv}%)")

    if profile.articulation == 7 and profile.detected_articulation in ("staccato", "legato"):
        tips.append(f"- **Articulation**:整体偏{profile.detected_articulation},加入对比会更丰富")

    if not tips:
        tips.append("- 各项指标均在合理范围,继续保持")

    return tips


# ----- 集成 voice_dialog -----
def patch_voice_dialog_with_expressiveness():
    """注入表现力分析到 voice_dialog"""
    import voice_dialog
    _original = voice_dialog.call_llm

    def with_expressiveness(messages, backend="mock", **kwargs):
        last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
        if not last_user:
            return _original(messages, backend=backend, **kwargs)
        content = last_user["content"]
        # 触发关键词
        if ("表现力" in content or "演奏" in content and "分析" in content) and (".mid" in content or "MIDI" in content):
            import re
            match = re.search(r"([\w/.\-]+\.mid)", content)
            if not match:
                return "请告诉我 MIDI 路径,例如:分析 /Users/me/sonata.mid 的表现力"
            midi_path = match.group(1)
            period_m = re.search(r"(Baroque|Classical|Romantic|巴洛克|古典|浪漫)", content)
            period = period_m.group(0) if period_m else ""
            try:
                profile = analyze_expressiveness(midi_path, period_hint=period)
                # 短摘要
                summary = (
                    f"表现力分析完成!综合分 {profile.overall}/100,"
                    f"旋律提前 {profile.melody_lead_ms}ms(Goebl 经典 30ms),"
                    f"动态范围 {profile.dynamic_range}/127,"
                    f"rubato {profile.ltv}%,"
                    f"声部平衡 {profile.voicing_balance}%。"
                )
                # 报告存文件
                report_path = Path("/tmp/copiano_expressiveness_report.md")
                report_path.write_text(format_report(profile, period), encoding="utf-8")
                return f"{summary} 完整 9 维报告在 {report_path}"
            except FileNotFoundError as e:
                return f"找不到 MIDI 文件:{e}"
        return _original(messages, backend=backend, **kwargs)

    voice_dialog.call_llm = with_expressiveness


# ----- CLI -----
def main():
    parser = argparse.ArgumentParser(description="CoPiano 表现力多维分析器")
    parser.add_argument("midi", help="MIDI 文件路径")
    parser.add_argument("--period", default="", help="时期(Baroque/Classical/Romantic)")
    parser.add_argument("--output", help="JSON 输出路径")
    parser.add_argument("--report", help="Markdown 报告路径")
    args = parser.parse_args()

    if not Path(args.midi).exists():
        print(f"❌ MIDI 不存在:{args.midi}")
        return

    profile = analyze_expressiveness(args.midi, period_hint=args.period)

    if args.output:
        Path(args.output).write_text(
            json.dumps(asdict(profile), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"📊 JSON: {args.output}")

    report = format_report(profile, args.period)
    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
        print(f"📝 报告: {args.report}")
    else:
        print()
        print(report)


if __name__ == "__main__":
    main()
