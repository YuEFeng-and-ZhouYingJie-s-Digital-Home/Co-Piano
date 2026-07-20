"""
ab_test_harness.py — CoPiano 课程效果 A/B 测试框架

Cycle 8 Stage 2 实现:
- CohortSimulator: 模拟学生 7 天 5 维分数变化
- ABTestHarness: control (无课程) vs treatment (curriculum_v2)
- MetricsCollector: 5 维分数 + 派生指标
- StatsAnalyzer: Cohen's d + t-test (pure Python) + p-value
- ReportGenerator: markdown 报告

调研依据: notes/market_knowledge_cycle8.md
对位: RCT 金标准 + Kulik & Fletcher 2016 meta-analysis (ITS 效应量 d=0.41)
"""

import hashlib
import json
import math
import random
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


# === 学习效应模型 ===

# 默认每维度的"自然学习率" (无课程) + "课程增益" (有课程)
DEFAULT_LEARNING_RATES = {
    'pitch':           {'natural': 0.3, 'curriculum': 0.8},   # 音准:课程提升 2.7x
    'expressiveness':  {'natural': 0.2, 'curriculum': 0.6},   # 表现力:3x
    'hand_pose':       {'natural': 0.4, 'curriculum': 0.9},   # 手型:2.25x
    'rhythm':          {'natural': 0.5, 'curriculum': 0.8},   # 节奏:1.6x
    'sight_reading':   {'natural': 0.1, 'curriculum': 0.5},   # 视奏:5x
}

# 银发:更慢
SENIOR_LEARNING_RATES = {
    'pitch':           {'natural': 0.2, 'curriculum': 0.5},
    'expressiveness':  {'natural': 0.1, 'curriculum': 0.4},
    'hand_pose':       {'natural': 0.3, 'curriculum': 0.7},
    'rhythm':          {'natural': 0.4, 'curriculum': 0.6},
    'sight_reading':   {'natural': 0.05, 'curriculum': 0.3},
}

# 噪声 (天间方差)
DEFAULT_NOISE_STD = 2.5


# === 数据类 ===

@dataclass
class StudentCohort:
    """单学生 (cohort 内)"""
    student_id: str
    age: int = 30
    initial_scores: Dict[str, float] = field(default_factory=dict)
    group: str = 'control'  # 'control' or 'treatment'
    daily_scores: List[Dict[str, float]] = field(default_factory=list)  # 7 天

    def __post_init__(self):
        if not self.initial_scores:
            self.initial_scores = {
                'pitch': 70.0,
                'expressiveness': 65.0,
                'hand_pose': 75.0,
                'rhythm': 80.0,
                'sight_reading': 60.0,
            }


@dataclass
class ABTestResult:
    """A/B 测试完整结果"""
    n_control: int
    n_treatment: int
    duration_days: int
    dimensions: List[str]
    control_pre: Dict[str, List[float]]   # dim → [n_control 个 pre 分数]
    control_post: Dict[str, List[float]]
    treatment_pre: Dict[str, List[float]]
    treatment_post: Dict[str, List[float]]
    statistics: Dict[str, dict] = field(default_factory=dict)  # dim → {mean_pre/mean_post/d/p/...}
    effect_sizes: Dict[str, float] = field(default_factory=dict)  # dim → Cohen's d
    summary: str = ''

    def to_dict(self):
        return asdict(self)


# === CohortSimulator ===

class CohortSimulator:
    """模拟学生 7 天学习进度"""

    def __init__(self, learning_rates: Dict = None, noise_std: float = DEFAULT_NOISE_STD, seed: int = None):
        self.learning_rates = learning_rates or DEFAULT_LEARNING_RATES
        self.noise_std = noise_std
        self.seed = seed

    def simulate_student(self, student: StudentCohort, days: int = 7) -> StudentCohort:
        """模拟单个学生 7 天进度"""
        if self.seed is not None:
            rng = random.Random(self.seed + hash(student.student_id) % 10000)
        else:
            rng = random.Random()

        # 初始分数
        current = dict(student.initial_scores)
        student.daily_scores = [dict(current)]  # day 0 = pre

        # 学习率
        if student.group == 'control':
            rates = {dim: cfg['natural'] for dim, cfg in self.learning_rates.items()}
        else:
            rates = {dim: cfg['curriculum'] for dim, cfg in self.learning_rates.items()}

        # 银发修正
        senior_factor = 0.7 if student.age >= 60 else 1.0

        # 模拟 7 天
        for day in range(1, days + 1):
            for dim in current:
                # 学习增益 + 噪声
                gain = rates[dim] * senior_factor
                noise = rng.gauss(0, self.noise_std)
                # 衰减 (有天花板 100,下界 0)
                current[dim] = max(0, min(100, current[dim] + gain + noise))
            student.daily_scores.append(dict(current))

        return student

    def simulate_cohort(self, students: List[StudentCohort], days: int = 7) -> List[StudentCohort]:
        """模拟整个 cohort"""
        return [self.simulate_student(s, days) for s in students]


# === ABTestHarness ===

class ABTestHarness:
    """A/B 测试主框架"""

    def __init__(self, n_per_group: int = 30, days: int = 7, simulator: CohortSimulator = None,
                 seed: int = 42):
        self.n_per_group = n_per_group
        self.days = days
        self.simulator = simulator or CohortSimulator(seed=seed)
        self.dimensions = list(DEFAULT_LEARNING_RATES.keys())

    def setup_cohorts(self) -> Tuple[List[StudentCohort], List[StudentCohort]]:
        """生成 control + treatment cohorts (随机分组)"""
        rng = random.Random(42)
        control = []
        treatment = []
        for i in range(self.n_per_group):
            # 50/50 混合成人+银发
            age = rng.choice([25, 30, 45, 60, 70]) if i % 3 == 0 else rng.choice([25, 30, 45])
            # 初始分数加入少量噪声 (避免完全相同)
            init = {
                'pitch': max(50, min(80, 70 + rng.gauss(0, 5))),
                'expressiveness': max(50, min(80, 65 + rng.gauss(0, 5))),
                'hand_pose': max(60, min(85, 75 + rng.gauss(0, 5))),
                'rhythm': max(60, min(90, 80 + rng.gauss(0, 5))),
                'sight_reading': max(50, min(75, 60 + rng.gauss(0, 5))),
            }
            student = StudentCohort(
                student_id=f's{i:03d}',
                age=age,
                initial_scores=init,
                group='control',
            )
            control.append(student)

        for i in range(self.n_per_group):
            age = rng.choice([25, 30, 45, 60, 70]) if i % 3 == 0 else rng.choice([25, 30, 45])
            init = {
                'pitch': max(50, min(80, 70 + rng.gauss(0, 5))),
                'expressiveness': max(50, min(80, 65 + rng.gauss(0, 5))),
                'hand_pose': max(60, min(85, 75 + rng.gauss(0, 5))),
                'rhythm': max(60, min(90, 80 + rng.gauss(0, 5))),
                'sight_reading': max(50, min(75, 60 + rng.gauss(0, 5))),
            }
            student = StudentCohort(
                student_id=f't{i:03d}',
                age=age,
                initial_scores=init,
                group='treatment',
            )
            treatment.append(student)
        return control, treatment

    def run(self) -> ABTestResult:
        """运行 A/B 测试"""
        control, treatment = self.setup_cohorts()
        # 模拟
        control = self.simulator.simulate_cohort(control, self.days)
        treatment = self.simulator.simulate_cohort(treatment, self.days)

        # 提取 pre/post 分数
        control_pre = {d: [s.initial_scores[d] for s in control] for d in self.dimensions}
        control_post = {d: [s.daily_scores[-1][d] for s in control] for d in self.dimensions}
        treatment_pre = {d: [s.initial_scores[d] for s in treatment] for d in self.dimensions}
        treatment_post = {d: [s.daily_scores[-1][d] for s in treatment] for d in self.dimensions}

        # 统计分析
        stats = {}
        effect_sizes = {}
        for dim in self.dimensions:
            c_pre = control_pre[dim]
            c_post = control_post[dim]
            t_pre = treatment_pre[dim]
            t_post = treatment_post[dim]

            # Control 增益
            c_gain = mean(c_post) - mean(c_pre)
            t_gain = mean(t_post) - mean(t_pre)

            # Treatment 增益
            delta_gain = t_gain - c_gain

            # 统计检验:t_post vs c_post (独立样本 t-test)
            t_stat, p_value = welch_t_test(t_post, c_post)
            # Cohen's d
            d = cohens_d(t_post, c_post)

            # Improvement ratio
            improvement = (t_gain / c_gain) if c_gain > 0.01 else float('inf') if t_gain > 0.01 else 1.0

            stats[dim] = {
                'control_pre': round(mean(c_pre), 2),
                'control_post': round(mean(c_post), 2),
                'control_gain': round(c_gain, 2),
                'treatment_pre': round(mean(t_pre), 2),
                'treatment_post': round(mean(t_post), 2),
                'treatment_gain': round(t_gain, 2),
                'delta_gain': round(delta_gain, 2),
                'improvement_ratio': round(improvement, 2) if improvement != float('inf') else 'inf',
                't_stat': round(t_stat, 3),
                'p_value': round(p_value, 4),
                'significant_005': p_value < 0.05,
                'significant_001': p_value < 0.01,
            }
            effect_sizes[dim] = round(d, 3)

        # 总结
        avg_d = mean(list(effect_sizes.values()))
        sig_count = sum(1 for s in stats.values() if s['significant_005'])
        summary = (
            f"A/B 测试完成: {self.n_per_group} per group × {self.days} 天\n"
            f"平均效应量 Cohen's d = {avg_d:.2f} ({effect_size_label(avg_d)})\n"
            f"显著维度 (p<0.05): {sig_count}/{len(self.dimensions)}\n"
        )

        return ABTestResult(
            n_control=self.n_per_group,
            n_treatment=self.n_per_group,
            duration_days=self.days,
            dimensions=self.dimensions,
            control_pre=control_pre,
            control_post=control_post,
            treatment_pre=treatment_pre,
            treatment_post=treatment_post,
            statistics=stats,
            effect_sizes=effect_sizes,
            summary=summary,
        )


# === 统计函数 (pure Python, no scipy) ===

def mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def variance(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = mean(values)
    return sum((x - m) ** 2 for x in values) / (len(values) - 1)


def std_dev(values: List[float]) -> float:
    return math.sqrt(variance(values))


def cohens_d(group1: List[float], group2: List[float]) -> float:
    """Cohen's d 效应量"""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0
    m1, m2 = mean(group1), mean(group2)
    s1, s2 = std_dev(group1), std_dev(group2)
    # 合并标准差
    pooled_std = math.sqrt(((n1 - 1) * s1 ** 2 + (n2 - 1) * s2 ** 2) / (n1 + n2 - 2))
    if pooled_std < 0.001:
        return 0.0
    return (m1 - m2) / pooled_std


def welch_t_test(group1: List[float], group2: List[float]) -> Tuple[float, float]:
    """Welch's t-test (不假设等方差)"""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0, 1.0
    m1, m2 = mean(group1), mean(group2)
    v1, v2 = variance(group1), variance(group2)
    se = math.sqrt(v1 / n1 + v2 / n2)
    if se < 0.001:
        return 0.0, 1.0
    t = (m1 - m2) / se
    # Welch-Satterthwaite 自由度
    df = (v1 / n1 + v2 / n2) ** 2 / (
        (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    )
    # p-value 近似 (双尾,大样本时用正态近似)
    # 使用学生 t 分布的 CDF 近似
    p = 2 * (1 - t_cdf(abs(t), df))
    return t, p


def t_cdf(t: float, df: float) -> float:
    """学生 t 分布 CDF 近似 (使用不完全 Beta 函数近似)"""
    if df <= 0:
        return 0.5
    # 用正态近似 (df > 30 时很准)
    if df > 30:
        return normal_cdf(t)
    # 否则用更粗糙的近似
    x = df / (df + t ** 2)
    # 不完全 beta 近似
    a, b = df / 2.0, 0.5
    return 1.0 - 0.5 * regularized_incomplete_beta(x, a, b)


def normal_cdf(z: float) -> float:
    """标准正态 CDF 近似 (Abramowitz & Stegun)"""
    if z < 0:
        return 1.0 - normal_cdf(-z)
    # 近似
    t = 1.0 / (1.0 + 0.2316419 * z)
    d = 0.3989422804014327  # 1/sqrt(2π)
    p = d * math.exp(-z * z / 2.0) * (
        t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    )
    return 1.0 - p


def regularized_incomplete_beta(x: float, a: float, b: float) -> float:
    """规则化不完全 Beta 函数 I_x(a, b) 近似 (简单连分式)"""
    if x < 0 or x > 1:
        return 0.0
    if x == 0 or x == 1:
        return x
    # 用连分式近似 (Lentz 算法简化版)
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * beta_cf(x, a, b) / a
    return 1.0 - front * beta_cf(1 - x, b, a) / b


def beta_cf(x: float, a: float, b: float, max_iter: int = 100, eps: float = 1e-10) -> float:
    """Beta 连分式"""
    qab = a + b
    qap = a + 1
    qam = a - 1
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def effect_size_label(d: float) -> str:
    """Cohen's d 标签"""
    d_abs = abs(d)
    if d_abs < 0.2:
        return 'negligible'
    elif d_abs < 0.5:
        return 'small'
    elif d_abs < 0.8:
        return 'medium'
    else:
        return 'large'


# === ReportGenerator ===

class ReportGenerator:
    """生成 markdown 报告"""

    @staticmethod
    def generate(result: ABTestResult) -> str:
        lines = [
            "# CoPiano 课程效果 A/B 测试报告",
            f"_生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
            f"_样本量: control n={result.n_control}, treatment n={result.n_treatment}_",
            f"_周期: {result.duration_days} 天_",
            "",
            "## 📊 测试结果摘要",
            "",
            result.summary,
            "",
            "## 📈 各维度分析",
            "",
        ]

        # 各维度表格
        lines.append("| 维度 | C-pre | C-post | C-gain | T-pre | T-post | T-gain | Δ gain | d | p | sig |")
        lines.append("|------|-------|--------|--------|-------|--------|--------|--------|-----|-----|-----|")
        for dim in result.dimensions:
            s = result.statistics[dim]
            d = result.effect_sizes[dim]
            sig = "**" if s['significant_001'] else ("*" if s['significant_005'] else "—")
            lines.append(
                f"| {dim} | {s['control_pre']:.1f} | {s['control_post']:.1f} | "
                f"{s['control_gain']:+.1f} | {s['treatment_pre']:.1f} | {s['treatment_post']:.1f} | "
                f"{s['treatment_gain']:+.1f} | {s['delta_gain']:+.1f} | {d:+.2f} | "
                f"{s['p_value']:.4f} | {sig} |"
            )

        # 解释
        lines.append("\n## 🔍 关键发现")
        lines.append("")
        # 找出最大效应量
        max_dim = max(result.effect_sizes, key=result.effect_sizes.get)
        max_d = result.effect_sizes[max_dim]
        lines.append(f"- **最大效应**: `{max_dim}` 维度 Cohen's d = {max_d:+.2f} ({effect_size_label(max_d)})")
        # 找出最显著
        sig_dims = [d for d, s in result.statistics.items() if s['significant_005']]
        if sig_dims:
            lines.append(f"- **统计显著 (p<0.05)**: {len(sig_dims)}/{len(result.dimensions)} 维度 — {', '.join(sig_dims)}")
        else:
            lines.append("- **统计显著 (p<0.05)**: 0 维度 (可能样本量不足或效应量过小)")
        # 平均提升
        avg_gain_ratio = mean([
            s['improvement_ratio'] for s in result.statistics.values()
            if isinstance(s['improvement_ratio'], (int, float))
        ]) if any(isinstance(s['improvement_ratio'], (int, float)) for s in result.statistics.values()) else 1.0
        lines.append(f"- **平均提升倍数**: {avg_gain_ratio:.2f}x (treatment vs control)")

        # 与文献对位
        lines.append("\n## 📚 文献对位 (Cohen's d)")
        lines.append("")
        lines.append("- Kulik & Fletcher 2016 meta-analysis: ITS 总体 d = 0.41 (medium)")
        lines.append("- Bloom 1985 (mastery learning): d = 0.75 (large)")
        lines.append(f"- **CoPiano 课程**: d = {mean(list(result.effect_sizes.values())):.2f}")
        lines.append("")

        # 结论
        avg_d = mean(list(result.effect_sizes.values()))
        if avg_d >= 0.5:
            lines.append("## ✅ 结论")
            lines.append("")
            lines.append(f"CoPiano 7 天多模态自适应课程显示出 **{effect_size_label(avg_d)} 效应** (d = {avg_d:.2f}),")
            lines.append("显著优于无课程对照组。推荐上线。")
        else:
            lines.append("## ⚠️ 结论")
            lines.append("")
            lines.append(f"CoPiano 课程显示出 **{effect_size_label(avg_d)} 效应** (d = {avg_d:.2f}),")
            lines.append("需要进一步优化或扩大样本量。")
        return '\n'.join(lines)


# === CLI ===

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--n', type=int, default=30, help='每组样本量')
    p.add_argument('--days', type=int, default=7, help='测试天数')
    p.add_argument('--seed', type=int, default=42, help='随机种子')
    p.add_argument('--demo', action='store_true', help='演示 (30 per group, 7 days)')
    p.add_argument('--json', action='store_true', help='JSON 输出')
    args = p.parse_args()

    if args.demo:
        n, days = 30, 7
    else:
        n, days = args.n, args.days

    sim = CohortSimulator(seed=args.seed)
    harness = ABTestHarness(n_per_group=n, days=days, simulator=sim, seed=args.seed)
    result = harness.run()

    if args.json:
        # JSON 不能包含 tuple
        out = result.to_dict()
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        report = ReportGenerator.generate(result)
        print(report)


if __name__ == '__main__':
    main()
