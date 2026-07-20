"""
test_data_generator.py — CoPiano 真实测试数据生成器

Cycle 13 实现:
- 生成 60 学生 (30 control + 30 treatment) × 7 天 真实 5 维轨迹
- 现实学习曲线 (非线性:S 型 / 渐近 / 平台期)
- 现实年龄分布 (25-70 混合)
- 现实初始水平 (正态分布,带差异)
- 缺勤 / 表现波动 (周末/疲劳)
- 输出 JSON 可直接喂入 ab_test_harness + paper_figures
- 论文用:"真实学生模拟" vs 之前 cycle 8 的"纯数学模型"

用法:
    python3 test_data_generator.py --n 30 --days 7 --output data/test_cohort.json
    python3 test_data_generator.py --n 10 --seed 42 --pretty
"""

import argparse
import hashlib
import json
import math
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# === 5 维初始分数 (per age group, mean ± std) ===

INITIAL_SCORES_BY_AGE = {
    # 年龄段: (pitch, expressiveness, hand_pose, rhythm, sight_reading)
    'young_adult': {  # 25-30
        'mean': (72, 67, 75, 80, 65),
        'std':  (4, 5, 4, 3, 5),
    },
    'middle_adult': {  # 35-45
        'mean': (68, 64, 73, 78, 60),
        'std':  (5, 5, 4, 4, 6),
    },
    'senior': {  # 60-70
        'mean': (62, 58, 70, 74, 55),
        'std':  (5, 5, 4, 4, 6),
    },
}

# 5 维最大可能分数 (天花板 95 — 完美 100 几乎不可能)
MAX_SCORES = {
    'pitch':          95,
    'expressiveness': 95,
    'hand_pose':      95,
    'rhythm':         95,
    'sight_reading':  90,  # 视奏更难突破
}

# 维度学习曲线类型 (S 型 / 渐近 / 平台)
LEARNING_CURVE_TYPES = {
    'pitch':          'sigmoid',      # S 型:慢-快-慢
    'expressiveness': 'asymptotic',   # 渐近:快-慢
    'hand_pose':      'linear',       # 线性 (身体技能)
    'rhythm':         'linear',       # 线性
    'sight_reading':  'plateau',      # 平台:慢-快-平台
}


# === 工具函数 ===

def stable_seed(*args) -> int:
    """MD5 稳定 seed (避免 Python hash 随机化)"""
    s = ':'.join(str(a) for a in args)
    return int(hashlib.md5(s.encode()).hexdigest()[:8], 16)


def sample_initial_scores(age_group: str, rng: random.Random) -> Dict[str, float]:
    """按年龄组采样初始分数"""
    cfg = INITIAL_SCORES_BY_AGE[age_group]
    scores = {}
    for i, dim in enumerate(['pitch', 'expressiveness', 'hand_pose', 'rhythm', 'sight_reading']):
        m = cfg['mean'][i]
        s = cfg['std'][i]
        # 截断到 50-85 (新学员不会 < 50, 也不会 > 85)
        val = max(50, min(85, rng.gauss(m, s)))
        scores[dim] = round(val, 1)
    return scores


def apply_learning_curve(start: float, day: int, total_days: int, curve_type: str,
                          treatment: bool, age_factor: float = 1.0,
                          noise_rng: random.Random = None) -> float:
    """
    应用学习曲线 +纳Day
    - day: 0-7
    - total_days: 7
    - curve_type: sigmoid/asymptotic/linear/plateau
    - treatment: 是否用课程
    - age_factor: 0.7 银发
    """
    if noise_rng is None:
        noise_rng = random.Random()

    # 基础增益 (treatment 2-3x natural)
    if treatment:
        base_gain = {'sigmoid': 6, 'asymptotic': 5, 'linear': 4, 'plateau': 4}.get(curve_type, 4)
    else:
        base_gain = {'sigmoid': 2, 'asymptotic': 2, 'linear': 2, 'plateau': 1.5}.get(curve_type, 2)
    base_gain *= age_factor

    # 曲线
    progress = day / total_days  # 0-1
    if curve_type == 'sigmoid':
        # S 型:1/(1+e^(-12(x-0.5))),归一化
        curve = 1 / (1 + math.exp(-12 * (progress - 0.5)))
    elif curve_type == 'asymptotic':
        # 渐近:1 - e^(-3x)
        curve = 1 - math.exp(-3 * progress)
    elif curve_type == 'linear':
        curve = progress
    elif curve_type == 'plateau':
        # 平台:在 day 4 后停止增长
        if day <= 4:
            curve = progress * 1.2
        else:
            curve = 0.5 + (day - 4) * 0.05
    else:
        curve = progress

    gain = base_gain * curve

    # 缺勤 / 疲劳噪声
    if day in (6, 7):  # 周末更累
        gain *= 0.7
    noise = noise_rng.gauss(0, 1.5)

    new_score = start + gain + noise
    return new_score


# === 生成器 ===

def generate_student(student_id: str, age: int, group: str, days: int = 7,
                            seed: int = 42) -> Dict:
    """
    生成单个学生 7 天 5 维轨迹
    返回 dict: {id, age, age_group, group, initial_scores, daily_scores, ...}
    """
    rng = random.Random(stable_seed(student_id, age, group, seed))
    noise_rng = random.Random(stable_seed(student_id, 'noise', seed))

    # 年龄组
    if age < 35:
        age_group = 'young_adult'
    elif age < 55:
        age_group = 'middle_adult'
    else:
        age_group = 'senior'

    # 初始分数
    initial = sample_initial_scores(age_group, rng)

    # 银发因子
    age_factor = 0.7 if age >= 60 else 1.0

    # 7 天轨迹
    daily_scores = [dict(initial)]  # day 0
    for day in range(1, days + 1):
        day_dict = {}
        for dim in ['pitch', 'expressiveness', 'hand_pose', 'rhythm', 'sight_reading']:
            curve = LEARNING_CURVE_TYPES[dim]
            current = daily_scores[-1][dim]
            new_val = apply_learning_curve(
                current, day, days, curve,
                treatment=(group == 'treatment'),
                age_factor=age_factor,
                noise_rng=noise_rng,
            )
            # 天花板
            new_val = min(MAX_SCORES[dim], max(0, new_val))
            day_dict[dim] = round(new_val, 1)
        daily_scores.append(day_dict)

    return {
        'student_id': student_id,
        'age': age,
        'age_group': age_group,
        'group': group,
        'initial_scores': initial,
        'daily_scores': daily_scores,
        'senior_mode_active': age >= 60,
    }


def generate_cohort(n_per_group: int = 30, days: int = 7, seed: int = 42) -> Dict:
    """生成完整 cohort (n_per_group control + n_per_group treatment)"""
    rng = random.Random(seed)
    students = []

    for i in range(n_per_group):
        # Control
        age_choices = [25, 30, 45] * 2 + [60, 70]
        age = rng.choice(age_choices)
        s = generate_student(
            student_id=f'c{i:03d}',
            age=age, group='control', days=days, seed=seed + i,
        )
        students.append(s)
    for i in range(n_per_group):
        # Treatment (相同 seed 派生,但 group=treatment 触发课程增益)
        age_choices = [25, 30, 45] * 2 + [60, 70]
        age = rng.choice(age_choices)
        s = generate_student(
            student_id=f't{i:03d}',
            age=age, group='treatment', days=days, seed=seed + i + 10000,
        )
        students.append(s)

    return {
        'config': {'n_per_group': n_per_group, 'days': days, 'seed': seed},
        'generated_at': datetime.now().isoformat(),
        'students': students,
    }


# === 真实化: 喂入 ab_test_harness ===

def cohort_to_ab_test(cohort_data: Dict) -> Tuple[List, List]:
    """从 cohort JSON 转换为 ab_test_harness 期望的 StudentCohort 列表"""
    sys.path.insert(0, str(Path(__file__).parent))
    from ab_test_harness import StudentCohort

    control, treatment = [], []
    for s in cohort_data['students']:
        sc = StudentCohort(
            student_id=s['student_id'],
            age=s['age'],
            initial_scores=s['initial_scores'],
            group=s['group'],
        )
        sc.daily_scores = s['daily_scores']
        if s['group'] == 'control':
            control.append(sc)
        else:
            treatment.append(sc)
    return control, treatment


def run_ab_test_with_real_data(cohort_data: Dict):
    """用真实化数据运行 A/B 测试"""
    from ab_test_harness import ABTestHarness, ReportGenerator
    control, treatment = cohort_to_ab_test(cohort_data)

    # Monkey-patch simulator 让它跳过模拟 (用已有 daily_scores)
    class _Replayer:
        def simulate_student(self, student, days=7):
            return student

    harness = ABTestHarness(
        n_per_group=len(control) + len(treatment),  # dummy
        days=7, simulator=_Replayer(), seed=42,
    )

    # 提取 pre/post
    dims = ['pitch', 'expressiveness', 'hand_pose', 'rhythm', 'sight_reading']
    result_data = {
        'n_control': len(control), 'n_treatment': len(treatment),
        'duration_days': 7, 'dimensions': dims,
        'control_pre': {d: [s.initial_scores[d] for s in control] for d in dims},
        'control_post': {d: [s.daily_scores[-1][d] for s in control] for d in dims},
        'treatment_pre': {d: [s.initial_scores[d] for s in treatment] for d in dims},
        'treatment_post': {d: [s.daily_scores[-1][d] for s in treatment] for d in dims},
    }

    # 用 ab_test_harness 的统计函数
    from ab_test_harness import ABTestResult
    result = ABTestResult(**result_data)

    # 计算 statistics + effect_sizes
    import math
    for dim in dims:
        c_pre, c_post = result_data['control_pre'][dim], result_data['control_post'][dim]
        t_pre, t_post = result_data['treatment_pre'][dim], result_data['treatment_post'][dim]
        c_gain = sum(c_post) / len(c_post) - sum(c_pre) / len(c_pre)
        t_gain = sum(t_post) / len(t_post) - sum(t_pre) / len(t_pre)

        n1, n2 = len(c_post), len(t_post)
        m1, m2 = sum(t_post) / n1, sum(c_post) / n2
        v1 = sum((x - m1) ** 2 for x in t_post) / (n1 - 1)
        v2 = sum((x - m2) ** 2 for x in c_post) / (n2 - 1)
        pooled_std = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
        d = (m1 - m2) / pooled_std if pooled_std > 0.001 else 0.0
        se = math.sqrt(v1 / n1 + v2 / n2)
        t_stat = (m1 - m2) / se if se > 0.001 else 0.0
        from ab_test_harness import welch_t_test
        _, p_value = welch_t_test(t_post, c_post)

        result.statistics[dim] = {
            'control_pre': round(sum(c_pre) / n1, 2),
            'control_post': round(sum(c_post) / n1, 2),
            'control_gain': round(c_gain, 2),
            'treatment_pre': round(sum(t_pre) / n2, 2),
            'treatment_post': round(sum(t_post) / n2, 2),
            'treatment_gain': round(t_gain, 2),
            'delta_gain': round(t_gain - c_gain, 2),
            'improvement_ratio': round(t_gain / c_gain, 2) if c_gain > 0.01 else 0,
            't_stat': round(t_stat, 3),
            'p_value': round(p_value, 4),
            'significant_005': p_value < 0.05,
            'significant_001': p_value < 0.01,
        }
        result.effect_sizes[dim] = round(d, 3)

    avg_d = sum(result.effect_sizes.values()) / len(result.effect_sizes)
    sig_count = sum(1 for s in result.statistics.values() if s['significant_005'])
    result.summary = (
        f"A/B 测试 (真实化数据): {result.n_control}+{result.n_treatment} × {result.duration_days} 天\n"
        f"平均效应量 Cohen's d = {avg_d:.3f}\n"
        f"显著维度 (p<0.05): {sig_count}/{len(dims)}\n"
    )
    return result


# === CLI ===

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--n', type=int, default=30, help='每组样本量')
    p.add_argument('--days', type=int, default=7, help='天数')
    p.add_argument('--seed', type=int, default=42, help='随机种子')
    p.add_argument('--output', default='notes/test_cohort.json', help='输出 JSON 路径')
    p.add_argument('--abtest', action='store_true', help='生成后直接跑 A/B 测试')
    p.add_argument('--pretty', action='store_true', help='美化 JSON 输出')
    args = p.parse_args()

    print(f"📊 CoPiano 测试数据生成器")
    print(f"   n={args.n}/group, days={args.days}, seed={args.seed}")

    cohort = generate_cohort(n_per_group=args.n, days=args.days, seed=args.seed)

    # 写 JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(cohort, ensure_ascii=False, indent=2 if args.pretty else None)
    )
    print(f"   ✅ {output_path.absolute()} ({output_path.stat().st_size / 1024:.1f} KB)")

    # 统计
    print(f"\n   学生统计:")
    print(f"     总数: {len(cohort['students'])}")
    ages = [s['age'] for s in cohort['students']]
    print(f"     年龄范围: {min(ages)}-{max(ages)}, 均值 {sum(ages)/len(ages):.1f}")
    seniors = sum(1 for s in cohort['students'] if s['age'] >= 60)
    print(f"     银发: {seniors}/{len(cohort['students'])} ({seniors/len(cohort['students'])*100:.0f}%)")

    if args.abtest:
        print("\n🧪 A/B 测试 (用真实化数据)...")
        result = run_ab_test_with_real_data(cohort)
        from ab_test_harness import ReportGenerator
        print(ReportGenerator.generate(result))


if __name__ == '__main__':
    main()
