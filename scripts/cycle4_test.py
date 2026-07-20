"""
cycle4_test.py — Phase 6 CYCLE 4 综合测试

测试 hand_pose_analyzer 模块的:
1. 4 场景基础分析 (perfect/tense/collapsed/asymmetric)
2. 9 维度分数合理性
3. 综合分单调性 (PERFECT > TENSE > COLLAPSED)
4. voice_dialog 集成 (无递归)
5. JSON 输出结构完整性
6. 边界情况 (空数据、缺关键点)
"""

import json
import os
import sys
import time
import types
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from hand_pose_analyzer import (
    analyze_hand_pose,
    generate_test_hand_pose,
    patch_voice_dialog_with_hand_pose,
    compute_finger_curl,
    compute_wrist_height,
    compute_hand_arch,
    compute_thumb_position,
    compute_palm_contact,
    compute_hand_rotation,
    compute_symmetry,
    compute_finger_independence,
    compute_relaxation,
)


PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = {"pass": 0, "fail": 0, "warn": 0, "tests": []}


def record(name, ok, detail=""):
    if ok:
        results["pass"] += 1
        status = PASS
    else:
        results["fail"] += 1
        status = FAIL
    results["tests"].append({"name": name, "pass": ok, "detail": detail})
    print(f"{status} {name}: {detail}")


def test_4_scenarios():
    """测试 4 种手型分析"""
    print("\n=== Test 1: 4 场景分析 ===")
    scenarios = {
        'perfect': (75, 95),  # 期望分数范围
        'tense': (50, 80),
        'collapsed': (50, 80),
        'asymmetric': (50, 80),
    }
    scores = {}
    for pose, (lo, hi) in scenarios.items():
        lm = generate_test_hand_pose(pose)
        r = analyze_hand_pose(lm)
        scores[pose] = r['overall_score']
        ok = lo <= r['overall_score'] <= hi
        record(f"scenario_{pose}", ok,
               f"score={r['overall_score']:.1f} grade={r['grade']} dims={len(r['dimensions'])}")
    return scores


def test_monotonicity(scores):
    """测试综合分单调性: PERFECT > TENSE ≈ ASYMMETRIC > COLLAPSED"""
    print("\n=== Test 2: 单调性 ===")
    # 期望: PERFECT 最高
    ok = scores['perfect'] > scores['tense'] and scores['perfect'] > scores['collapsed']
    record("monotonicity_perfect_best", ok,
           f"PERFECT={scores['perfect']:.1f} > TENSE={scores['tense']:.1f} & COLLAPSED={scores['collapsed']:.1f}")
    return ok


def test_dimension_distribution():
    """测试 9 维度都返回了分数"""
    print("\n=== Test 3: 9 维度分布 ===")
    expected_dims = {
        'wrist_height', 'hand_arch', 'finger_curl', 'thumb_position',
        'palm_contact', 'hand_rotation', 'symmetry',
        'finger_independence', 'relaxation'
    }
    lm = generate_test_hand_pose('perfect')
    r = analyze_hand_pose(lm)
    missing = expected_dims - set(r['dimensions'].keys())
    extra = set(r['dimensions'].keys()) - expected_dims
    ok = len(missing) == 0 and len(extra) == 0
    record("all_9_dimensions", ok,
           f"missing={missing or 'none'} extra={extra or 'none'}")

    # 分数范围 0-100
    in_range = all(0 <= v <= 100 for v in r['dimensions'].values())
    record("dimension_score_range", in_range,
           f"all in [0,100]: {in_range}")


def test_finger_curl():
    """测试指节角度计算"""
    print("\n=== Test 4: 指节角度 ===")
    # Perfect 手型 4 指角度应在 30-90° 范围
    lm = generate_test_hand_pose('perfect')
    fc = compute_finger_curl(lm)
    print(f"   各指角度: " + ", ".join(
        f"{f}={info['angle']}°" for f, info in fc.items()
    ))
    for finger in ['index', 'middle', 'ring', 'pinky']:
        in_range = 20 <= fc[finger]['angle'] <= 100
        record(f"finger_curl_{finger}_range", in_range,
               f"angle={fc[finger]['angle']}° in [20,100]")

    # Tense 手型非拇指角度应接近 0 (伸直)
    lm_t = generate_test_hand_pose('tense')
    fc_t = compute_finger_curl(lm_t)
    for finger in ['index', 'middle', 'ring', 'pinky']:
        is_straight = fc_t[finger]['angle'] < 10
        record(f"tense_{finger}_straight", is_straight,
               f"angle={fc_t[finger]['angle']}° < 10°")

    # Asymmetric: 食指弯,4/5 指直
    lm_a = generate_test_hand_pose('asymmetric')
    fc_a = compute_finger_curl(lm_a)
    is_index_bent = fc_a['index']['angle'] > 30
    is_ring_straight = fc_a['ring']['angle'] < 10
    record("asymmetric_index_bent", is_index_bent,
           f"index angle={fc_a['index']['angle']}° > 30°")
    record("asymmetric_ring_straight", is_ring_straight,
           f"ring angle={fc_a['ring']['angle']}° < 10°")


def test_voice_dialog_integration():
    """测试 voice_dialog 集成 (无递归)"""
    print("\n=== Test 5: voice_dialog 集成 ===")
    # Mock voice_dialog
    vd = types.SimpleNamespace()
    call_count = [0]

    def original_call_llm(text, *args, **kwargs):
        call_count[0] += 1
        return f"LLM: {text}"

    vd.call_llm = original_call_llm
    vd.process_query = lambda text: original_call_llm(text)

    # Patch
    ok = patch_voice_dialog_with_hand_pose(vd)
    record("patch_applied", ok, f"patch result: {ok}")

    # 测试手型意图
    r1 = vd.process_query("分析我的手型")
    is_hand_response = "维度" in r1 or "手型" in r1
    record("intent_hand_pose", is_hand_response,
           f"got: {r1[:80]}...")

    # 测试非手型查询 (应走 LLM)
    r2 = vd.process_query("今天天气怎么样")
    is_llm_response = "LLM" in r2
    record("fallthrough_to_llm", is_llm_response,
           f"got: {r2}")

    # 测试无递归 (call_count 应该 = 1,不会反复调用)
    ok = call_count[0] == 1
    record("no_recursion", ok,
           f"LLM called {call_count[0]} times (expected 1)")

    # 测试多次调用不累积
    # 3 次调用: 1 个 hand pose (拦截) + 2 个普通 (走 LLM)
    # 所以 LLM 应被调用 1 (之前的) + 2 (新增) = 3 次
    vd.process_query("再来一次")  # 走 LLM
    vd.process_query("今天呢")  # 走 LLM
    r3 = vd.process_query("hand pose")  # 英文,拦截
    is_hand2 = "维度" in r3
    record("english_keyword", is_hand2,
           f"hand pose query: {r3[:60]}...")
    record("multi_calls_stable", call_count[0] == 3,
           f"after 3 LLM calls, count={call_count[0]} (expected 3)")


def test_json_output():
    """测试 JSON 输出结构"""
    print("\n=== Test 6: JSON 输出 ===")
    lm = generate_test_hand_pose('perfect')
    r = analyze_hand_pose(lm)
    j = json.dumps(r, ensure_ascii=False)
    # 重新解析
    parsed = json.loads(j)
    ok = (
        'overall_score' in parsed
        and 'dimensions' in parsed
        and 'finger_details' in parsed
        and 'suggestions' in parsed
        and 'grade' in parsed
    )
    record("json_structure", ok,
           f"keys: {list(parsed.keys())}")

    # suggestions 应该是 list
    ok2 = isinstance(parsed['suggestions'], list)
    record("suggestions_is_list", ok2,
           f"type: {type(parsed['suggestions']).__name__}, len: {len(parsed['suggestions'])}")

    # dimensions 应有 9 项
    ok3 = len(parsed['dimensions']) == 9
    record("dimensions_count", ok3,
           f"count: {len(parsed['dimensions'])}")


def test_edge_cases():
    """测试边界情况"""
    print("\n=== Test 7: 边界情况 ===")
    # 21 个零关键点
    try:
        zero_lm = [[0, 0, 0]] * 21
        r = analyze_hand_pose(zero_lm)
        ok = 0 <= r['overall_score'] <= 100
        record("zero_landmarks", ok, f"score={r['overall_score']}")
    except Exception as e:
        record("zero_landmarks", False, f"exception: {e}")

    # 不对称:手指伸得很直
    try:
        straight_lm = []
        for i in range(21):
            straight_lm.append([0.5 + i * 0.01, 0.5 - i * 0.01, 0])
        r = analyze_hand_pose(straight_lm)
        ok = 0 <= r['overall_score'] <= 100
        record("collinear_landmarks", ok, f"score={r['overall_score']}")
    except Exception as e:
        record("collinear_landmarks", False, f"exception: {e}")


def test_teaching_suggestions():
    """测试教学建议生成"""
    print("\n=== Test 8: 教学建议 ===")
    lm = generate_test_hand_pose('tense')
    r = analyze_hand_pose(lm)
    # 紧张手型应至少有建议
    ok = len(r['suggestions']) > 0
    record("suggestions_generated", ok,
           f"{len(r['suggestions'])} suggestions")

    # 建议应有具体文本
    has_advice = all('advice' in s and len(s['advice']) > 20 for s in r['suggestions'])
    record("suggestions_have_advice", has_advice,
           f"all have detailed advice: {has_advice}")

    # 严重程度分类
    severities = [s['severity'] for s in r['suggestions']]
    has_severity = 'high' in severities or 'medium' in severities
    record("severity_classified", has_severity,
           f"severities: {severities}")


def test_both_hands():
    """测试左右手分析"""
    print("\n=== Test 9: 左右手分析 ===")
    perfect = generate_test_hand_pose('perfect')
    asym = generate_test_hand_pose('asymmetric')
    # 用 perfect 当右手,asym 当左手,应得到 symmetry 差异
    r = analyze_hand_pose(perfect, left_landmarks=asym, right_landmarks=perfect)
    ok = 0 <= r['dimensions']['symmetry'] <= 100
    record("both_hands_symmetry", ok,
           f"symmetry={r['dimensions']['symmetry']}")


def test_speed():
    """测试处理速度"""
    print("\n=== Test 10: 处理速度 ===")
    lm = generate_test_hand_pose('perfect')
    t0 = time.time()
    for _ in range(100):
        r = analyze_hand_pose(lm)
    elapsed = (time.time() - t0) / 100
    ok = elapsed < 0.01  # < 10ms
    record("speed", ok, f"{elapsed*1000:.2f} ms/analyze")


def main():
    print("=" * 60)
    print("Phase 6 CYCLE 4 — Hand Pose Analyzer 综合测试")
    print("=" * 60)

    scores = test_4_scenarios()
    test_monotonicity(scores)
    test_dimension_distribution()
    test_finger_curl()
    test_voice_dialog_integration()
    test_json_output()
    test_edge_cases()
    test_teaching_suggestions()
    test_both_hands()
    test_speed()

    # 总结
    print("\n" + "=" * 60)
    print(f"结果: {results['pass']} 通过 / {results['fail']} 失败")
    total = results['pass'] + results['fail']
    if total > 0:
        pass_rate = results['pass'] / total * 100
        print(f"通过率: {pass_rate:.1f}%")
    print("=" * 60)

    # 导出报告
    out = {
        'cycle': 4,
        'pass': results['pass'],
        'fail': results['fail'],
        'tests': results['tests'],
        'summary': f"{results['pass']}/{results['pass'] + results['fail']}",
    }
    notes_dir = SCRIPT_DIR.parent / 'notes'
    notes_dir.mkdir(exist_ok=True)
    report_path = notes_dir / 'cycle4_test_results.json'
    with open(report_path, 'w') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n结果已存: {report_path}")

    report_md = notes_dir / 'cycle4_test_report.md'
    with open(report_md, 'w') as f:
        f.write(f"# Cycle 4 测试报告\n\n")
        f.write(f"**结果**: {results['pass']} / {results['pass'] + results['fail']} 通过\n\n")
        f.write(f"## 详细测试\n\n")
        f.write(f"| 测试 | 结果 | 详情 |\n|------|------|------|\n")
        for t in results['tests']:
            icon = PASS if t['pass'] else FAIL
            f.write(f"| {t['name']} | {icon} | {t['detail']} |\n")
    print(f"报告已存: {report_md}")

    return 0 if results['fail'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
