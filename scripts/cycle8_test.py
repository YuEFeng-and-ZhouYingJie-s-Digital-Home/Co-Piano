"""
cycle8_test.py — Phase 6 CYCLE 8 综合测试

测试 ab_test_harness 模块的:
1. 数据类 (StudentCohort / ABTestResult)
2. CohortSimulator 单学生 + cohort
3. 学习率 (control vs treatment)
4. 银发模式 (age >= 60)
5. ABTestHarness setup + run
6. 统计函数 (mean/variance/std_dev/cohens_d/welch_t_test)
7. 统计正确性 (已知答案对比)
8. ReportGenerator 输出 markdown
9. JSON 序列化
10. 性能 (1 个完整 A/B test < 1s)
"""

import json
import math
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from ab_test_harness import (
    DEFAULT_LEARNING_RATES,
    SENIOR_LEARNING_RATES,
    DEFAULT_NOISE_STD,
    StudentCohort,
    ABTestResult,
    CohortSimulator,
    ABTestHarness,
    ReportGenerator,
    cohens_d,
    welch_t_test,
    mean,
    variance,
    std_dev,
    t_cdf,
    normal_cdf,
    regularized_incomplete_beta,
    effect_size_label,
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


# === Test 1: 数据类 ===
def test_dataclasses():
    print("\n=== Test 1: 数据类 ===")
    sc = StudentCohort(student_id='s001', age=30, group='control')
    record("student_cohort_init", sc.student_id == 's001' and sc.age == 30, f"id={sc.student_id}, age={sc.age}")
    record("default_initial_scores", 'pitch' in sc.initial_scores, f"has pitch: {sc.initial_scores.get('pitch')}")

    ar = ABTestResult(
        n_control=10, n_treatment=10, duration_days=7,
        dimensions=['pitch'],
        control_pre={'pitch': [70.0] * 10},
        control_post={'pitch': [75.0] * 10},
        treatment_pre={'pitch': [70.0] * 10},
        treatment_post={'pitch': [80.0] * 10},
    )
    record("ab_result_init", ar.n_control == 10, f"n_control={ar.n_control}")
    d = ar.to_dict()
    record("to_dict", isinstance(d, dict), f"keys: {list(d.keys())[:5]}")


# === Test 2: 统计函数基础 ===
def test_basic_stats():
    print("\n=== Test 2: 统计函数基础 ===")
    record("mean_basic", abs(mean([1, 2, 3, 4, 5]) - 3.0) < 0.01, f"mean=3")
    record("mean_empty", mean([]) == 0.0, "empty=0")
    record("variance_basic", abs(variance([1, 2, 3, 4, 5]) - 2.5) < 0.01, f"var=2.5")
    record("std_dev_basic", abs(std_dev([1, 2, 3, 4, 5]) - math.sqrt(2.5)) < 0.01,
           f"std={math.sqrt(2.5):.2f}")


# === Test 3: cohens_d ===
def test_cohens_d():
    print("\n=== Test 3: Cohen's d ===")
    # 已知答案:g1=[1,2,3,4,5] g2=[3,4,5,6,7] → |d| = 2/√(2.5) ≈ 1.265
    # 注意:d 符号由 g1-g2 决定 (g1 小 → d 负)
    d1 = cohens_d([1, 2, 3, 4, 5], [3, 4, 5, 6, 7])
    expected = 2.0 / math.sqrt(2.5)
    record("cohens_d_basic", abs(abs(d1) - expected) < 0.01, f"|d|={abs(d1):.3f}, expected={expected:.3f}")

    # 相同组 → d=0
    d2 = cohens_d([1, 2, 3], [1, 2, 3])
    record("cohens_d_zero", abs(d2) < 0.01, f"d={d2}")

    # 大效应 (避免方差 0,加少量噪声)
    g_low = [0.1, 0.2, 0.0, 0.15, 0.05]
    g_high = [10.0, 10.1, 9.9, 10.2, 9.8]
    d3 = abs(cohens_d(g_low, g_high))
    record("cohens_d_large", d3 > 5.0, f"|d|={d3:.2f} (large)")


# === Test 4: welch_t_test ===
def test_welch_t_test():
    print("\n=== Test 4: Welch t-test ===")
    # 显著差异 (g1 更大, t 应为正)
    t, p = welch_t_test([6, 7, 8, 9, 10], [1, 2, 3, 4, 5])
    record("t_test_significant", p < 0.05, f"t={t:.2f}, p={p:.4f}")
    record("t_positive", t > 0, f"t={t:.2f}")

    # 无差异
    t2, p2 = welch_t_test([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    record("t_test_ns", p2 > 0.5, f"t={t2:.2f}, p={p2:.4f}")


# === Test 5: normal_cdf + t_cdf ===
def test_distributions():
    print("\n=== Test 5: 分布函数 ===")
    # normal_cdf
    record("normal_cdf_0", abs(normal_cdf(0) - 0.5) < 0.01, f"cdf(0)={normal_cdf(0)}")
    record("normal_cdf_2", abs(normal_cdf(2) - 0.9772) < 0.01, f"cdf(2)={normal_cdf(2):.4f}")
    record("normal_cdf_-2", abs(normal_cdf(-2) - 0.0228) < 0.01, f"cdf(-2)={normal_cdf(-2):.4f}")

    # t_cdf (大 df → 接近 normal)
    record("t_cdf_0", abs(t_cdf(0, 30) - 0.5) < 0.01, f"t_cdf(0,30)={t_cdf(0, 30)}")
    record("t_cdf_2_df30", abs(t_cdf(2, 30) - 0.9729) < 0.02, f"t_cdf(2,30)={t_cdf(2, 30):.4f}")


# === Test 6: effect_size_label ===
def test_effect_labels():
    print("\n=== Test 6: Effect size 标签 ===")
    record("label_negligible", effect_size_label(0.1) == 'negligible', f"0.1=negligible")
    record("label_small", effect_size_label(0.3) == 'small', f"0.3=small")
    record("label_medium", effect_size_label(0.6) == 'medium', f"0.6=medium")
    record("label_large", effect_size_label(1.0) == 'large', f"1.0=large")
    record("label_negative", effect_size_label(-0.4) == 'small', f"-0.4=small (abs)")


# === Test 7: CohortSimulator ===
def test_simulator():
    print("\n=== Test 7: CohortSimulator ===")
    sim = CohortSimulator(seed=42)
    student = StudentCohort(student_id='s001', age=30, group='control')
    sim.simulate_student(student, days=7)
    record("simulate_7_days", len(student.daily_scores) == 8, f"len={len(student.daily_scores)} (day 0-7)")
    record("scores_in_range",
           all(0 <= student.daily_scores[-1][d] <= 100 for d in DEFAULT_LEARNING_RATES),
           f"post scores: {student.daily_scores[-1]}")


# === Test 8: control vs treatment 单学生对比 ===
def test_control_vs_treatment():
    print("\n=== Test 8: control vs treatment ===")
    sim = CohortSimulator(seed=42, noise_std=0)  # 无噪声,纯信号
    c = StudentCohort(student_id='c1', group='control', initial_scores={
        'pitch': 70, 'expressiveness': 65, 'hand_pose': 75, 'rhythm': 80, 'sight_reading': 60,
    })
    t = StudentCohort(student_id='t1', group='treatment', initial_scores={
        'pitch': 70, 'expressiveness': 65, 'hand_pose': 75, 'rhythm': 80, 'sight_reading': 60,
    })
    sim.simulate_student(c, 7)
    sim.simulate_student(t, 7)
    # 7 天后,treatment 应该比 control 进步更多
    record("treatment_pitch_higher", t.daily_scores[-1]['pitch'] > c.daily_scores[-1]['pitch'],
           f"control={c.daily_scores[-1]['pitch']:.1f}, treatment={t.daily_scores[-1]['pitch']:.1f}")
    record("treatment_sight_higher", t.daily_scores[-1]['sight_reading'] > c.daily_scores[-1]['sight_reading'],
           f"control sight={c.daily_scores[-1]['sight_reading']:.1f}, treatment={t.daily_scores[-1]['sight_reading']:.1f}")


# === Test 9: 银发模式 ===
def test_senior():
    print("\n=== Test 9: 银发模式 ===")
    sim = CohortSimulator(seed=42, learning_rates=SENIOR_LEARNING_RATES, noise_std=0)
    senior = StudentCohort(student_id='sr1', age=70, group='treatment',
                           initial_scores={'pitch': 70, 'expressiveness': 65,
                                           'hand_pose': 75, 'rhythm': 80, 'sight_reading': 60})
    sim.simulate_student(senior, 7)
    # 银发进步应比普通慢
    sim_normal = CohortSimulator(seed=42, noise_std=0)
    normal = StudentCohort(student_id='n1', age=30, group='treatment',
                           initial_scores={'pitch': 70, 'expressiveness': 65,
                                           'hand_pose': 75, 'rhythm': 80, 'sight_reading': 60})
    sim_normal.simulate_student(normal, 7)
    senior_gain = senior.daily_scores[-1]['pitch'] - 70
    normal_gain = normal.daily_scores[-1]['pitch'] - 70
    record("senior_slower", senior_gain < normal_gain,
           f"senior gain={senior_gain:.1f}, normal gain={normal_gain:.1f}")


# === Test 10: ABTestHarness setup + run ===
def test_harness_run():
    print("\n=== Test 10: ABTestHarness 运行 ===")
    harness = ABTestHarness(n_per_group=10, days=7, seed=42)
    control, treatment = harness.setup_cohorts()
    record("control_count", len(control) == 10, f"n={len(control)}")
    record("treatment_count", len(treatment) == 10, f"n={len(treatment)}")
    record("control_group", all(s.group == 'control' for s in control), "all control")
    record("treatment_group", all(s.group == 'treatment' for s in treatment), "all treatment")

    result = harness.run()
    record("result_dimensions", len(result.dimensions) == 5, f"dims: {result.dimensions}")
    record("result_stats", all(d in result.statistics for d in result.dimensions),
           f"stats: {list(result.statistics.keys())}")
    record("result_effect_sizes", len(result.effect_sizes) == 5, f"d: {list(result.effect_sizes.keys())}")


# === Test 11: treatment 优于 control ===
def test_treatment_better():
    print("\n=== Test 11: treatment 优于 control ===")
    harness = ABTestHarness(n_per_group=20, days=7, seed=42)
    result = harness.run()
    # 每个维度 treatment post 应该 >= control post (因为课程有提升)
    wins = 0
    for d in result.dimensions:
        if result.statistics[d]['treatment_post'] >= result.statistics[d]['control_post']:
            wins += 1
    # 4/5 维度获胜就足够 (考虑 1 维可能落入噪声)
    record("treatment_wins_majority", wins >= 4, f"treatment wins {wins}/5 dims")


# === Test 12: effect size 合理范围 ===
def test_effect_range():
    print("\n=== Test 12: effect size 范围 ===")
    harness = ABTestHarness(n_per_group=30, days=7, seed=42)
    result = harness.run()
    for d in result.dimensions:
        d_val = result.effect_sizes[d]
        # 允许负数 (control > treatment) 在小样本时也可能
        record(f"d_{d}_in_range", -2.0 <= d_val <= 5.0, f"d={d_val:.3f}")


# === Test 13: ReportGenerator ===
def test_report():
    print("\n=== Test 13: ReportGenerator ===")
    harness = ABTestHarness(n_per_group=10, days=7, seed=42)
    result = harness.run()
    report = ReportGenerator.generate(result)
    record("has_title", 'CoPiano' in report, f"title ok")
    record("has_table", '| pitch |' in report, f"table ok")
    record("has_summary", '效应' in report or 'Effect' in report, "has 效应")
    record("has_conclusion", '结论' in report, "has 结论")


# === Test 14: JSON 序列化 ===
def test_json():
    print("\n=== Test 14: JSON 序列化 ===")
    harness = ABTestHarness(n_per_group=5, days=3, seed=42)
    result = harness.run()
    s = json.dumps(result.to_dict(), ensure_ascii=False)
    record("json_serializable", len(s) > 100, f"len={len(s)}")
    # 解析
    parsed = json.loads(s)
    record("json_round_trip", parsed['n_control'] == 5, f"n_control={parsed['n_control']}")


# === Test 15: 性能 (1 个完整 A/B test < 1s) ===
def test_speed():
    print("\n=== Test 15: 性能 ===")
    start = time.time()
    harness = ABTestHarness(n_per_group=30, days=7, seed=42)
    result = harness.run()
    elapsed = time.time() - start
    record("ab_test_speed", elapsed < 1.0, f"{elapsed*1000:.1f}ms for 30/group × 7 days")


# === Test 16: 多次运行可重现 (固定 seed) ===
def test_reproducible():
    print("\n=== Test 16: 可重现性 ===")
    h1 = ABTestHarness(n_per_group=10, days=7, seed=42)
    r1 = h1.run()
    h2 = ABTestHarness(n_per_group=10, days=7, seed=42)
    r2 = h2.run()
    # 同样 seed,同样结果
    same = all(
        abs(r1.statistics[d]['treatment_post'] - r2.statistics[d]['treatment_post']) < 0.01
        for d in r1.dimensions
    )
    record("same_seed_same_result", same, "deterministic")


# === Test 17: regularized_incomplete_beta ===
def test_beta():
    print("\n=== Test 17: Beta 函数 ===")
    # 已知值:I_0.5(1, 1) = 0.5
    v1 = regularized_incomplete_beta(0.5, 1, 1)
    record("beta_half_1_1", abs(v1 - 0.5) < 0.01, f"I_0.5(1,1)={v1:.4f}")


# === Test 18: summary 字段 ===
def test_summary():
    print("\n=== Test 18: summary 字段 ===")
    harness = ABTestHarness(n_per_group=5, days=3, seed=42)
    result = harness.run()
    record("has_summary", 'A/B 测试完成' in result.summary, f"summary: {result.summary[:60]}")


# === 主测试 ===
def main():
    print("=" * 60)
    print("Phase 6 CYCLE 8 — ab_test_harness 综合测试")
    print("=" * 60)

    test_dataclasses()
    test_basic_stats()
    test_cohens_d()
    test_welch_t_test()
    test_distributions()
    test_effect_labels()
    test_simulator()
    test_control_vs_treatment()
    test_senior()
    test_harness_run()
    test_treatment_better()
    test_effect_range()
    test_report()
    test_json()
    test_speed()
    test_reproducible()
    test_beta()
    test_summary()

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

    out_path = SCRIPT_DIR.parent / 'notes' / 'cycle8_test_results.json'
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))

    return 0 if results['fail'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
