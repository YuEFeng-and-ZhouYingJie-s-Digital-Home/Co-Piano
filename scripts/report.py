"""
report.py — CoPiano 评估报告生成器(把 copiano 输出变可读 Markdown)

输入:copiano.py 输出的 JSON(eval + align + style + llm_response)
输出:Markdown 报告(可打印 / 分享 / 归档)

报告结构:
1. 总览(score + 评价)
2. 评估详情(错音 / 节奏 / 力度)
3. 风格分析(调性 / 速度 / 时期)
4. 乐谱对齐(质量 + 关键点)
5. 教学反馈(LLM 生成)
6. 下一步建议(自动生成)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


def format_evaluation(eval_result: dict) -> str:
    score = eval_result.get("score", 0)
    if score >= 95:
        rating = "⭐ 优秀"
    elif score >= 85:
        rating = "✓ 良好"
    elif score >= 70:
        rating = "○ 中等"
    else:
        rating = "△ 待提升"
    out = f"""## 1. 总览

**总分: {score:.1f} / 100**  {rating}

| 指标 | 数值 | 说明 |
|------|------|------|
| 错音准确率 | {eval_result.get('pitch_accuracy', 0):.1%} | {eval_result.get('n_pitch_errors', 0)} 个错音 |
| 节奏稳定性 | std {eval_result.get('timing_std_ms', 0):.1f}ms | {'稳定' if eval_result.get('timing_std_ms', 0) < 30 else '需改进'} |
| 节奏偏差 | {eval_result.get('timing_mean_ms', 0):+.1f}ms | {'略快' if eval_result.get('timing_mean_ms', 0) < -20 else '略慢' if eval_result.get('timing_mean_ms', 0) > 20 else '稳定'} |
| 力度相关性 | {eval_result.get('velocity_correlation', 0):.2f} | 0=无关联,1=完全跟随 |
| 完整度 | {eval_result.get('note_completeness', 0):.1%} | 漏音比例 |
"""
    return out


def format_style_analysis(style: dict) -> str:
    if "error" in style:
        return f"\n## 2. 风格分析\n\n(无法分析: {style['error']})\n"
    out = f"""## 2. 风格分析

| 维度 | 检测值 | 解读 |
|------|--------|------|
| 调性 | {style.get('key', '?')} | music21 自动检测 |
| 拍号 | {style.get('time_signature', '?')} | - |
| 速度 | {style.get('tempo_bpm', 0):.0f} BPM | {'偏快' if style.get('tempo_bpm', 0) > 140 else '偏慢' if style.get('tempo_bpm', 0) < 70 else '适中'} |
| 音域 | {style.get('pitch', {}).get('min', 0):.0f} - {style.get('pitch', {}).get('max', 0):.0f} ({style.get('pitch', {}).get('range_semitones', 0):.0f} 半音) | {'宽' if style.get('pitch', {}).get('range_semitones', 0) > 40 else '窄'} |
| 力度 std | {style.get('velocity', {}).get('std', 0):.1f} | {'变化大' if style.get('velocity', {}).get('std', 0) > 20 else '均匀'} |
| 音符密度 | {style.get('texture', {}).get('note_density_per_sec', 0):.1f}/s | {'密集' if style.get('texture', {}).get('note_density_per_sec', 0) > 8 else '稀疏'} |
| 同时发声音 | {style.get('texture', {}).get('max_simultaneous_notes', 0)} | 多声部织体 |

**时期线索**: {style.get('period_hint', '?')} (置信度 {style.get('period_confidence', 0):.2f})

**风格提示**:
"""
    for h in style.get("style_hints", []):
        out += f"- {h}\n"
    return out


def format_alignment(align: dict) -> str:
    if "error" in align:
        return f"\n## 3. 乐谱对齐\n\n(无法对齐: {align['error']})\n"
    out = f"""## 3. 乐谱对齐

| 指标 | 数值 | 解读 |
|------|------|------|
| 对齐点 | {align.get('n_alignment_points', 0)} | DTW 路径点数 |
| 对齐质量 | {align.get('alignment_quality', 0):.4f} | 越低越好 |
| 乐谱时长 | {align.get('score_duration_s', 0):.1f}s | - |
| 演奏时长 | {align.get('perf_duration_s', 0):.1f}s | {'与乐谱同步' if abs(align.get('score_duration_s', 0) - align.get('perf_duration_s', 0)) < 1 else '有偏差'} |

**前 5 个对齐点**:
| 乐谱时间 (s) | 演奏时间 (s) | 偏差 (s) |
|--------------|--------------|----------|
"""
    points = align.get("first_5_alignment", [])
    for p in points:
        diff = p["perf_time_s"] - p["score_time_s"]
        out += f"| {p['score_time_s']:.3f} | {p['perf_time_s']:.3f} | {diff:+.3f} |\n"
    return out


def format_feedback(llm_response: str) -> str:
    return f"""## 4. 教学反馈 (AI 老师)

> {llm_response}

---
*由 Qwen 2.5-7B-Instruct 生成 · 基于乐理知识图谱 RAG + MIDI 自动评估*
"""


def format_cluster(copiano_result: dict) -> str:
    """如果跑了 --cluster-history,展示聚类结果"""
    cluster = copiano_result.get("cluster")
    if not cluster:
        return ""
    n_clusters = cluster.get("n_clusters", 0)
    sil = cluster.get("silhouette_score", 0)
    method = cluster.get("method", "kmeans")
    out = f"""
## 4.7 错误模式聚类 (Phase 3 自适应)

**方法**: {method} | **簇数**: K={n_clusters} | **轮廓系数**: {sil} ({'良好' if sil > 0.5 else '中等' if sil > 0.3 else '一般'})

| 曲目 | 簇 ID | 错误画像 |
|------|-------|----------|
"""
    for rec in cluster.get("recommendations", []):
        out += f"| {rec['piece']} | {rec['cluster_id']} | {rec['profile_name']} |\n"
    return out


def format_recommend(copiano_result: dict) -> str:
    """如果跑了 --recommend,展示推荐"""
    recs = copiano_result.get("recommendations", [])
    if not recs:
        return ""
    out = f"""
## 4.8 下一步推荐 (Phase 3 自适应)

基于你的错误模式聚类,推荐下一首练习(由 Contextual Bandit 算法生成):

| # | 曲目 | 作曲家 | 难度 | 时期 | UCB 评分 |
|---|------|--------|------|------|----------|
"""
    for i, r in enumerate(recs, 1):
        score = r["ucb_score"]
        score_str = f"{score}" if isinstance(score, (int, float)) else str(score)
        out += f"| {i} | {r['piece']} | {r['composer']} | {r['difficulty']} | {r['period']} | {score_str} |\n"

    out += "\n**推荐理由**:\n"
    for i, r in enumerate(recs, 1):
        out += f"- {r['piece']}: {r['reason']}\n"
    return out


def format_practice_suggestion(eval_result: dict, style: dict, piece: dict) -> str:
    """自动生成下一步练习建议"""
    score = eval_result.get("score", 0)
    n_errors = eval_result.get("n_pitch_errors", 0)
    timing_std = eval_result.get("timing_std_ms", 0)
    period = piece.get("period", "Classical")

    suggestions = []
    if n_errors > 0:
        suggestions.append(f"🎯 **重点攻错音**: 本次有 {n_errors} 个错音,建议在小节级别重练这些点,先慢速 60 BPM 准后再加速")
    if timing_std > 50:
        suggestions.append("⏱️ **节奏训练**: 用节拍器从 60 BPM 练起,先稳定 8 小节无错,再加速到原速")
    if score >= 90:
        suggestions.append(f"📈 **进阶**: 已达 {score:.0f} 分,可尝试下一首(难度 +1),或同一首的更深表现力版本")
    if period == "Baroque":
        suggestions.append("🎼 **风格提示**: 巴洛克作品注意装饰音(trill/mordent)的时值与各声部独立")
    elif period == "Classical":
        suggestions.append("🎼 **风格提示**: 古典作品注意触键颗粒感(legato/staccato 分明),避免过度 rubato")
    elif period == "Romantic":
        suggestions.append("🎼 **风格提示**: 浪漫作品注意大幅力度对比和踏板的精细控制")

    if not suggestions:
        suggestions.append("继续保持,尝试不同的乐曲风格")

    out = "## 5. 下一步建议\n\n"
    for s in suggestions:
        out += f"{s}\n\n"
    return out


def format_aggregation(copiano_result: dict) -> str:
    """如果用了 --aggregated,展示段落级聚合"""
    agg = copiano_result.get("aggregation")
    if not agg:
        return ""
    out = f"""
## 4.5 段落级聚合(全曲级)

**整体判断**: {agg.get('overall_judgment', '?')}

| 指标 | 数值 |
|------|------|
| 总小节数 | {agg.get('n_measures', 0)} |
| 平均分 | {agg.get('global', {}).get('avg_score', 0):.1f} |
| 最低分 | {agg.get('global', {}).get('min_score', 0):.1f} |
| 最高分 | {agg.get('global', {}).get('max_score', 0):.1f} |
| 总错音 | {agg.get('global', {}).get('total_errors', 0)} |

**错音热点 TOP 3**:
"""
    for h in agg.get("error_hotspots", [])[:3]:
        out += f"- 小节 {h['measure']}: {h['n_errors']} 错音 (score {h['score']})\n"

    out += "\n**弱项小节**:\n"
    for w in agg.get("weak_measures", []):
        out += f"- 小节 {w['measure']}: score {w['score']}\n"

    agg_resp = copiano_result.get("aggregated_llm_response", "")
    if agg_resp:
        out += f"\n**AI 综合反馈(全曲级)**:\n\n> {agg_resp}\n"

    return out
    for s in suggestions:
        out += f"{s}\n\n"
    return out


def generate_report(copiano_result: dict) -> str:
    """主函数:从 copiano JSON 生成 Markdown 报告"""
    eval_r = copiano_result.get("eval", {})
    style_r = copiano_result.get("style", {})
    align_r = copiano_result.get("align", {})
    piece = copiano_result.get("piece", {})
    llm = copiano_result.get("llm_response", "")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    header = f"""# CoPiano 评估报告

**曲目**: {piece.get('name', '?')} ({piece.get('composer', '?')})
**时期**: {piece.get('period', '?')} | **难度**: {piece.get('difficulty', '?')}
**生成时间**: {now}

---
"""
    body = (
        format_evaluation(eval_r)
        + "\n"
        + format_style_analysis(style_r)
        + "\n"
        + format_alignment(align_r)
        + "\n"
        + (format_feedback(llm) if llm else "\n## 4. 教学反馈\n\n(LLM 未调用,使用 --no-llm 模式)\n")
        + "\n"
        + format_aggregation(copiano_result)
        + "\n"
        + format_cluster(copiano_result)
        + "\n"
        + format_recommend(copiano_result)
        + "\n"
        + format_practice_suggestion(eval_r, style_r, piece)
    )

    footer = """
---

*本报告由 CoPiano 自动生成。CoPiano 是一个 AI 古典钢琴教练,基于 MIDI 自动评估 + 乐理知识图谱 + 大语言模型。*
*项目位置: `~/piano-ai-corpus/`*
"""

    return header + body + footer


def main():
    if len(sys.argv) < 2:
        print("Usage: report.py <copiano_result.json> [output.md]", file=sys.stderr)
        return 1
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".md")
    data = json.loads(src.read_text(encoding="utf-8"))
    md = generate_report(data)
    out.write_text(md, encoding="utf-8")
    print(f"✓ Report written: {out} ({len(md)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
