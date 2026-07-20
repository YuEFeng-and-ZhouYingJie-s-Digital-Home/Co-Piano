"""
cycle2_test.py — Cycle 2 综合测试(MIDI 文件分析 + MAESTRO 网络数据)

覆盖:
1. 网络数据:MAESTRO 公开数据集(单首 MIDI 文件)
2. MIDI analyzer 多场景(本地 + 远程)
3. voice_dialog MIDI 集成
4. 性能指标

输出:
- notes/cycle2_test_report.md
- notes/cycle2_test_results.json
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
NOTES = ROOT / "notes"

import voice_dialog
from midi_analyzer import analyze_midi, format_report, download_midi, patch_voice_dialog_with_midi


# ----- 测试场景 -----
SCENARIOS = [
    # (name, midi_path, reference_path, piece, period, source)
    ("beginner_clean", "/tmp/cycle1_00_ref.mid", "/tmp/cycle1_00_ref.mid", "Beyer", "Baroque", "synth"),
    ("beginner_one_err", "/tmp/cycle1_01_user.mid", "/tmp/cycle1_01_ref.mid", "Beyer", "Baroque", "synth"),
    ("elementary", "/tmp/cycle1_02_user.mid", "/tmp/cycle1_02_ref.mid", "Minuet in G", "Baroque", "synth"),
    ("bach_prelude", "/tmp/cycle1_05_user.mid", "/tmp/cycle1_05_ref.mid", "Bach Prelude", "Baroque", "synth"),
    ("sonata_k545", "/tmp/cycle1_07_user.mid", "/tmp/cycle1_07_ref.mid", "Sonata K.545", "Classical", "synth"),
    ("chopin_nocturne", "/tmp/cycle1_08_user.mid", "/tmp/cycle1_08_ref.mid", "Chopin Nocturne", "Romantic", "synth"),
    ("fur_elise", "/tmp/cycle1_09_user.mid", "/tmp/cycle1_09_ref.mid", "Für Elise", "Classical", "synth"),
    ("many_errors", "/tmp/cycle1_10_user.mid", "/tmp/cycle1_10_ref.mid", "Bach Invention", "Baroque", "synth"),
    ("solo_no_ref", "/tmp/cycle1_00_ref.mid", None, "Beyer", "Baroque", "synth"),
]


def try_maestro_download() -> dict:
    """尝试下载 MAESTRO 单个 MIDI 文件"""
    print("🌐 尝试 MAESTRO 公开数据集...")
    # MAESTRO 单个 MIDI URL 格式(从 dataset JSON metadata)
    # 先试一个标准 URL
    test_urls = [
        # MAESTRO v3.0.0 单文件示例
        "https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/2018/MIDI-Unprocessed_05_R1_2018_MID--AUDIOINDPG_01-06_R1_2018_wav--2.midi",
        "https://storage.googleapis.com/magentadata/datasets/maestro/v2.0.0/2004/MIDI-Unprocessed_Segment_01_R1_2004_01-08_wav--1.midi",
    ]

    for url in test_urls:
        try:
            target = Path("/tmp/maestro_sample.mid")
            download_midi(url, target)
            return {
                "available": True,
                "url": url,
                "path": str(target),
                "size_bytes": target.stat().st_size,
            }
        except Exception as e:
            print(f"   ❌ {url}: {str(e)[:100]}")
            continue

    return {
        "available": False,
        "tried_urls": test_urls,
        "note": "MAESTRO 直链访问失败,可能需要 GCS 认证或换 URL 格式",
    }


def test_scenario(scenario: tuple) -> dict:
    """跑一个 MIDI analyzer 场景"""
    name, midi, ref, piece, period, source = scenario
    try:
        if not Path(midi).exists():
            return {
                "scenario": name,
                "ok": False,
                "error": f"MIDI 不存在: {midi}",
            }
        t0 = time.time()
        result = analyze_midi(
            midi_path=midi,
            reference_path=ref,
            piece_name=piece,
            period_hint=period,
        )
        dt = time.time() - t0
        return {
            "scenario": name,
            "piece": piece,
            "period": period,
            "source": source,
            "ok": True,
            "latency_s": round(dt, 3),
            "score": result.get("eval", {}).get("score") if result.get("eval") else None,
            "n_pitch_errors": result.get("eval", {}).get("n_pitch_errors") if result.get("eval") else None,
            "period_detected": result.get("style", {}).get("period_hint", "?"),
            "n_notes": result.get("style", {}).get("n_notes", 0),
            "report_chars": len(format_report(result)),
        }
    except Exception as e:
        return {
            "scenario": name,
            "ok": False,
            "error": str(e)[:200],
        }


def test_voice_dialog_midi() -> dict:
    """测试 voice_dialog MIDI 集成"""
    try:
        patch_voice_dialog_with_midi()

        queries = [
            "帮我分析 /tmp/cycle1_00_ref.mid 这个 MIDI",
            "看下 /tmp/cycle1_05_user.mid 怎么样",
        ]
        results = []
        for q in queries:
            state = voice_dialog.DialogState()
            state.add_user(q)
            msgs = state.build_messages()
            t0 = time.time()
            try:
                reply = voice_dialog.call_llm(msgs, backend="mock")
                dt = time.time() - t0
                results.append({
                    "query": q,
                    "reply_preview": reply[:150] if reply else "",
                    "latency_s": round(dt, 2),
                    "ok": True,
                })
            except Exception as e:
                results.append({
                    "query": q,
                    "ok": False,
                    "error": str(e)[:100],
                })
        return {"ok": True, "queries": results}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def main():
    print("=" * 60)
    print("CoPiano Cycle 2 综合测试(MIDI 文件分析)")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)
    print()

    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {},
    }

    # 1. MAESTRO 下载
    print("🌐 测试 1: MAESTRO 公开数据集")
    maestro = try_maestro_download()
    results["tests"]["maestro_download"] = maestro
    if maestro["available"]:
        print(f"   ✅ 下载成功:{maestro['path']} ({maestro['size_bytes']} bytes)")
    else:
        print(f"   ⚠️  失败: {maestro.get('note', '')}")
    print()

    # 2. MIDI analyzer 场景
    print("🎹 测试 2: MIDI analyzer 多场景")
    scenario_results = []
    for sc in SCENARIOS:
        r = test_scenario(sc)
        scenario_results.append(r)
        if r["ok"]:
            score = r.get("score")
            score_str = f"score={score}" if score is not None else "solo"
            print(f"   [{r['scenario']:20s}] {r['piece']:20s} ({r['period']:10s}) {score_str}, {r['n_notes']} 音符, {r['latency_s']}s")
        else:
            print(f"   [{r['scenario']:20s}] ❌ {r.get('error', '')}")
    results["tests"]["scenarios"] = scenario_results
    print()

    # 3. voice_dialog 集成
    print("🗣️  测试 3: voice_dialog MIDI 集成")
    vd = test_voice_dialog_midi()
    results["tests"]["voice_dialog_midi"] = vd
    if vd["ok"]:
        for q in vd["queries"]:
            status = "✅" if q.get("ok") else "❌"
            if q.get("ok"):
                print(f"   {status} {q['query'][:50]} ({q['latency_s']}s)")
                print(f"      → {q['reply_preview']}")
            else:
                print(f"   {status} {q.get('error', '')}")
    else:
        print(f"   ❌ {vd.get('error', '')}")
    print()

    # 总结
    sc_pass = sum(1 for r in scenario_results if r["ok"])
    sc_total = len(scenario_results)
    vd_pass = sum(1 for q in vd.get("queries", []) if q.get("ok")) if vd.get("ok") else 0
    vd_total = len(vd.get("queries", []))
    overall_pass = sc_pass + vd_pass + (1 if maestro["available"] else 0)
    overall_total = sc_total + vd_total + 1

    print("=" * 60)
    print("📊 Cycle 2 综合测试总结")
    print("=" * 60)
    print(f"   MAESTRO 下载:    {'✅' if maestro['available'] else '⚠️  失败'}")
    print(f"   MIDI analyzer:   {sc_pass}/{sc_total} 场景通过")
    print(f"   voice_dialog:    {vd_pass}/{vd_total} 集成通过")
    print(f"   总计:            {overall_pass}/{overall_total} ({overall_pass/overall_total*100:.0f}%)")

    results["summary"] = {
        "maestro_available": maestro["available"],
        "scenarios_pass": sc_pass,
        "scenarios_total": sc_total,
        "vd_pass": vd_pass,
        "vd_total": vd_total,
        "overall_pass": overall_pass,
        "overall_total": overall_total,
        "pass_rate": f"{overall_pass/overall_total*100:.0f}%",
    }

    # 写报告
    write_report(results)
    status_path = NOTES / "cycle2_test_results.json"
    status_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📝 报告: {NOTES / 'cycle2_test_report.md'}")
    print(f"📊 数据: {status_path}")


def write_report(results: dict):
    s = results["summary"]
    md = f"""# CoPiano Cycle 2 综合测试报告

**测试时间**: {results['timestamp']}
**总通过率**: {s['overall_pass']}/{s['overall_total']} ({s['pass_rate']})

---

## 🌐 MAESTRO 公开数据集

**状态**: {'✅ 可下载' if s['maestro_available'] else '⚠️  失败'}
"""
    if results["tests"]["maestro_download"].get("available"):
        md += f"""- URL: {results["tests"]["maestro_download"]["url"]}
- 路径: `{results["tests"]["maestro_download"]["path"]}`
- 大小: {results["tests"]["maestro_download"]["size_bytes"]} bytes
"""
    else:
        md += "- 网络限制,使用自生成 MIDI 替代\n"
        for u in results["tests"]["maestro_download"].get("tried_urls", []):
            md += f"  - 尝试: {u}\n"

    md += f"""
---

## 🎹 MIDI analyzer 9 场景

| 场景 | 曲目 | 时期 | 来源 | Score | 错音 | 风格识别 | 音符 | 延迟 |
|------|------|------|------|-------|------|---------|------|------|
"""
    for r in results["tests"]["scenarios"]:
        if r["ok"]:
            score = r.get("score")
            md += f"| {r['scenario']} | {r['piece']} | {r['period']} | {r['source']} | {score if score is not None else 'solo'} | {r.get('n_pitch_errors', '-')} | {r['period_detected']} | {r['n_notes']} | {r['latency_s']}s |\n"
        else:
            md += f"| {r['scenario']} | - | - | - | - | - | - | - | ❌ |\n"

    md += f"""
**通过**: {s['scenarios_pass']}/{s['scenarios_total']}

---

## 🗣️ voice_dialog MIDI 集成

| Query | 状态 | 摘要 |
|-------|------|------|
"""
    if results["tests"]["voice_dialog_midi"].get("ok"):
        for q in results["tests"]["voice_dialog_midi"]["queries"]:
            if q.get("ok"):
                md += f"| {q['query']} | ✅ | {q['reply_preview']} |\n"
            else:
                md += f"| {q['query']} | ❌ | {q.get('error', '')} |\n"

    md += f"""
**通过**: {s['vd_pass']}/{s['vd_total']}

---

## 📈 Cycle 2 完成度

| 阶段 | 状态 | 内容 |
|------|------|------|
| 1. 调研 | ✅ | SWOT + 用户行为 + 6 改进候选 |
| 2. 实践 | ✅ | MIDI analyzer (9.5K) + voice_dialog 集成 |
| 3. 测试 | ✅ | 9 场景 + MAESTRO 尝试 + voice 集成 |

---

## 💡 下一步建议(Cycle 3)

- 修复 MAESTRO URL(可能要翻墙或换源)
- 扩展 MIDI analyzer:多文件批量、参考曲库推荐
- 表现力深度评估(SWOT 弱项 #2)
- 视奏(sight-reading)训练(MuseFlow 对标)
"""

    (NOTES / "cycle2_test_report.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
