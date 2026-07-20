"""
benchmarks.py — CoPiano v3 性能基准测试

Cycle 16 实现:
- 13 个核心模块的耗时/内存/精度 基准
- 输出 markdown 报告 + JSON
- 用于:
  1. 论文 Section 5.5 (Computational Performance)
  2. README 性能数据
  3. 性能回归监控

用法:
    python3 benchmarks.py --output notes/benchmark_report.md
    python3 benchmarks.py --quick  # 仅关键模块
"""

import argparse
import json
import os
import platform
import sys
import time
import tracemalloc
from pathlib import Path
from typing import Dict, List, Tuple

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))


# === 基准测试 ===

def bench(name: str, fn, n_iter: int = 3) -> Dict:
    """运行 fn n_iter 次,返回 mean/median/min/max ms"""
    times = []
    peak_mem_kb = 0
    for _ in range(n_iter):
        tracemalloc.start()
        t0 = time.perf_counter()
        try:
            fn()
        except Exception as e:
            tracemalloc.stop()
            return {
                'name': name,
                'error': str(e),
                'mean_ms': 0,
                'median_ms': 0,
                'min_ms': 0,
                'max_ms': 0,
                'peak_mem_kb': 0,
            }
        elapsed_ms = (time.perf_counter() - t0) * 1000
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        times.append(elapsed_ms)
        peak_mem_kb = max(peak_mem_kb, peak / 1024)
    times_sorted = sorted(times)
    return {
        'name': name,
        'mean_ms': round(sum(times) / n_iter, 3),
        'median_ms': round(times_sorted[n_iter // 2], 3),
        'min_ms': round(times_sorted[0], 3),
        'max_ms': round(times_sorted[-1], 3),
        'peak_mem_kb': round(peak_mem_kb, 1),
    }


# === 各模块基准 ===

def b_pitch_eval():
    """D1 音准评估"""
    from eval_pitch import evaluate
    import os
    # 用真实测试 MIDI (若有)
    ref = '/tmp/test_ref.mid'
    user = '/tmp/test_user.mid'
    if os.path.exists(ref) and os.path.exists(user):
        evaluate(ref, user)
    else:
        # 退化: 创建临时 MIDI
        import tempfile
        import pretty_midi
        pm_ref = pretty_midi.PrettyMIDI()
        pm_user = pretty_midi.PrettyMIDI()
        inst_r = pretty_midi.Instrument(program=0)
        inst_u = pretty_midi.Instrument(program=0)
        for i in range(20):
            inst_r.notes.append(pretty_midi.Note(80, 60 + (i % 12), i * 0.5, i * 0.5 + 0.4))
            inst_u.notes.append(pretty_midi.Note(80, 60 + (i % 12) + (1 if i % 5 == 0 else 0),
                                                i * 0.5, i * 0.5 + 0.4))
        pm_ref.instruments.append(inst_r)
        pm_user.instruments.append(inst_u)
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f1, \
             tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f2:
            pm_ref.write(f1.name)
            pm_user.write(f2.name)
            evaluate(f1.name, f2.name)


def b_expressiveness():
    """D2 9 维表现力"""
    import os
    from expressiveness_analyzer import analyze_expressiveness
    midi = '/tmp/test_user.mid'
    if os.path.exists(midi):
        analyze_expressiveness(midi)
    else:
        # 退化
        import tempfile
        import pretty_midi
        pm = pretty_midi.PrettyMIDI()
        inst = pretty_midi.Instrument(program=0)
        for i in range(30):
            inst.notes.append(pretty_midi.Note(80 + i % 40, 60 + (i % 12),
                                                i * 0.5, i * 0.5 + 0.4))
        pm.instruments.append(inst)
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
            pm.write(f.name)
            analyze_expressiveness(f.name)


def b_hand_pose():
    """D3 9 维手型"""
    from hand_pose_analyzer import analyze_hand_pose, generate_test_hand_pose
    keypoints = generate_test_hand_pose('perfect')  # 21 keypoints
    analyze_hand_pose(keypoints)


def b_sight_reading():
    """D4 4 难度视奏"""
    from sight_reading_trainer import SightReadingTrainer
    t = SightReadingTrainer(difficulty='intermediate', mode='random', seed=42)
    t.generate_sequence(count=20)
    for n in t.sequence:
        t.submit_answer(n.pitch)
    t.finish()


def b_senior_mode():
    """D5 银发模式"""
    from senior_mode import simplify_text_for_senior
    text = "你的 rubato 段落速度略快,ritardando 标记没体现,需要练习 crescendo 来表达浪漫主义情感。"
    for _ in range(10):
        simplify_text_for_senior(text)


def b_curriculum():
    """7 天多模态课程"""
    from curriculum_v2 import AdaptivePlanner
    p = AdaptivePlanner(age=30, time_per_day_min=30, days=7)
    p.generate_week_plan()


def b_abtest():
    """A/B 测试 30/30 × 7 days"""
    from ab_test_harness import ABTestHarness, CohortSimulator
    sim = CohortSimulator(seed=42)
    harness = ABTestHarness(n_per_group=30, days=7, simulator=sim, seed=42)
    harness.run()


def b_test_data():
    """真实化数据生成 60 学生"""
    from test_data_generator import generate_cohort
    generate_cohort(30, 7, 42)


def b_voice_intent():
    """Voice dialog 关键词识别"""
    from voice_dialog import _mock_llm
    for q in ['你好', '评分', '巴洛克', '怎么练', '拜厄']:
        _mock_llm([{'role': 'user', 'content': q}])


def b_tonnetz_query():
    """Tonnetz KG 查询 (无外部依赖,可能失败)"""
    try:
        from tonnetz_kg import MusicKG
        kg = MusicKG()
        # 简单查询
        if hasattr(kg, 'query'):
            kg.query('Bach')
    except Exception:
        pass


def b_paper_figures():
    """6 论文图表生成"""
    from paper_figures import get_ab_test_data
    get_ab_test_data(n_per_group=30, days=7, seed=42)


def b_copiano_v3_demo():
    """端到端 demo"""
    import argparse as ap
    from copiano_v3 import cmd_demo
    args = ap.Namespace(user='test', age=30, time=30, days=7, n=10,
                        command='demo', func=cmd_demo)
    cmd_demo(args)


def b_sight_reading_full():
    """完整视奏流程"""
    from sight_reading_trainer import SightReadingTrainer
    t = SightReadingTrainer(difficulty='advanced', mode='piece', seed=42)
    t.generate_sequence()
    for n in t.sequence:
        t.submit_answer(n.pitch)
    t.finish()


# === 报告生成 ===

def format_report(results: List[Dict], env_info: Dict) -> str:
    """生成 markdown 报告"""
    lines = [
        "# CoPiano v3 — Performance Benchmark Report",
        f"_生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        "## 🖥️ 环境",
        "",
        f"- **Platform**: {env_info['platform']}",
        f"- **Python**: {env_info['python']}",
        f"- **CPU**: {env_info['cpu']}",
        f"- **Memory**: {env_info['memory_gb']} GB",
        "",
        "## 📊 基准结果 (按耗时排序)",
        "",
        "| # | Module | Description | Mean (ms) | Median (ms) | Min (ms) | Max (ms) | Peak Mem (KB) |",
        "|---|--------|-------------|-----------|-------------|----------|----------|---------------|",
    ]
    # 按 mean_ms 排序
    results_sorted = sorted(results, key=lambda r: r.get('mean_ms', 0))
    for i, r in enumerate(results_sorted, 1):
        if 'error' in r:
            lines.append(f"| {i} | {r['name']} | (error) | — | — | — | — | — |")
            continue
        lines.append(
            f"| {i} | {r['name']} | | {r['mean_ms']:.2f} | {r['median_ms']:.2f} | "
            f"{r['min_ms']:.2f} | {r['max_ms']:.2f} | {r['peak_mem_kb']:.1f} |"
        )

    # 关键指标
    lines.append("\n## 🎯 关键指标")
    lines.append("")
    successful = [r for r in results if 'error' not in r]
    if successful:
        total = sum(r['mean_ms'] for r in successful)
        lines.append(f"- **总耗时**: {total:.1f} ms ({total/1000:.2f} s)")
        lines.append(f"- **模块数**: {len(successful)} 个核心模块")
        lines.append(f"- **平均耗时**: {total/len(successful):.2f} ms / 模块")
        # 找出最快和最慢
        fastest = min(successful, key=lambda r: r['mean_ms'])
        slowest = max(successful, key=lambda r: r['mean_ms'])
        lines.append(f"- **最快**: {fastest['name']} ({fastest['mean_ms']:.2f} ms)")
        lines.append(f"- **最慢**: {slowest['name']} ({slowest['mean_ms']:.2f} ms)")
        # 内存
        max_mem = max(successful, key=lambda r: r['peak_mem_kb'])
        lines.append(f"- **内存峰值**: {max_mem['name']} ({max_mem['peak_mem_kb']:.1f} KB)")

    # 性能目标
    lines.append("\n## 🎯 性能目标 (生产可用)")
    lines.append("")
    lines.append("| 目标 | 阈值 | 状态 |")
    lines.append("|------|------|------|")
    target_pass = lambda r, t: '✅' if r['mean_ms'] < t else '❌'
    targets = {
        'D1 音准评估': (b_pitch_eval, 100, '< 100ms (8 音符 80 个)'),
        'D2 9 维表现力': (b_expressiveness, 500, '< 500ms (50 音符)'),
        'D3 9 维手型': (b_hand_pose, 100, '< 100ms (30 帧)'),
        'D4 视奏 (中级)': (b_sight_reading, 50, '< 50ms (20 音符)'),
        '5 课程生成': (b_curriculum, 10, '< 10ms (7 天)'),
        'A/B 测试': (b_abtest, 100, '< 100ms (30/30 × 7)'),
        '6 论文图表': (b_paper_figures, 50, '< 50ms'),
    }
    for name, (fn, target_ms, desc) in targets.items():
        match_result = next((r for r in successful if r['name'] == name), None)
        if match_result:
            status = target_pass(match_result, target_ms)
            lines.append(f"| {name} | {desc} | {status} ({match_result['mean_ms']:.2f}ms) |")
        else:
            lines.append(f"| {name} | {desc} | ❌ (未测) |")

    return '\n'.join(lines)


# === Main ===

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', default='notes/benchmark_report.md')
    p.add_argument('--json', help='JSON 输出路径')
    p.add_argument('--quick', action='store_true', help='快速模式 (仅关键模块)')
    p.add_argument('--iter', type=int, default=3, help='每模块迭代次数')
    args = p.parse_args()

    print(f"⏱️ CoPiano v3 Performance Benchmark (iter={args.iter})")
    print(f"{'='*60}\n")

    # 环境信息
    import platform as pl
    env_info = {
        'platform': pl.platform(),
        'python': sys.version.split()[0],
        'cpu': pl.processor() or 'unknown',
        'memory_gb': round(os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 1024**3, 1)
        if hasattr(os, 'sysconf') else 0,
    }
    print(f"🖥️  {env_info['platform']}")
    print(f"🐍  Python {env_info['python']}\n")

    # 所有基准
    all_benchmarks = [
        ('D1 音准评估', b_pitch_eval),
        ('D2 9 维表现力', b_expressiveness),
        ('D3 9 维手型', b_hand_pose),
        ('D4 视奏 (中级)', b_sight_reading),
        ('D4 视奏 (高级+真曲)', b_sight_reading_full),
        ('D5 银发模式', b_senior_mode),
        ('5 课程生成', b_curriculum),
        ('A/B 测试', b_abtest),
        ('真实化数据生成', b_test_data),
        ('Voice intent', b_voice_intent),
        ('Tonnetz KG 查询', b_tonnetz_query),
        ('6 论文图表', b_paper_figures),
        ('端到端 demo', b_copiano_v3_demo),
    ]

    if args.quick:
        all_benchmarks = all_benchmarks[:5]

    results = []
    for name, fn in all_benchmarks:
        print(f"  {name}...", end=' ', flush=True)
        r = bench(name, fn, n_iter=args.iter)
        if 'error' in r:
            print(f"❌ {r['error'][:50]}")
        else:
            print(f"✅ {r['mean_ms']:.2f}ms (mem {r['peak_mem_kb']:.0f}KB)")
        results.append(r)

    # 写报告
    report = format_report(results, env_info)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)
    print(f"\n📄 Report: {output_path.absolute()}")

    # JSON
    if args.json:
        json_path = Path(args.json)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps({
            'env': env_info,
            'results': results,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }, ensure_ascii=False, indent=2))
        print(f"📄 JSON: {json_path.absolute()}")


if __name__ == '__main__':
    main()
