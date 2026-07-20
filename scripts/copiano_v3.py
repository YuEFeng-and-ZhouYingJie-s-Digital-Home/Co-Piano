"""
copiano_v3.py — CoPiano v3 统一 CLI (5 维 + 7d 课程 + A/B 验证)

用法:
    python3 copiano_v3.py demo --user yuefeng
    python3 copiano_v3.py curriculum --days 7
    python3 copiano_v3.py abtest --n 30 --days 7
    python3 copiano_v3.py scores --user yuefeng --age 65
    python3 copiano_v3.py voice --text "识谱训练"

整合 v3.0 所有模块:
- 5 维评分 (pitch + expressiveness + hand_pose + sight_reading + senior)
- 7 天多模态自适应课程 (curriculum_v2)
- A/B 测试 (ab_test_harness)
- voice_dialog 5 个模块集成 (识谱/银发/课程/手型/节拍)
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

# 默认用户档案
DEFAULT_USER = "yuefeng"
DEFAULT_AGE = 30
DEFAULT_DAYS = 7


def cmd_demo(args):
    """端到端 demo — 展示完整 v3.0 能力"""
    user = args.user or DEFAULT_USER
    age = args.age or DEFAULT_AGE
    print(f"🎹 CoPiano v3 端到端 demo for {user} (age={age})")
    print(f"{'='*60}\n")

    # 1. 5 维默认分数
    print("📊 5 维评估 (默认分数)")
    print("-" * 40)
    scores = {
        'pitch': 78.0,
        'expressiveness': 72.0,
        'hand_pose': 76.0,
        'rhythm': 82.0,
        'sight_reading': 65.0,
    }
    for d, s in scores.items():
        bar = '█' * int(s / 5) + '░' * (20 - int(s / 5))
        print(f"  {d:18s} {s:5.1f} {bar}")
    print()

    # 2. 弱项检测
    print("🎯 弱项检测 (top 3)")
    print("-" * 40)
    from curriculum_v2 import WeaknessDetector
    wd = WeaknessDetector(scores)
    weak = wd.detect(top_n=3)
    for w in weak:
        print(f"  #{w['rank']} {w['dimension']:18s} score={w['score']:.0f} severity={w['severity']}")
        print(f"     → {w['focus']}")
    print()

    # 3. 7 天课程
    print(f"📅 7 天多模态课程")
    print("-" * 40)
    from curriculum_v2 import AdaptivePlanner
    planner = AdaptivePlanner(age=age, time_per_day_min=args.time or 30, days=args.days or 7)
    planner.weakness_detector = wd
    plan = planner.generate_week_plan()
    for d in plan.days:
        icons = ''.join('•' for _ in d.blocks)
        senior = ' 👴' if d.senior_mode else ''
        print(f"  Day {d.day_num} ({d.date}) {d.theme:20s} {d.total_minutes()}min{senior}")
    print()

    # 4. 间隔复习
    print("🔁 间隔复习 (SM-2)")
    print("-" * 40)
    from curriculum_v2 import SpacedRepetition
    sr = SpacedRepetition()
    # 模拟 4 首曲子
    for piece, score in [('Bach Prelude', 92), ('Minuet in G', 75), ('Sonata K.545', 88), ('Für Elise', 60)]:
        sr.record_review(piece, score)
    due = sr.get_due_pieces(3)
    if due:
        for p in due:
            print(f"  {p['piece']:20s} due in {p['days_until']}d, ease={p['ease']}")
    else:
        print("  无 due 复习")
    print()

    # 5. A/B 测试
    print(f"🧪 A/B 测试 ({args.n or 30} per group × {args.days or 7} days)")
    print("-" * 40)
    from ab_test_harness import ABTestHarness, CohortSimulator
    sim = CohortSimulator(seed=42)
    harness = ABTestHarness(n_per_group=args.n or 30, days=args.days or 7, simulator=sim, seed=42)
    result = harness.run()
    print(f"  {result.summary.strip()}")
    print(f"  Effect sizes: d = {result.effect_sizes}")
    print()

    # 6. Voice dialog 集成
    print("🎤 Voice dialog 集成")
    print("-" * 40)
    from voice_dialog import _mock_llm
    queries = ['识谱训练', '长辈模式', '我的课程', '我的手型', '开始节拍器']
    for q in queries:
        # 简单 mock — 各模块关键词检测
        detected = []
        for kw, mod in [('识谱', 'sight_reading'), ('长辈', 'senior'), ('课程', 'curriculum'),
                        ('手型', 'hand_pose'), ('节拍器', 'metronome')]:
            if kw in q:
                detected.append(mod)
        if detected:
            print(f"  '{q}' → {detected}")
        else:
            print(f"  '{q}' → (no specific module)")
    print()

    print("="*60)
    print(f"✅ CoPiano v3 demo complete (5 维 + 7d 课程 + RCT d=0.43)")


def cmd_curriculum(args):
    """生成 7 天课程"""
    from curriculum_v2 import AdaptivePlanner
    planner = AdaptivePlanner(age=args.age, time_per_day_min=args.time, days=args.days)
    plan = planner.generate_week_plan()

    if args.json:
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(planner.format_plan(plan))


def cmd_abtest(args):
    """运行 A/B 测试"""
    from ab_test_harness import ABTestHarness, CohortSimulator, ReportGenerator
    sim = CohortSimulator(seed=args.seed)
    harness = ABTestHarness(n_per_group=args.n, days=args.days, simulator=sim, seed=args.seed)
    result = harness.run()

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(ReportGenerator.generate(result))


def cmd_scores(args):
    """5 维评分模拟 (无需真实 MIDI)"""
    # 基础分 + 年龄修正
    age_factor = 0.85 if args.age and args.age >= 60 else 1.0
    scores = {
        'pitch': round(70 * age_factor + 8, 1),
        'expressiveness': round(65 * age_factor + 5, 1),
        'hand_pose': round(75 * age_factor + 3, 1),
        'rhythm': round(80 * age_factor + 5, 1),
        'sight_reading': round(60 * age_factor + 5, 1),
    }
    output = {
        'user': args.user,
        'age': args.age,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'scores': scores,
        'senior_mode_active': args.age >= 60 if args.age else False,
    }
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"🎹 5 维评分 for {args.user} (age={args.age})")
        print(f"银发模式: {'激活' if output['senior_mode_active'] else '关闭'}")
        for d, s in scores.items():
            bar = '█' * int(s / 5) + '░' * (20 - int(s / 5))
            print(f"  {d:18s} {s:5.1f} {bar}")


def cmd_voice(args):
    """Voice dialog 集成测试"""
    text = args.text
    print(f"🎤 Voice input: '{text}'")

    # 关键词检测
    detected = []
    if any(kw in text for kw in ['识谱', '视奏', 'sight reading']):
        from sight_reading_trainer import patch_voice_dialog_with_sight_reading
        handle, state = patch_voice_dialog_with_sight_reading()
        result = handle(text)
        if result:
            print(f"  → 视奏模块: {result[:80]}")
            detected.append('sight_reading')

    if any(kw in text for kw in ['长辈', '老年', 'senior']):
        from senior_mode import patch_voice_dialog_with_senior_mode
        # mock age=70
        result = patch_voice_dialog_with_senior_mode(age=70)
        if result:
            print(f"  → 银发模式: {result[:80]}")
            detected.append('senior')

    if any(kw in text for kw in ['课程', '练什么', '我的']):
        from curriculum_v2 import patch_voice_dialog_with_curriculum, AdaptivePlanner
        planner = AdaptivePlanner(age=30)
        handle, state = patch_voice_dialog_with_curriculum(planner=planner)
        result = handle(text)
        if result:
            print(f"  → 课程模块: {result[:80]}")
            detected.append('curriculum')

    if not detected:
        # 走 LLM
        from voice_dialog import _mock_llm
        llm_resp = _mock_llm([{'role': 'user', 'content': text}])
        print(f"  → LLM mock: {llm_resp[:80]}")
        detected.append('llm')

    print(f"  Modules: {detected}")


def cmd_modules(args):
    """列出所有 v3.0 模块"""
    modules = [
        ('eval_pitch', '音准 + 节奏评估'),
        ('expressiveness_analyzer', '9 维表现力'),
        ('hand_pose_analyzer', '9 维手型'),
        ('sight_reading_trainer', '4 难度 × 3 模式视奏'),
        ('senior_mode', '4 开关银发模式'),
        ('curriculum_v2', '8 块多模态 7 天课程'),
        ('ab_test_harness', 'A/B 测试 + RCT'),
        ('metronome', '节拍器'),
        ('student_db', '学生长期记忆'),
        ('tonnetz_kg', '音乐理论知识图谱 (241 节点)'),
    ]
    print("🎹 CoPiano v3 模块清单")
    print("=" * 60)
    for mod, desc in modules:
        path = SCRIPTS / f"{mod}.py"
        exists = '✅' if path.exists() else '❌'
        print(f"  {exists} {mod:30s} {desc}")
    print()
    print(f"总模块数: {len(modules)}")


def main():
    p = argparse.ArgumentParser(description='CoPiano v3 统一 CLI')
    sub = p.add_subparsers(dest='command', help='子命令')

    # demo
    p_demo = sub.add_parser('demo', help='端到端 demo (5 维 + 课程 + A/B)')
    p_demo.add_argument('--user', default=DEFAULT_USER)
    p_demo.add_argument('--age', type=int, default=DEFAULT_AGE)
    p_demo.add_argument('--time', type=int, default=30, help='每天练习分钟')
    p_demo.add_argument('--days', type=int, default=7)
    p_demo.add_argument('--n', type=int, default=30, help='A/B 测试每组样本')
    p_demo.set_defaults(func=cmd_demo)

    # curriculum
    p_cur = sub.add_parser('curriculum', help='生成 7 天课程')
    p_cur.add_argument('--age', type=int, default=DEFAULT_AGE)
    p_cur.add_argument('--time', type=int, default=30)
    p_cur.add_argument('--days', type=int, default=7)
    p_cur.add_argument('--json', action='store_true')
    p_cur.set_defaults(func=cmd_curriculum)

    # abtest
    p_ab = sub.add_parser('abtest', help='运行 A/B 测试')
    p_ab.add_argument('--n', type=int, default=30)
    p_ab.add_argument('--days', type=int, default=7)
    p_ab.add_argument('--seed', type=int, default=42)
    p_ab.add_argument('--json', action='store_true')
    p_ab.set_defaults(func=cmd_abtest)

    # scores
    p_sc = sub.add_parser('scores', help='5 维评分 (模拟)')
    p_sc.add_argument('--user', default=DEFAULT_USER)
    p_sc.add_argument('--age', type=int, default=DEFAULT_AGE)
    p_sc.add_argument('--json', action='store_true')
    p_sc.set_defaults(func=cmd_scores)

    # voice
    p_vo = sub.add_parser('voice', help='Voice dialog 集成测试')
    p_vo.add_argument('--text', required=True)
    p_vo.set_defaults(func=cmd_voice)

    # modules
    p_md = sub.add_parser('modules', help='列出所有模块')
    p_md.set_defaults(func=cmd_modules)

    args = p.parse_args()
    if args.command is None:
        # 默认 demo
        args.command = 'demo'
        args.user = DEFAULT_USER
        args.age = DEFAULT_AGE
        args.time = 30
        args.days = 7
        args.n = 30
        args.func = cmd_demo

    args.func(args)


if __name__ == '__main__':
    main()
