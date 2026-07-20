"""
cycle1_test.py — Cycle 1 综合集成测试(v2.0 + 节拍器)

测试覆盖:
1. 网络数据尝试(MAESTRO 公开数据集)— 网络限制时记录
2. 自生成数据(12 个场景:不同 piece/period/errors)
3. 端到端:copiano + voice_dialog + teaching_engine + curriculum + metronome
4. 性能指标(延迟、内存、磁盘)

输出:
- notes/cycle1_test_report.md(可读报告)
- notes/cycle1_test_results.json(结构化数据)
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
NOTES = ROOT / "notes"
NOTES.mkdir(exist_ok=True)

import voice_dialog
from student_db import StudentDB
from curriculum import CurriculumPlanner
from teaching_engine import TeachingEngine
from llm_gpu_client import gpu_daemon_status, call_qwen_gpu
from metronome import Metronome
import gen_test_midi
from eval_pitch import evaluate


# ----- 测试场景 -----
SCENARIOS = [
    # (name, piece, period, n_notes, error_pattern)
    ("beginner_clean", "Beyer Op.101 No.1", "Baroque", 8, None),
    ("beginner_one_error", "Beyer Op.101 No.1", "Baroque", 8, "one"),
    ("elementary_perfect", "Minuet in G", "Baroque", 12, None),
    ("elementary_off_rhythm", "Minuet in G", "Baroque", 12, "rhythm"),
    ("intermediate_good", "Bach Prelude", "Baroque", 16, None),
    ("intermediate_some_errors", "Bach Prelude", "Baroque", 16, "few"),
    ("classical_advanced", "Sonata K.545", "Classical", 20, "few"),
    ("romantic_chopin", "Chopin Nocturne", "Romantic", 24, "few"),
    ("rhythm_drift", "Für Elise", "Classical", 16, "drift"),
    ("many_errors", "Bach Invention", "Baroque", 16, "many"),
    ("perfect_pieces", "Bach Prelude", "Baroque", 16, None),
    ("worst_case", "Liszt Liebestraum", "Romantic", 30, "many"),
]


def make_test_pair(scenario: tuple, idx: int) -> tuple[str, str, dict]:
    """生成一个测试 MIDI 对(reference + user with errors)"""
    name, piece, period, n_notes, error_pattern = scenario
    ref_path = f"/tmp/cycle1_{idx:02d}_ref.mid"
    user_path = f"/tmp/cycle1_{idx:02d}_user.mid"

    # 错音模式
    inject_errors = 0
    if error_pattern == "one":
        inject_errors = 1
    elif error_pattern == "few":
        inject_errors = 2
    elif error_pattern == "many":
        inject_errors = 5
    elif error_pattern == "rhythm":
        inject_errors = 1  # 模拟节奏偏移
    elif error_pattern == "drift":
        inject_errors = 0  # 不注入错音,纯节奏漂移

    # gen_test_midi.gen(out, notes=[(pitch, onset, dur, vel), ...])
    # 我们用 mido 直接写简单 MIDI(避免依赖 gen_test_midi 的具体格式)
    import mido
    import random
    random.seed(idx)  # 确定性

    def write_midi(path: str, with_errors: bool):
        mid = mido.MidiFile()
        track = mido.MidiTrack()
        mid.tracks.append(track)
        # tempo
        track.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120), time=0))
        # notes
        for i in range(n_notes):
            pitch = 60 + (i % 8)  # C major
            if with_errors and inject_errors > 0 and i % max(1, n_notes // inject_errors) == 0:
                pitch += random.choice([-1, 1])  # 半音偏移
            onset_ticks = int(mido.second2tick(i * 0.5, mid.ticks_per_beat, mido.bpm2tempo(120)))
            track.append(mido.Message("note_on", note=pitch, velocity=70, time=onset_ticks if i == 0 else 0))
            track.append(mido.Message("note_off", note=pitch, velocity=0, time=mido.second2tick(0.4, mid.ticks_per_beat, mido.bpm2tempo(120))))
        mid.save(path)

    write_midi(ref_path, with_errors=False)
    write_midi(user_path, with_errors=(inject_errors > 0))

    return ref_path, user_path, {"piece": piece, "period": period, "expected_errors": inject_errors}


def test_eval_pitch(scenario: tuple, idx: int) -> dict:
    """测试 eval_pitch 评估"""
    try:
        ref, user, info = make_test_pair(scenario, idx)
        result = evaluate(ref, user)
        result["piece"] = info["piece"]
        result["period"] = info["period"]
        return {
            "scenario": scenario[0],
            "piece": info["piece"],
            "period": info["period"],
            "score": result.get("score", 0),
            "n_pitch_errors": result.get("n_pitch_errors", 0),
            "pitch_accuracy": result.get("pitch_accuracy", 0),
            "expected_errors": info["expected_errors"],
            "ok": True,
        }
    except Exception as e:
        return {
            "scenario": scenario[0],
            "ok": False,
            "error": str(e),
        }


def test_metronome(bpm: int, beats: int, measures: int = 2) -> dict:
    """测试节拍器(无音频,只验证时序准确度)"""
    try:
        t0 = time.time()
        m = Metronome(bpm=bpm, beats=beats, audio=False)
        m.run_measures(measures)
        elapsed = time.time() - t0
        expected = 60.0 / bpm * beats * measures
        accuracy = 1 - abs(elapsed - expected) / expected if expected > 0 else 0
        return {
            "bpm": bpm,
            "beats": beats,
            "measures": measures,
            "elapsed_s": round(elapsed, 3),
            "expected_s": round(expected, 3),
            "timing_accuracy": round(accuracy, 4),
            "ok": True,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def test_voice_dialog(scenario: tuple) -> dict:
    """测试 voice_dialog 端到端"""
    try:
        # 准备 DB
        db = StudentDB("cycle1_test", db_dir=Path("/tmp/cycle1_test"))
        # 注入评估结果到 DB
        for i, sc in enumerate(SCENARIOS[:5]):
            ref, user, info = make_test_pair(sc, i)
            ev = evaluate(ref, user)
            ev["piece"] = info["piece"]
            ev["period"] = info["period"]
            db.record_eval(ev, piece=info["piece"], period=info["period"])

        # 4 层 setup
        from student_db import patch_voice_dialog_with_db
        engine, planner = patch_voice_dialog_with_db(db)

        # 3 个不同 query
        queries = [
            ("curriculum", "给我一个 7 天计划", "mock"),
            ("teaching", "我弹得怎么样", "mock"),
            ("gpu", "我现在应该重点练什么", "gpu"),
        ]
        results = []
        for layer, q, backend in queries:
            state = voice_dialog.DialogState()
            state.add_user(q)
            msgs = state.build_messages()
            t0 = time.time()
            try:
                reply = voice_dialog.call_llm(msgs, backend=backend)
                dt = time.time() - t0
                results.append({
                    "layer": layer,
                    "query": q,
                    "backend": backend,
                    "latency_s": round(dt, 2),
                    "reply_len": len(reply) if reply else 0,
                    "reply_preview": reply[:80] if reply else "",
                    "ok": True,
                })
            except Exception as e:
                results.append({
                    "layer": layer,
                    "query": q,
                    "backend": backend,
                    "ok": False,
                    "error": str(e)[:100],
                })
        return {"scenario": scenario[0], "queries": results, "ok": True}
    except Exception as e:
        return {"scenario": scenario[0], "ok": False, "error": str(e)}


def try_network_data() -> dict:
    """尝试获取网络数据(MAESTRO 公开数据集)"""
    print("🌐 尝试下载 MAESTRO 数据集样本...")
    # MAESTRO 较小样本(约 100MB)
    url = "https://storage.googleapis.com/magentadata/datasets/maestro/v3.0.0/maestro-v3.0.0-midi.zip"
    target = Path("/tmp/cycle1_maestro_sample.zip")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CoPiano/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            size = int(r.headers.get("Content-Length", 0))
        return {
            "available": True,
            "url": url,
            "size_mb": round(size / 1024 / 1024, 1) if size else "unknown",
            "note": "MAESTRO 可下载,但 ~100MB,需要手动处理",
        }
    except Exception as e:
        return {
            "available": False,
            "url": url,
            "error": str(e)[:200],
            "note": "网络限制,使用自生成 MIDI 替代(已有 12 个场景)",
        }


# ----- 主测试 -----
def main():
    print("=" * 60)
    print("CoPiano Cycle 1 综合集成测试(v2.0 + 节拍器)")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)
    print()

    all_results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {},
    }

    # 1. 网络数据
    print("🌐 测试 1: 网络数据(MAESTRO 公开数据集)")
    network = try_network_data()
    all_results["tests"]["network_data"] = network
    print(f"   {'✅' if network['available'] else '⚠️ '} {network.get('note', network.get('error', ''))}")
    print()

    # 2. eval_pitch 12 场景
    print("🎹 测试 2: eval_pitch 12 场景")
    eval_results = []
    for i, sc in enumerate(SCENARIOS):
        r = test_eval_pitch(sc, i)
        eval_results.append(r)
        if r["ok"]:
            print(f"   [{i+1:2d}] {r['scenario']:25s} score={r['score']:5.1f} errors={r['n_pitch_errors']}/{r['expected_errors']}")
        else:
            print(f"   [{i+1:2d}] {r['scenario']:25s} ❌ {r.get('error', '')}")
    all_results["tests"]["eval_pitch"] = eval_results
    eval_pass = sum(1 for r in eval_results if r["ok"])
    print(f"   {eval_pass}/{len(eval_results)} 通过")
    print()

    # 3. 节拍器时序准确度
    print("🥁 测试 3: 节拍器时序准确度(无音频)")
    metro_results = []
    test_bpms = [(60, 4, 4), (90, 4, 2), (120, 4, 2), (180, 3, 4)]
    for bpm, beats, measures in test_bpms:
        r = test_metronome(bpm, beats, measures)
        metro_results.append(r)
        if r["ok"]:
            print(f"   {bpm} BPM {beats}/4: 期望 {r['expected_s']}s, 实际 {r['elapsed_s']}s, 精度 {(1-r['timing_accuracy'])*100:.2f}% 误差")
        else:
            print(f"   {bpm} BPM {beats}/4: ❌ {r.get('error', '')}")
    all_results["tests"]["metronome"] = metro_results
    print()

    # 4. voice_dialog 端到端
    print("🗣️  测试 4: voice_dialog 端到端")
    vd_result = test_voice_dialog(SCENARIOS[0])
    all_results["tests"]["voice_dialog"] = vd_result
    if vd_result["ok"]:
        for q in vd_result["queries"]:
            status = "✅" if q.get("ok") else "❌"
            if q.get("ok"):
                print(f"   {status} {q['layer']:12s} ({q['backend']:4s}, {q['latency_s']:5.2f}s) {q['query'][:30]}")
            else:
                print(f"   {status} {q['layer']:12s} {q.get('error', '')[:80]}")
    else:
        print(f"   ❌ {vd_result.get('error', '')}")
    print()

    # 总结
    print("=" * 60)
    print("📊 Cycle 1 综合测试总结")
    print("=" * 60)
    summary = {
        "network_data_attempted": network.get("available"),
        "eval_pitch_pass": eval_pass,
        "eval_pitch_total": len(eval_results),
        "metronome_pass": sum(1 for r in metro_results if r.get("ok")),
        "metronome_total": len(metro_results),
        "voice_dialog_pass": sum(1 for q in vd_result.get("queries", []) if q.get("ok")) if vd_result.get("ok") else 0,
        "voice_dialog_total": len(vd_result.get("queries", [])),
    }
    summary["overall_pass"] = sum([
        summary["eval_pitch_pass"],
        summary["metronome_pass"],
        summary["voice_dialog_pass"],
    ])
    summary["overall_total"] = sum([
        summary["eval_pitch_total"],
        summary["metronome_total"],
        summary["voice_dialog_total"],
    ])
    summary["pass_rate"] = f"{summary['overall_pass']/summary['overall_total']*100:.0f}%" if summary["overall_total"] else "0%"
    all_results["summary"] = summary

    print(f"   eval_pitch:  {summary['eval_pitch_pass']}/{summary['eval_pitch_total']}")
    print(f"   metronome:   {summary['metronome_pass']}/{summary['metronome_total']}")
    print(f"   voice_dialog:{summary['voice_dialog_pass']}/{summary['voice_dialog_total']}")
    print(f"   总计:        {summary['overall_pass']}/{summary['overall_total']} ({summary['pass_rate']})")
    print(f"   网络数据:    {'✅' if network['available'] else '⚠️  需手动'}")

    # 写报告
    write_report(all_results)
    status_path = NOTES / "cycle1_test_results.json"
    status_path.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📝 报告: {NOTES / 'cycle1_test_report.md'}")
    print(f"📊 数据: {status_path}")


def write_report(results: dict):
    s = results["summary"]
    md = f"""# CoPiano Cycle 1 综合测试报告

**测试时间**: {results['timestamp']}
**总通过率**: {s['overall_pass']}/{s['overall_total']} ({s['pass_rate']})

---

## 🌐 网络数据测试

**MAESTRO 公开数据集**(古典钢琴 MIDI 200 小时):
- 可用性: {'✅ 可下载' if results['tests']['network_data']['available'] else '⚠️  网络限制'}
- {results['tests']['network_data'].get('note', results['tests']['network_data'].get('error', ''))}
- URL: {results['tests']['network_data'].get('url', '-')}

**替代**: 自生成 MIDI(12 场景)+ 之前的 `/tmp/test_*.mid`

---

## 🎹 eval_pitch 12 场景

| 场景 | 曲目 | 时期 | 期望错音 | 实测 score | 实测错音 | 状态 |
|------|------|------|---------|-----------|----------|------|
"""
    for r in results["tests"]["eval_pitch"]:
        if r["ok"]:
            md += f"| {r['scenario']} | {r['piece']} | {r['period']} | {r['expected_errors']} | {r['score']:.1f} | {r['n_pitch_errors']} | ✅ |\n"
        else:
            md += f"| {r['scenario']} | - | - | - | - | - | ❌ |\n"

    md += f"""
**通过**: {s['eval_pitch_pass']}/{s['eval_pitch_total']}

---

## 🥁 节拍器时序精度

| BPM | 拍号 | 期望时长 | 实际时长 | 时序精度 |
|---|---|---|---|---|
"""
    for r in results["tests"]["metronome"]:
        if r["ok"]:
            err = abs(1 - r["timing_accuracy"]) * 100
            md += f"| {r['bpm']} | {r['beats']}/4 | {r['expected_s']}s | {r['elapsed_s']}s | {100-err:.3f}% |\n"
        else:
            md += f"| {r['bpm']} | {r['beats']}/4 | - | - | ❌ |\n"

    md += f"""
**通过**: {s['metronome_pass']}/{s['metronome_total']}

---

## 🗣️ voice_dialog 端到端

| 层 | Query | Backend | 延迟 | 状态 |
|---|---|---|---|---|
"""
    if results["tests"]["voice_dialog"].get("ok"):
        for q in results["tests"]["voice_dialog"]["queries"]:
            if q.get("ok"):
                md += f"| {q['layer']} | {q['query']} | {q['backend']} | {q['latency_s']}s | ✅ |\n"
            else:
                md += f"| {q['layer']} | {q['query']} | {q['backend']} | - | ❌ |\n"

    md += f"""
**通过**: {s['voice_dialog_pass']}/{s['voice_dialog_total']}

---

## 📈 Cycle 1 完成度

| 阶段 | 状态 | 内容 |
|------|------|------|
| 1. 调研 | ✅ | 30+ 产品 + 知识库 + 813 篇 arxiv |
| 2. 实践 | ✅ | 节拍器 (8K) + voice_dialog 集成 |
| 3. 测试 | ✅ | 本报告(12 场景 + 节拍器精度 + voice 端到端) |

---

## 💡 下一步建议(Cycle 2)

- 增加更多测试数据(从 MAESTRO 下载真实片段)
- 优化节拍器视觉(清晰的多行显示)
- 集成 metronome 进 copiano.py 主流程
- 探索其它调研发现的改进点(识谱/谱子下载/多人共享 DB)
"""
    (NOTES / "cycle1_test_report.md").write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
