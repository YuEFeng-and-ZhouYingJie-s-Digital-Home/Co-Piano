"""
midi_analyzer.py — MIDI 文件深度分析器(Cycle 2 实践)

让用户上传任何 MIDI 文件(自己的练习 / 公开数据集 / 录制转 MIDI),
得到完整的 5 维评估 + 风格分析 + 教学反馈。

Cycle 2 调研结论:用户无 MIDI 键盘也能用这个工具
- MAESTRO 公开数据集(200h 古典钢琴)
- 用户自己录的音 → Basic Pitch 转 MIDI
- 共享的 MIDI 文件

用法:
    python3 midi_analyzer.py /path/to/file.mid
    python3 midi_analyzer.py /path/to/file.mid --reference /path/to/ref.mid  # 对比
    python3 midi_analyzer.py /path/to/file.mid --url                     # 远程下载
    python3 midi_analyzer.py /path/to/file.mid --report report.md        # 写报告

    # 集成 voice_dialog
    from midi_analyzer import patch_voice_dialog_with_midi
    patch_voice_dialog_with_midi()
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from eval_pitch import evaluate
from style_analyzer import analyze_midi as analyze_style_fn
from report import generate_report as gen_md_report


def download_midi(url: str, target: Optional[Path] = None) -> Path:
    """从 URL 下载 MIDI(支持 Google Cloud Storage / S3 直链)"""
    if target is None:
        target = Path("/tmp") / Path(url).name
    print(f"🌐 下载 {url} → {target}")
    req = urllib.request.Request(url, headers={"User-Agent": "CoPiano/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    target.write_bytes(data)
    print(f"   ✅ {len(data)} bytes")
    return target


def analyze_midi(
    midi_path: str | Path,
    reference_path: Optional[str | Path] = None,
    piece_name: str = "Unknown",
    period_hint: str = "",
) -> dict:
    """完整分析一个 MIDI 文件

    Args:
        midi_path: 用户/参考演奏 MIDI
        reference_path: 参考演奏(可选,做对比)
        piece_name: 曲目名
        period_hint: 时期提示(Baroque/Classical/Romantic)

    Returns:
        dict with eval + style + meta
    """
    midi_path = Path(midi_path)
    if not midi_path.exists():
        raise FileNotFoundError(f"MIDI 不存在:{midi_path}")

    result = {
        "meta": {
            "midi_path": str(midi_path),
            "midi_size_bytes": midi_path.stat().st_size,
            "piece": piece_name,
            "period": period_hint,
        },
    }

    # 1. 评估(需要 reference 才能给分,否则只做 solo)
    if reference_path:
        ref = Path(reference_path)
        if not ref.exists():
            raise FileNotFoundError(f"参考 MIDI 不存在:{ref}")
        print(f"🎯 评估:{midi_path.name} vs {ref.name}")
        ev = evaluate(str(ref), str(midi_path))
        ev["piece"] = piece_name
        ev["period"] = period_hint
        result["eval"] = ev
    else:
        print(f"🎵 风格分析(无 reference,只 solo)")
        result["eval"] = None

    # 2. 风格分析
    print(f"🎨 风格分析:{midi_path.name}")
    try:
        style = analyze_style_fn(str(midi_path))
        # 字段简化
        result["style"] = {
            "key": style.get("key", "?"),
            "time_signature": style.get("time_signature", "?"),
            "tempo_bpm": style.get("tempo_bpm", 0),
            "n_notes": style.get("n_notes", 0),
            "duration_s": style.get("duration_s", 0),
            "period_hint": style.get("period_hint", "?"),
            "period_confidence": style.get("period_confidence", 0),
            "style_hints": style.get("style_hints", []),
        }
    except Exception as e:
        result["style"] = {"error": str(e)}

    # 3. 综合评分(只有 reference 时)
    if result["eval"]:
        ev = result["eval"]
        style = result["style"]
        result["meta"]["overall_score"] = ev.get("score", 0)
        result["meta"]["grade"] = (
            "优秀" if ev["score"] >= 95 else
            "良好" if ev["score"] >= 85 else
            "中等" if ev["score"] >= 70 else
            "需加强"
        )
    else:
        result["meta"]["overall_score"] = None
        result["meta"]["grade"] = "未评分(无 reference)"

    return result


def format_report(result: dict) -> str:
    """格式化为可读 Markdown 报告"""
    meta = result["meta"]
    lines = [
        f"# CoPiano MIDI 分析报告",
        f"",
        f"**曲目**: {meta['piece']}",
        f"**时期**: {meta.get('period', '?')}",
        f"**文件**: `{Path(meta['midi_path']).name}` ({meta['midi_size_bytes']} bytes)",
        f"**分析时间**: {result.get('analyzed_at', 'N/A')}",
        f"",
        f"---",
        f"",
    ]

    if result.get("eval"):
        ev = result["eval"]
        lines.extend([
            f"## 1. 评估总览",
            f"",
            f"**总分**: {ev.get('score', 0):.1f} / 100 — {meta.get('grade', '?')}",
            f"",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 错音 | {ev.get('n_pitch_errors', 0)} / {ev.get('n_ref', 0)} |",
            f"| 音准率 | {ev.get('pitch_accuracy', 0)*100:.1f}% |",
            f"| 节奏偏差 | {ev.get('timing_mean_ms', 0):.1f}ms |",
            f"| 节奏波动 | {ev.get('timing_std_ms', 0):.1f}ms |",
            f"| 力度相关 | {ev.get('velocity_correlation', 0):.2f} |",
            f"| 完整度 | {ev.get('note_completeness', 0)*100:.1f}% |",
            f"",
        ])
    else:
        lines.extend([
            f"## 1. 评估",
            f"",
            f"未提供参考 MIDI,无评分。如需评分:`midi_analyzer.py user.mid --reference ref.mid`",
            f"",
        ])

    if result.get("style") and "error" not in result["style"]:
        s = result["style"]
        lines.extend([
            f"## 2. 风格分析",
            f"",
            f"| 维度 | 数值 |",
            f"|------|------|",
            f"| 调性 | {s.get('key', '?')} |",
            f"| 拍号 | {s.get('time_signature', '?')} |",
            f"| 速度 | {s.get('tempo_bpm', 0)} BPM |",
            f"| 音符数 | {s.get('n_notes', 0)} |",
            f"| 时长 | {s.get('duration_s', 0):.1f}s |",
            f"| 时期判断 | **{s.get('period_hint', '?')}** (置信度 {s.get('period_confidence', 0):.2f}) |",
            f"",
            f"**风格提示**:",
            f"",
        ])
        for hint in s.get("style_hints", []):
            lines.append(f"- {hint}")
        lines.append("")

    lines.extend([
        f"---",
        f"",
        f"_本报告由 CoPiano MIDI 分析器自动生成_",
    ])

    return "\n".join(lines)


# ----- 集成 voice_dialog -----
def patch_voice_dialog_with_midi():
    """注入 MIDI 分析到 voice_dialog"""
    import voice_dialog

    def with_midi(messages, backend="mock", **kwargs):
        last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
        if not last_user:
            return voice_dialog.call_llm(messages, backend=backend, **kwargs)

        content = last_user["content"]
        # 触发关键词
        if "分析" in content and (".mid" in content or "MIDI" in content):
            # 提取 MIDI 路径(从用户消息中)
            import re
            match = re.search(r"([\w/.\-]+\.mid)", content)
            if not match:
                return "请告诉我 MIDI 文件的完整路径,例如:分析 /Users/me/sonata.mid"

            midi_path = match.group(1)
            try:
                result = analyze_midi(midi_path)
                report = format_report(result)
                # 短摘要给用户听
                summary = f"分析完成!{result['meta'].get('grade', '未评分')},共 {result['style'].get('n_notes', 0)} 个音符,{result['style'].get('period_hint', '?')} 风格。"
                if result.get("eval"):
                    summary += f" 总分 {result['eval'].get('score', 0):.1f},错音 {result['eval'].get('n_pitch_errors', 0)} 个。"
                # 报告存文件
                report_path = Path("/tmp/copiano_midi_report.md")
                report_path.write_text(report, encoding="utf-8")
                return f"{summary} 完整报告在 {report_path}"
            except FileNotFoundError as e:
                return f"找不到 MIDI 文件:{e}"

        return voice_dialog.call_llm(messages, backend=backend, **kwargs)

    voice_dialog.call_llm = with_midi


# ----- CLI -----
def main():
    parser = argparse.ArgumentParser(description="CoPiano MIDI 文件分析器")
    parser.add_argument("midi", nargs="?", help="MIDI 文件路径")
    parser.add_argument("--reference", help="参考演奏 MIDI(用于评分)")
    parser.add_argument("--url", action="store_true", help="从 URL 下载")
    parser.add_argument("--url-path", help="远程 URL")
    parser.add_argument("--piece", default="Unknown", help="曲目名")
    parser.add_argument("--period", default="", help="时期(Baroque/Classical/Romantic)")
    parser.add_argument("--output", help="JSON 输出路径")
    parser.add_argument("--report", help="Markdown 报告路径")
    args = parser.parse_args()

    if args.url:
        if not args.url_path:
            print("❌ --url 必须配合 --url-path")
            return
        midi_path = download_midi(args.url_path)
    elif args.midi:
        midi_path = Path(args.midi)
    else:
        print("用法: midi_analyzer.py <midi> [--reference ref.mid] [--url --url-path URL]")
        print("示例: midi_analyzer.py /tmp/sonata.mid --reference /tmp/sonata_ref.mid --piece 'K.545' --period Classical")
        return

    # 跑分析
    from datetime import datetime
    result = analyze_midi(
        midi_path,
        reference_path=args.reference,
        piece_name=args.piece,
        period_hint=args.period,
    )
    result["analyzed_at"] = datetime.now().isoformat()

    # 输出 JSON
    if args.output:
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"📊 JSON: {args.output}")

    # 输出 Markdown
    report_md = format_report(result)
    if args.report:
        Path(args.report).write_text(report_md, encoding="utf-8")
        print(f"📝 报告: {args.report}")
    else:
        print()
        print(report_md)


if __name__ == "__main__":
    main()
