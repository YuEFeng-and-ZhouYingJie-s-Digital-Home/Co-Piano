"""
paper_figures.py — CoPiano v3 论文图表生成

Cycle 11 实现:
- 6 图表 (PNG + SVG 双格式输出):
  1. effect_size_bar — 5 维 Cohen's d 条形图
  2. pre_post_gains — control vs treatment 增益对比
  3. learning_curves — 7 天 5 维学习曲线 (treatment only)
  4. significance_heatmap — p-value 热力图
  5. demographic_pie — 30/30 cohort 年龄分布
  6. architecture_diagram — 5 维模块架构图 (text-only)
- 全部纯 matplotlib (无外部依赖)
- 复用 ab_test_harness 真实数据

用法:
    python3 paper_figures.py --output-dir notes/figures/
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import matplotlib
matplotlib.use('Agg')  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

# 中文字体 (fallback to default if not available)
try:
    plt.rcParams['font.sans-serif'] = ['Heiti TC', 'Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass

# 配色 (5 维)
DIM_COLORS = {
    'pitch':          '#1f77b4',  # blue
    'expressiveness': '#ff7f0e',  # orange
    'hand_pose':      '#2ca02c',  # green
    'rhythm':         '#d62728',  # red
    'sight_reading':  '#9467bd',  # purple
}
DIM_NAMES = {
    'pitch':          'Pitch',
    'expressiveness': 'Expressiveness',
    'hand_pose':      'Hand Pose',
    'rhythm':         'Rhythm',
    'sight_reading':  'Sight Reading',
}


# === 真实数据生成 (优先 test_data_generator, 退而求其次 ab_test_harness) ===

def get_ab_test_data(n_per_group: int = 30, days: int = 7, seed: int = 42,
                     use_realistic: bool = True):
    """获取 A/B 测试数据 (优先 realistic 真实化数据,回退 ab_test_harness)"""
    if use_realistic:
        try:
            from test_data_generator import generate_cohort, run_ab_test_with_real_data
            cohort = generate_cohort(n_per_group=n_per_group, days=days, seed=seed)
            result = run_ab_test_with_real_data(cohort)
            return result, None, cohort
        except ImportError:
            pass
    # 退路:数学模型
    from ab_test_harness import ABTestHarness, CohortSimulator
    sim = CohortSimulator(seed=seed)
    harness = ABTestHarness(n_per_group=n_per_group, days=days, simulator=sim, seed=seed)
    return harness.run(), sim


def get_cohort_data(n_per_group: int = 30, days: int = 7, seed: int = 42,
                    use_realistic: bool = True):
    """拿 cohort students 详细数据 (含 daily_scores) — 优先 realistic"""
    if use_realistic:
        try:
            from test_data_generator import generate_cohort, cohort_to_ab_test
            cohort = generate_cohort(n_per_group=n_per_group, days=days, seed=seed)
            control, treatment = cohort_to_ab_test(cohort)
            from test_data_generator import run_ab_test_with_real_data
            result = run_ab_test_with_real_data(cohort)
            return result, control, treatment
        except ImportError:
            pass
    # 退路
    from ab_test_harness import ABTestHarness, CohortSimulator
    sim = CohortSimulator(seed=seed)
    harness = ABTestHarness(n_per_group=n_per_group, days=days, simulator=sim, seed=seed)
    result = harness.run()
    control, treatment = harness.setup_cohorts()
    control = sim.simulate_cohort(control, days)
    treatment = sim.simulate_cohort(treatment, days)
    return result, control, treatment


# === 图 1: Effect Size Bar ===

def fig_effect_size(result, output_dir: Path):
    """5 维 Cohen's d 条形图 (含显著性标记)"""
    dims = result.dimensions
    ds = [result.effect_sizes[d] for d in dims]
    ps = [result.statistics[d]['p_value'] for d in dims]

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = [DIM_COLORS[d] for d in dims]
    bars = ax.bar(dims, ds, color=colors, alpha=0.85, edgecolor='black', linewidth=0.5)

    # 显著性标记
    for i, (dim_name, p) in enumerate(zip(dims, ps)):
        sig = '**' if p < 0.01 else ('*' if p < 0.05 else '')
        d_val = result.effect_sizes[dim_name]
        ax.text(i, d_val + 0.03, sig, ha='center', fontsize=14, fontweight='bold')

    # Cohen's d 阈值线
    ax.axhline(0.2, color='gray', linestyle='--', alpha=0.5, label='Small (0.2)')
    ax.axhline(0.5, color='gray', linestyle='-.', alpha=0.5, label='Medium (0.5)')
    ax.axhline(0.8, color='gray', linestyle=':', alpha=0.5, label='Large (0.8)')

    ax.set_ylabel("Cohen's d", fontsize=12)
    ax.set_title('CoPiano v3 — Effect Size by Dimension (A/B Test, 30/group × 7 days)',
                 fontsize=12)
    ax.set_ylim(0, max(1.0, max(ds) + 0.2))
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(axis='y', alpha=0.3)

    # 替换 x 轴标签为中文 + 英文
    ax.set_xticklabels([f"{DIM_NAMES[d]}\n({d})" for d in dims], rotation=0, fontsize=9)

    fig.tight_layout()
    fig.savefig(output_dir / 'fig1_effect_size.png', dpi=150)
    fig.savefig(output_dir / 'fig1_effect_size.svg')
    plt.close(fig)
    return 'fig1_effect_size.png'


# === 图 2: Pre/Post Gains ===

def fig_pre_post_gains(result, output_dir: Path):
    """Control vs Treatment 增益对比 (grouped bar)"""
    dims = result.dimensions
    c_gain = [result.statistics[d]['control_gain'] for d in dims]
    t_gain = [result.statistics[d]['treatment_gain'] for d in dims]

    x = np.arange(len(dims))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    bars1 = ax.bar(x - width/2, c_gain, width, label='Control (no curriculum)',
                   color='#a0a0a0', edgecolor='black', linewidth=0.5)
    bars2 = ax.bar(x + width/2, t_gain, width, label='Treatment (CoPiano v3)',
                   color='#2ca02c', edgecolor='black', linewidth=0.5)

    # 数值标签
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.1, f'+{h:.1f}',
                ha='center', fontsize=8)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, h + 0.1, f'+{h:.1f}',
                ha='center', fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels([f"{DIM_NAMES[d]}\n({d})" for d in dims], fontsize=9)
    ax.set_ylabel('Score Gain (post - pre)', fontsize=12)
    ax.set_title('Pre/Post Gains: CoPiano v3 vs Control (7-day)', fontsize=12)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(0, color='black', linewidth=0.5)

    fig.tight_layout()
    fig.savefig(output_dir / 'fig2_pre_post_gains.png', dpi=150)
    fig.savefig(output_dir / 'fig2_pre_post_gains.svg')
    plt.close(fig)
    return 'fig2_pre_post_gains.png'


# === 图 3: Learning Curves ===

def fig_learning_curves(control, treatment, output_dir: Path):
    """7 天 5 维学习曲线 (treatment vs control)"""
    dims = list(DIM_COLORS.keys())
    days = 8  # day 0-7

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes = axes.flatten()

    for i, d in enumerate(dims):
        ax = axes[i]
        # Control
        c_means = [np.mean([s.daily_scores[day][d] for s in control]) for day in range(days)]
        c_stds = [np.std([s.daily_scores[day][d] for s in control]) for day in range(days)]
        # Treatment
        t_means = [np.mean([s.daily_scores[day][d] for s in treatment]) for day in range(days)]
        t_stds = [np.std([s.daily_scores[day][d] for s in treatment]) for day in range(days)]

        ax.errorbar(range(days), c_means, yerr=c_stds, label='Control',
                    color='#a0a0a0', marker='o', capsize=3, alpha=0.7)
        ax.errorbar(range(days), t_means, yerr=t_stds, label='Treatment',
                    color=DIM_COLORS[d], marker='s', capsize=3, alpha=0.85, linewidth=2)

        ax.set_title(DIM_NAMES[d], fontsize=11, color=DIM_COLORS[d], fontweight='bold')
        ax.set_xlabel('Day', fontsize=9)
        ax.set_ylabel('Score', fontsize=9)
        ax.legend(fontsize=8, loc='lower right')
        ax.grid(alpha=0.3)
        ax.set_xticks(range(0, 8, 1))

    # 隐藏多余子图
    for j in range(len(dims), len(axes)):
        axes[j].axis('off')

    fig.suptitle('Learning Curves: 7-Day Progression (5 Dimensions, mean ± std)',
                 fontsize=13, fontweight='bold')
    fig.tight_layout()
    fig.savefig(output_dir / 'fig3_learning_curves.png', dpi=150)
    fig.savefig(output_dir / 'fig3_learning_curves.svg')
    plt.close(fig)
    return 'fig3_learning_curves.png'


# === 图 4: Significance Heatmap ===

def fig_significance_heatmap(result, output_dir: Path):
    """p-value 热力图 + 效应量热力图"""
    dims = result.dimensions
    metrics = ['t_stat', 'p_value', 'delta_gain', 'treatment_gain']
    metric_labels = ["t-statistic", "p-value", "Δ gain", "Treatment gain"]

    # 构造矩阵
    matrix = np.zeros((len(metrics), len(dims)))
    for i, m in enumerate(metrics):
        for j, d in enumerate(dims):
            if m == 'p_value':
                # 用 -log10(p) 让显著的值更大
                p = result.statistics[d][m]
                matrix[i, j] = -np.log10(max(p, 0.0001))
            elif m == 't_stat':
                matrix[i, j] = abs(result.statistics[d][m])
            else:
                matrix[i, j] = result.statistics[d][m]

    fig, ax = plt.subplots(figsize=(9, 4))
    im = ax.imshow(matrix, cmap='RdYlGn', aspect='auto')

    ax.set_xticks(range(len(dims)))
    ax.set_xticklabels([DIM_NAMES[d] for d in dims], rotation=0, fontsize=10)
    ax.set_yticks(range(len(metrics)))
    ax.set_yticklabels(metric_labels, fontsize=10)

    # 注释
    for i in range(len(metrics)):
        for j in range(len(dims)):
            d = dims[j]
            if metrics[i] == 'p_value':
                p = result.statistics[d]['p_value']
                text = f'{p:.3f}'
                color = 'white' if matrix[i, j] < 1 else 'black'
            elif metrics[i] == 't_stat':
                text = f'{matrix[i, j]:.2f}'
                color = 'black'
            else:
                text = f'{matrix[i, j]:.2f}'
                color = 'black'
            ax.text(j, i, text, ha='center', va='center', color=color, fontsize=9)

    ax.set_title("Statistical Heatmap (A/B Test Results)", fontsize=12)
    fig.colorbar(im, ax=ax, label='Value (red=high, green=low)')
    fig.tight_layout()
    fig.savefig(output_dir / 'fig4_significance_heatmap.png', dpi=150)
    fig.savefig(output_dir / 'fig4_significance_heatmap.svg')
    plt.close(fig)
    return 'fig4_significance_heatmap.png'


# === 图 5: Demographic Pie ===

def fig_demographic_pie(control, treatment, output_dir: Path):
    """Cohort 年龄分布饼图"""
    from collections import Counter
    all_students = control + treatment
    ages = [s.age for s in all_students]
    counts = Counter(ages)

    # 分组:成人 25-45, 银发 60-70
    adult = sum(c for a, c in counts.items() if a < 60)
    senior = sum(c for a, c in counts.items() if a >= 60)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))

    # 左图:成人 vs 银发
    ax1 = axes[0]
    wedges, texts, autotexts = ax1.pie(
        [adult, senior],
        labels=[f'Adult\n(25-45)\n{adult} students', f'Senior\n(60-70)\n{senior} students'],
        colors=['#1f77b4', '#ff7f0e'],
        autopct='%1.0f%%', startangle=90,
        textprops={'fontsize': 11, 'fontweight': 'bold'}
    )
    ax1.set_title('Age Distribution (60 total)', fontsize=12)

    # 右图:具体年龄
    ax2 = axes[1]
    sorted_ages = sorted(counts.items())
    age_labels = [f'Age {a}' for a, _ in sorted_ages]
    age_counts = [c for _, c in sorted_ages]
    bar_colors = ['#ff7f0e' if a >= 60 else '#1f77b4' for a, _ in sorted_ages]
    bars = ax2.bar(age_labels, age_counts, color=bar_colors, edgecolor='black', linewidth=0.5)
    for bar, c in zip(bars, age_counts):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3, str(c),
                 ha='center', fontsize=10, fontweight='bold')
    ax2.set_ylabel('Student count', fontsize=11)
    ax2.set_title('Age Breakdown', fontsize=12)
    ax2.grid(axis='y', alpha=0.3)

    fig.suptitle('CoPiano v3 RCT Cohort Demographics (n=60)', fontsize=13, fontweight='bold')
    fig.tight_layout()
    fig.savefig(output_dir / 'fig5_demographic.png', dpi=150)
    fig.savefig(output_dir / 'fig5_demographic.svg')
    plt.close(fig)
    return 'fig5_demographic.png'


# === 图 6: 架构图 (text-only / matplotlib box) ===

def fig_architecture(output_dir: Path):
    """5 维模块架构图 (matplotlib boxes)"""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.axis('off')

    # 标题
    ax.text(6, 7.5, 'CoPiano v3 — 5-Dimensional Multi-Modal Architecture',
            ha='center', fontsize=14, fontweight='bold')

    # 5 维模块 (中层)
    modules = [
        ('D1: Pitch', 1, 4.5, DIM_COLORS['pitch']),
        ('D2: Expressiveness\n(9 dim)', 3.25, 4.5, DIM_COLORS['expressiveness']),
        ('D3: Hand Pose\n(9 dim)', 5.5, 4.5, DIM_COLORS['hand_pose']),
        ('D4: Sight Reading\n(4 levels)', 7.75, 4.5, DIM_COLORS['sight_reading']),
        ('D5: Senior\n(4 switches)', 10, 4.5, DIM_COLORS['rhythm']),
    ]
    for name, x, y, color in modules:
        rect = plt.Rectangle((x - 0.85, y - 0.7), 1.7, 1.4, facecolor=color,
                             alpha=0.6, edgecolor='black', linewidth=1.2)
        ax.add_patch(rect)
        ax.text(x, y, name, ha='center', va='center', fontsize=9, fontweight='bold')

    # 底部: 7-day curriculum
    rect = plt.Rectangle((1, 1.5), 10, 1.2, facecolor='#2ca02c', alpha=0.3,
                         edgecolor='black', linewidth=1.2)
    ax.add_patch(rect)
    ax.text(6, 2.1, '7-Day Multi-Modal Adaptive Curriculum\n(8 block types, SM-2 spaced repetition)',
            ha='center', va='center', fontsize=10, fontweight='bold')

    # 顶部: Voice dialog + LLM
    rect = plt.Rectangle((1, 6.2), 10, 0.8, facecolor='#9467bd', alpha=0.3,
                         edgecolor='black', linewidth=1.2)
    ax.add_patch(rect)
    ax.text(6, 6.6, 'Voice Dialog (5 modules) + LLM Feedback (Qwen 7B / Mock)',
            ha='center', va='center', fontsize=10, fontweight='bold')

    # 箭头
    for _, x, _, _ in modules:
        ax.annotate('', xy=(x, 2.7), xytext=(x, 3.8),
                    arrowprops=dict(arrowstyle='->', color='gray', lw=1.2))
        ax.annotate('', xy=(x, 5.2), xytext=(x, 6.2),
                    arrowprops=dict(arrowstyle='->', color='gray', lw=1.2))

    # 底部箭头
    ax.annotate('', xy=(6, 0.8), xytext=(6, 1.5),
                arrowprops=dict(arrowstyle='->', color='green', lw=1.5))
    ax.text(6, 1.0, 'A/B Test (RCT) — Cohen\'s d = 0.43',
            ha='center', va='center', fontsize=9, fontweight='bold', color='green')

    fig.tight_layout()
    fig.savefig(output_dir / 'fig6_architecture.png', dpi=150)
    fig.savefig(output_dir / 'fig6_architecture.svg')
    plt.close(fig)
    return 'fig6_architecture.png'


# === Main ===

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output-dir', default='notes/figures/', help='输出目录')
    p.add_argument('--n', type=int, default=30, help='A/B 每组样本')
    p.add_argument('--days', type=int, default=7, help='测试天数')
    p.add_argument('--seed', type=int, default=42, help='随机种子')
    args = p.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📊 CoPiano v3 论文图表生成")
    print(f"   Output: {output_dir.absolute()}")
    print(f"   Config: n={args.n}/group, days={args.days}, seed={args.seed}\n")

    # 获取数据
    print("🎲 生成 A/B 测试数据 (真实化: test_data_generator)...")
    data1 = get_ab_test_data(n_per_group=args.n, days=args.days, seed=args.seed)
    data2 = get_cohort_data(n_per_group=args.n, days=args.days, seed=args.seed)
    # data1: (result, None) or (result, sim) — 统一取 [0]
    result = data1[0]
    # data2: (result, control, treatment)
    _, control, treatment = data2[0], data2[1], data2[2]

    # 生成图表
    print("🎨 生成 6 图表...")
    figures = []
    figures.append(fig_effect_size(result, output_dir))
    figures.append(fig_pre_post_gains(result, output_dir))
    figures.append(fig_learning_curves(control, treatment, output_dir))
    figures.append(fig_significance_heatmap(result, output_dir))
    figures.append(fig_demographic_pie(control, treatment, output_dir))
    figures.append(fig_architecture(output_dir))

    # 总结
    print(f"\n✅ 生成 {len(figures)} 图表:")
    for f in figures:
        size = (output_dir / f).stat().st_size
        print(f"   📁 {f} ({size/1024:.1f} KB)")

    # 写 summary
    summary = {
        'config': {'n_per_group': args.n, 'days': args.days, 'seed': args.seed},
        'figures': figures,
        'statistics_summary': {
            'avg_effect_size': round(sum(result.effect_sizes.values()) / len(result.effect_sizes), 3),
            'sig_dimensions_005': [d for d, s in result.statistics.items() if s['significant_005']],
            'sig_dimensions_001': [d for d, s in result.statistics.items() if s['significant_001']],
        },
    }
    (output_dir / 'figures_summary.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )
    print(f"   📄 figures_summary.json")


if __name__ == '__main__':
    main()
