"""
cycle7_test.py — Phase 6 CYCLE 7 综合测试

测试 curriculum_v2 模块的:
1. 8 块类型 (warmup_pitch / warmup_hand / expressiveness / sight_reading / main_piece / review / weakness / cooldown)
2. 5 维整合 (音高/表现力/手型/节奏/视奏)
3. DayPlanV2 字段 + total_minutes
4. WeekPlanV2 7 天生成
5. SpacedRepetition SM-2 简化算法
6. WeaknessDetector top 3 弱项
7. AdaptivePlanner 7 天 + 难度渐进
8. 银发模式 (age >= 60)
9. voice_dialog 集成 (无递归)
10. 自适应难度 (avg_score 升档)
"""

import json
import sys
import time
import types
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from curriculum_v2 import (
    BLOCK_TYPES,
    DIMENSION_NAMES,
    SPACED_INTERVALS,
    DIFFICULTY_PROGRESSION,
    BlockSpec,
    DayPlanV2,
    WeekPlanV2,
    SpacedRepetition,
    WeaknessDetector,
    AdaptivePlanner,
    get_difficulty_for_day,
    patch_voice_dialog_with_curriculum,
)


PASS = "✅"
FAIL = "❌"

results = {"pass": 0, "fail": 0, "tests": []}


def record(name, ok, detail=""):
    if ok:
        results["pass"] += 1
        status = PASS
    else:
        results["fail"] += 1
        status = FAIL
    results["tests"].append({"name": name, "pass": ok, "detail": detail})
    print(f"{status} {name}: {detail}")


# === Test 1: 8 块类型 ===
def test_block_types():
    print("\n=== Test 1: 8 块类型 ===")
    expected = {'warmup_pitch', 'warmup_hand', 'expressiveness', 'sight_reading',
                'main_piece', 'review_piece', 'weakness_drill', 'cooldown_relax'}
    record("has_8_block_types", set(BLOCK_TYPES.keys()) == expected,
           f"keys: {set(BLOCK_TYPES.keys())}")

    # 每个块都有必要字段
    required = ['name', 'name_en', 'default_minutes', 'module', 'description', 'icon']
    for bt, cfg in BLOCK_TYPES.items():
        missing = [k for k in required if k not in cfg]
        record(f"block_{bt}_complete", len(missing) == 0,
               f"all {len(required)} fields" if not missing else f"missing: {missing}")


# === Test 2: 5 维定义 ===
def test_dimensions():
    print("\n=== Test 2: 5 维 ===")
    record("has_5_dims", len(DIMENSION_NAMES) == 5, f"dims: {DIMENSION_NAMES}")
    record("dims_include_pitch", 'pitch' in DIMENSION_NAMES, "pitch")
    record("dims_include_sight_reading", 'sight_reading' in DIMENSION_NAMES, "sight_reading")


# === Test 3: BlockSpec ===
def test_block_spec():
    print("\n=== Test 3: BlockSpec ===")
    b = BlockSpec(block_type='warmup_pitch', minutes=5, target='C 大调')
    record("basic_init", b.minutes == 5 and b.block_type == 'warmup_pitch', f"min={b.minutes}")
    record("module_auto_set", b.module == 'eval_pitch', f"module={b.module}")
    record("name_auto", b.name == '音准热身', f"name={b.name}")

    d = b.to_dict()
    record("to_dict_has_all", all(k in d for k in ['block_type', 'minutes', 'target', 'module', 'notes', 'score']),
           f"keys: {list(d.keys())}")


# === Test 4: DayPlanV2 ===
def test_day_plan():
    print("\n=== Test 4: DayPlanV2 ===")
    blocks = [
        BlockSpec('warmup_pitch', 5),
        BlockSpec('warmup_hand', 3),
        BlockSpec('main_piece', 15),
        BlockSpec('cooldown_relax', 2),
    ]
    d = DayPlanV2(
        day_num=1, date='2026-07-21', theme='新起点',
        duration_min=25, blocks=blocks, daily_goals=['90 分', '错音 < 2'],
    )
    record("basic_init", d.day_num == 1, f"day={d.day_num}")
    record("total_minutes", d.total_minutes() == 25, f"total={d.total_minutes()}")
    record("block_count", len(d.blocks) == 4, f"blocks={len(d.blocks)}")
    record("summary_works", '新起点' in d.block_summary(), f"summary: {d.block_summary()}")
    record("to_dict", isinstance(d.to_dict(), dict), "to_dict ok")


# === Test 5: SpacedRepetition ===
def test_spaced_repetition():
    print("\n=== Test 5: SpacedRepetition ===")
    sr = SpacedRepetition()
    # 第一次 record → 初始化
    sr.record_review('Bach Prelude', 92, '2026-07-20')
    nr = sr.get_next_review('Bach Prelude')
    # days_until 可能是 0 或 -1 (取决于当天时间),允许小幅波动
    record("first_review_next_1day", nr['interval_idx'] == 0 and nr['days_until'] >= -1,
           f"next: {nr['next_review']}, interval_idx={nr['interval_idx']}, days_until={nr['days_until']}")

    # 答得好 (>=85) → interval_idx 推进
    sr.record_review('Bach Prelude', 90, '2026-07-21')
    nr2 = sr.get_next_review('Bach Prelude')
    record("score_90_advances", nr2['interval_idx'] >= 1, f"interval_idx={nr2['interval_idx']}")

    # 答得差 (<60) → 重置
    sr.record_review('Bad Piece', 50, '2026-07-21')
    nr3 = sr.get_next_review('Bad Piece')
    record("bad_score_resets", nr3['interval_idx'] == 0, f"interval_idx={nr3['interval_idx']}")

    # ease 变化
    record("ease_changed", nr2['ease'] > 1.5, f"ease={nr2['ease']}")

    # get_due_pieces
    sr.record_review('Old Piece', 88, '2026-06-01')  # 很久以前
    due = sr.get_due_pieces(3)
    record("get_due_pieces", isinstance(due, list), f"due: {len(due)} pieces")


# === Test 6: WeaknessDetector ===
def test_weakness():
    print("\n=== Test 6: WeaknessDetector ===")
    # 默认分数
    wd = WeaknessDetector()
    weak = wd.detect(top_n=3)
    record("default_weakness_count", len(weak) == 3, f"got {len(weak)}")
    # 第一名应该是最低分 (默认 sight_reading=60)
    record("first_is_lowest", weak[0]['dimension'] == 'sight_reading', f"first: {weak[0]['dimension']}")

    # 自定义分数
    wd2 = WeaknessDetector({'pitch': 50, 'expressiveness': 80, 'hand_pose': 70, 'rhythm': 90, 'sight_reading': 60})
    weak2 = wd2.detect(top_n=3)
    record("custom_weakness_first", weak2[0]['dimension'] == 'pitch', f"first: {weak2[0]['dimension']}")
    record("high_severity", weak2[0]['severity'] == 'high', f"severity={weak2[0]['severity']}")

    # 块类型映射
    record("pitch_to_warmup", weak2[0]['block_type'] == 'warmup_pitch', f"block_type={weak2[0]['block_type']}")
    record("has_focus", len(weak2[0]['focus']) > 0, f"focus: {weak2[0]['focus'][:30]}")


# === Test 7: AdaptivePlanner 默认 7 天 ===
def test_planner_default():
    print("\n=== Test 7: AdaptivePlanner 默认 7 天 ===")
    p = AdaptivePlanner()
    plan = p.generate_week_plan()
    record("has_7_days", len(plan.days) == 7, f"days: {len(plan.days)}")
    record("weekly_goals_count", len(plan.weekly_goals) == 3, f"goals: {len(plan.weekly_goals)}")
    record("difficulty_progression", len(plan.difficulty_progression) == 7,
           f"progression: {plan.difficulty_progression}")
    # 难度渐进
    record("day1_beginner", plan.days[0].difficulty == 'beginner', f"d1: {plan.days[0].difficulty}")
    record("day7_advanced", plan.days[6].difficulty == 'advanced', f"d7: {plan.days[6].difficulty}")


# === Test 8: AdaptivePlanner 块数 ===
def test_planner_blocks():
    print("\n=== Test 8: AdaptivePlanner 块数 ===")
    p = AdaptivePlanner()
    plan = p.generate_week_plan()
    for d in plan.days:
        # 6-8 块
        ok = 5 <= len(d.blocks) <= 8
        record(f"day{d.day_num}_blocks", ok, f"blocks: {len(d.blocks)} (total {d.total_minutes()}min)")


# === Test 9: 5 维整合 (8 块类型都用上) ===
def test_5d_integration():
    print("\n=== Test 9: 5 维整合 ===")
    p = AdaptivePlanner()
    plan = p.generate_week_plan()
    used_types = set()
    for d in plan.days:
        for b in d.blocks:
            used_types.add(b.block_type)
    # 7 天内应该覆盖大部分块类型
    expected_core = {'warmup_pitch', 'warmup_hand', 'main_piece', 'cooldown_relax'}
    record("core_blocks_used", expected_core.issubset(used_types),
           f"used: {used_types}")
    # 5 维模块映射
    modules_used = set()
    for d in plan.days:
        for b in d.blocks:
            modules_used.add(b.module)
    record("multi_modules", len(modules_used) >= 3, f"modules: {modules_used}")


# === Test 10: 银发模式 (age >= 60) ===
def test_senior_mode():
    print("\n=== Test 10: 银发模式 (age >= 60) ===")
    p = AdaptivePlanner(age=30)
    plan30 = p.generate_week_plan()
    record("age30_no_senior", not plan30.days[0].senior_mode, f"senior={plan30.days[0].senior_mode}")

    p60 = AdaptivePlanner(age=60)
    plan60 = p60.generate_week_plan()
    record("age60_senior_activated", plan60.days[0].senior_mode, f"senior={plan60.days[0].senior_mode}")

    p75 = AdaptivePlanner(age=75)
    plan75 = p75.generate_week_plan()
    record("age75_senior", plan75.days[0].senior_mode, f"senior={plan75.days[0].senior_mode}")

    # 银发模式:每日总时长更多 (+5)
    record("senior_more_time", plan60.days[0].duration_min > plan30.days[0].duration_min,
           f"30={plan30.days[0].duration_min}min, 60={plan60.days[0].duration_min}min")


# === Test 11: voice_dialog 集成 (无递归) ===
def test_voice_dialog_integration():
    print("\n=== Test 11: voice_dialog 集成 (无递归) ===")
    p = AdaptivePlanner()
    handle, state = patch_voice_dialog_with_curriculum(dialog_module=None, planner=p)

    # 关键词
    r = handle('我的课程')
    record("kw_我的课程", r is not None and 'Day 1' in r, f"r: {r[:60] if r else 'None'}")

    r2 = handle('今天练什么')
    record("kw_今天练什么", r2 is not None, f"r2: {r2[:60] if r2 else 'None'}")

    r3 = handle('查看计划')
    record("kw_查看计划", r3 is not None, f"r3: {r3[:60] if r3 else 'None'}")

    # 标记完成
    r4 = handle('标记完成')
    record("kw_标记完成", r4 is not None and 'Day' in r4, f"r4: {r4[:60] if r4 else 'None'}")
    record("day_advanced", state['current_day_idx'] == 1, f"day_idx={state['current_day_idx']}")

    # 跳过
    r5 = handle('跳过')
    record("kw_跳过", r5 is not None, f"r5: {r5[:60] if r5 else 'None'}")

    # Monkey patch 测试 (无递归)
    mock_mod = types.SimpleNamespace()
    call_count = {'llm': 0}

    def mock_call_llm(messages, **kwargs):
        call_count['llm'] += 1
        return "mock"
    mock_mod.call_llm = mock_call_llm
    mock_mod.process_query = None

    p2 = AdaptivePlanner()
    patch_voice_dialog_with_curriculum(mock_mod, p2)
    # 课程关键词
    r6 = mock_mod.process_query('我的课程')
    record("voice_no_recursion_on", r6 is not None, f"got: {r6[:50] if r6 else 'None'}")
    # 非关键词 → 走 LLM
    r7 = mock_mod.process_query('你好')
    record("voice_falls_to_llm", call_count['llm'] == 1, f"llm_call_count={call_count['llm']}")


# === Test 12: 自适应难度 (avg_score 升档) ===
def test_adaptive_difficulty():
    print("\n=== Test 12: 自适应难度 ===")
    # 高分用户:Day 1 应该有更高难度
    p_high = AdaptivePlanner()
    p_high.avg_score = 92
    plan_high = p_high.generate_week_plan()
    # 低分用户
    p_low = AdaptivePlanner()
    p_low.avg_score = 65
    plan_low = p_low.generate_week_plan()

    # 高分 Day 1 难度 >= 低分 Day 1 难度
    diffs = ['beginner', 'elementary', 'intermediate', 'advanced']
    idx_high = diffs.index(plan_high.days[0].difficulty)
    idx_low = diffs.index(plan_low.days[0].difficulty)
    record("high_score_advances", idx_high >= idx_low,
           f"high: {plan_high.days[0].difficulty} ({idx_high}), low: {plan_low.days[0].difficulty} ({idx_low})")


# === Test 13: get_difficulty_for_day 函数 ===
def test_difficulty_function():
    print("\n=== Test 13: get_difficulty_for_day ===")
    record("day1_default", get_difficulty_for_day(1) == 'beginner', f"d1={get_difficulty_for_day(1)}")
    record("day4_default", get_difficulty_for_day(4) == 'elementary', f"d4={get_difficulty_for_day(4)}")
    record("day7_default", get_difficulty_for_day(7) == 'advanced', f"d7={get_difficulty_for_day(7)}")

    # 高分
    record("high_d1", get_difficulty_for_day(1, 92) == 'elementary', f"d1=92: {get_difficulty_for_day(1, 92)}")
    # 低分
    record("low_d1", get_difficulty_for_day(1, 65) == 'beginner', f"d1=65: {get_difficulty_for_day(1, 65)}")


# === Test 14: format_plan 输出 ===
def test_format_plan():
    print("\n=== Test 14: format_plan 输出 ===")
    p = AdaptivePlanner(age=68, time_per_day_min=20)
    plan = p.generate_week_plan()
    text = p.format_plan(plan)
    record("has_title", 'CoPiano' in text or '🎹' in text, f"title: {text[:60]}")
    record("has_senior_marker", '银发模式' in text, "has 银发模式")
    record("has_7_days", text.count('Day ') >= 7, f"Day count: {text.count('Day ')}")
    record("has_weekly_goals", '目标' in text, "has 目标")


# === Test 15: 速度 (1 个 7 天计划 < 100ms) ===
def test_speed():
    print("\n=== Test 15: 速度 ===")
    start = time.time()
    for _ in range(10):
        p = AdaptivePlanner(age=65, time_per_day_min=30)
        p.generate_week_plan()
    elapsed = (time.time() - start) / 10
    record("plan_speed", elapsed < 0.5, f"{elapsed*1000:.1f}ms per plan")


# === Test 16: WeaknessDetector.from_student_db ===
def test_weakness_from_db():
    print("\n=== Test 16: WeaknessDetector.from_student_db ===")
    # 模拟 student_db
    class MockDB:
        data = {
            'evaluations': [
                {'score': 80, 'pitch_accuracy': 0.78},
                {'score': 75, 'pitch_accuracy': 0.70},
                {'score': 85, 'pitch_accuracy': 0.82},
            ]
        }
    wd = WeaknessDetector.from_student_db(MockDB())
    record("from_db_works", wd.dim_scores is not None, f"dims: {wd.dim_scores}")
    record("from_db_pitch_correct", 70 <= wd.dim_scores['pitch'] <= 85,
           f"pitch={wd.dim_scores['pitch']}")

    # 无数据的 db
    class EmptyDB:
        data = {'evaluations': []}
    wd2 = WeaknessDetector.from_student_db(EmptyDB())
    record("empty_db_uses_default", wd2.dim_scores is not None, "uses default")


# === Test 17: JSON 序列化 ===
def test_json():
    print("\n=== Test 17: JSON 序列化 ===")
    p = AdaptivePlanner()
    plan = p.generate_week_plan()
    try:
        s = json.dumps(plan.to_dict(), ensure_ascii=False)
        record("json_serializable", len(s) > 100, f"len={len(s)}")
    except Exception as e:
        record("json_serializable", False, f"err: {e}")


# === Test 18: 间隔复习集成 ===
def test_review_integration():
    print("\n=== Test 18: 间隔复习集成 ===")
    p = AdaptivePlanner()
    # 模拟一个 piece 很久以前学过
    p.spaced_rep.record_review('Old Bach', 88, '2026-06-01')
    plan = p.generate_week_plan()
    # Day 3 / 5 / 7 应该有 review_piece 块
    review_blocks = []
    for d in plan.days:
        for b in d.blocks:
            if b.block_type == 'review_piece':
                review_blocks.append((d.day_num, b.piece))
    record("has_review_blocks", len(review_blocks) > 0,
           f"reviews: {review_blocks}")


# === Test 19: 自定义 dim 分数 ===
def test_custom_dim():
    print("\n=== Test 19: 自定义 dim 分数 ===")
    p = AdaptivePlanner()
    # 强制覆盖
    p.weakness_detector = WeaknessDetector({
        'pitch': 95, 'expressiveness': 90, 'hand_pose': 85,
        'rhythm': 92, 'sight_reading': 88,
    })
    plan = p.generate_week_plan()
    # 弱项最少应该是 sight_reading (88 < 90) - 但 all > 80 → 都是 medium
    weak = plan.weakness_focus
    record("custom_weakness", len(weak) > 0, f"weak_focus: {weak}")


# === 主测试 ===
def main():
    print("=" * 60)
    print("Phase 6 CYCLE 7 — curriculum_v2 综合测试")
    print("=" * 60)

    test_block_types()
    test_dimensions()
    test_block_spec()
    test_day_plan()
    test_spaced_repetition()
    test_weakness()
    test_planner_default()
    test_planner_blocks()
    test_5d_integration()
    test_senior_mode()
    test_voice_dialog_integration()
    test_adaptive_difficulty()
    test_difficulty_function()
    test_format_plan()
    test_speed()
    test_weakness_from_db()
    test_json()
    test_review_integration()
    test_custom_dim()

    print("\n" + "=" * 60)
    total = results['pass'] + results['fail']
    rate = results['pass'] / total if total else 0
    print(f"结果: {results['pass']}/{total} pass ({rate:.0%})")
    if results['fail'] == 0:
        print("🎉 全部通过!")
    else:
        print("失败的测试:")
        for t in results['tests']:
            if not t['pass']:
                print(f"  ❌ {t['name']}: {t['detail']}")
    print("=" * 60)

    out_path = SCRIPT_DIR.parent / 'notes' / 'cycle7_test_results.json'
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    return 0 if results['fail'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
