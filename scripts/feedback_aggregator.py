"""
feedback_aggregator.py — 多小节反馈聚合器(L3 自适应推荐 + L4 增强)

对位论文:
- 2501.10222 Integrated Expressive Piano(综合表现力)
- 2511.03425 SyMuPe Affective Symbolic(情感可控)

设计:
- 输入:多个小节的 eval_pitch 结果(数组)
- 中间:聚合统计 + 错误模式聚类
  - 错音热点(哪个小节错最多)
  - 节奏稳定性(全局 std)
  - 力度曲线(各小节力度变化)
  - 弱项识别(最低分小节)
- 输出:综合 prompt(段落级 + 全曲级)
  - 段落反馈:针对弱项小节的具体建议
  - 全曲反馈:整体表现总结 + 下一步推荐
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path
from typing import Optional


def aggregate_measures(measure_results: list[dict]) -> dict:
    """聚合多小节评估结果"""
    if not measure_results:
        return {"error": "no measures"}

    # 1. 全局统计
    scores = [m.get("score", 0) for m in measure_results]
    pitch_acc = [m.get("pitch_accuracy", 0) for m in measure_results]
    timing_std = [m.get("timing_std_ms", 0) for m in measure_results]
    timing_mean = [m.get("timing_mean_ms", 0) for m in measure_results]
    n_errors = [m.get("n_pitch_errors", 0) for m in measure_results]

    # 2. 错音热点(错最多的小节)
    error_hotspots = []
    for i, m in enumerate(measure_results):
        if m.get("n_pitch_errors", 0) > 0:
            error_hotspots.append({
                "measure": i + 1,
                "n_errors": m["n_pitch_errors"],
                "score": m.get("score", 0),
                "errors": m.get("pitch_error_samples", [])[:3],
            })
    error_hotspots.sort(key=lambda x: -x["n_errors"])

    # 3. 弱项小节(score 最低 3 个)
    weak_measures = sorted(measure_results, key=lambda m: m.get("score", 100))[:3]
    weak_measures = [
        {"measure": i + 1, "score": m.get("score", 0), "errors": m.get("n_pitch_errors", 0)}
        for i, m in enumerate(weak_measures)
    ]

    # 4. 强项小节(score 最高 3 个)
    strong_measures = sorted(measure_results, key=lambda m: -m.get("score", 0))[:3]
    strong_measures = [
        {"measure": i + 1, "score": m.get("score", 0)}
        for i, m in enumerate(strong_measures)
    ]

    # 5. 节奏稳定性趋势
    timing_trend = {
        "mean_ms": round(statistics.mean(timing_mean), 1) if timing_mean else 0,
        "std_ms": round(statistics.mean(timing_std), 1) if timing_std else 0,
        "drift": "speeding up" if timing_mean and timing_mean[-1] < timing_mean[0] else "slowing down" if timing_mean else "unknown",
    }

    # 6. 整体判断
    avg_score = statistics.mean(scores) if scores else 0
    if avg_score >= 95:
        overall = "优秀,可进入下一首"
    elif avg_score >= 85:
        overall = "良好,小幅修正后即可"
    elif avg_score >= 70:
        overall = "中等,需重点突破弱项"
    else:
        overall = "基础阶段,建议降速重练"

    return {
        "n_measures": len(measure_results),
        "global": {
            "avg_score": round(avg_score, 1),
            "min_score": round(min(scores), 1) if scores else 0,
            "max_score": round(max(scores), 1) if scores else 0,
            "avg_pitch_accuracy": round(statistics.mean(pitch_acc), 3) if pitch_acc else 0,
            "total_errors": sum(n_errors),
        },
        "error_hotspots": error_hotspots[:3],
        "weak_measures": weak_measures,
        "strong_measures": strong_measures,
        "timing_trend": timing_trend,
        "overall_judgment": overall,
    }


def build_aggregated_prompt(agg: dict, piece_meta: dict) -> dict:
    """根据聚合结果生成综合 prompt"""
    if "error" in agg:
        return {"error": agg["error"]}

    system = "你是一位有 30 年经验的古典钢琴教师。你刚听完整首曲子,现在给出一份段落级 + 全曲级的综合反馈。"
    user = f"""## 教学场景
学生刚完成:{piece_meta.get('name', '练习曲')}({piece_meta.get('composer', 'Unknown')},{piece_meta.get('period', 'Classical')})
总小节数:{agg['n_measures']}
整体判断:**{agg['overall_judgment']}**

## 全曲统计
- 平均分:{agg['global']['avg_score']} / 100(范围 {agg['global']['min_score']}-{agg['global']['max_score']})
- 平均错音率:{agg['global']['avg_pitch_accuracy']:.1%}
- 总错音数:{agg['global']['total_errors']}
- 节奏趋势:{agg['timing_trend']['drift']}(均值 {agg['timing_trend']['mean_ms']:+.1f}ms, 稳定性 std {agg['timing_trend']['std_ms']:.1f}ms)

## 错音热点 TOP 3
{chr(10).join([f"  - 小节 {h['measure']}: {h['n_errors']} 个错音(score {h['score']})" for h in agg['error_hotspots'][:3]]) or '  (无)'}

## 弱项小节 TOP 3
{chr(10).join([f"  - 小节 {w['measure']}: score {w['score']}, {w['errors']} 错音" for w in agg['weak_measures']])}

## 强项小节 TOP 3
{chr(10).join([f"  - 小节 {s['measure']}: score {s['score']}" for s in agg['strong_measures']])}

## 你的任务
写一份 250-400 字的综合反馈,分三段:
1. **肯定**(100 字):突出强项小节,具体到哪段做得好
2. **改进建议**(150 字):针对错音热点和弱项小节,具体到小节号和原因
3. **下一步推荐**(100 字):根据整体判断,推荐下一步(继续精炼 / 改练其他小节 / 进入新曲)
"""
    return {"system": system, "user": user}


def main():
    """演示:从 test_ref vs test_user 生成模拟多小节评估"""
    # 模拟 8 个小节(实际应用应跑多遍)
    import subprocess
    r = subprocess.run(
        ["python3", str(Path(__file__).parent / "eval_pitch.py"),
         "/tmp/test_ref.mid", "/tmp/test_user.mid"],
        capture_output=True, text=True, cwd=str(Path(__file__).parent.parent)
    )
    if r.returncode != 0:
        print(f"eval_pitch failed: {r.stderr}")
        return 1
    base = json.loads(r.stdout)

    # 模拟 8 个小节,每小节 score 略不同
    measure_results = []
    for i in range(8):
        m = dict(base)
        m["measure"] = i + 1
        # 前 4 小节错得多,后 4 稳定
        m["score"] = base["score"] - i * 1.5 if i < 4 else base["score"] + (i - 4) * 0.5
        m["n_pitch_errors"] = 1 if i < 4 else 0
        m["pitch_error_samples"] = base.get("pitch_error_samples", []) if i < 4 else []
        measure_results.append(m)

    piece = {
        "name": "Minuet in G",
        "composer": "Bach",
        "period": "Baroque",
    }

    agg = aggregate_measures(measure_results)
    prompt = build_aggregated_prompt(agg, piece)

    print("=== AGGREGATION RESULT ===")
    print(json.dumps(agg, indent=2, ensure_ascii=False))
    print("\n=== AGGREGATED PROMPT ===")
    print("SYSTEM:", prompt["system"])
    print("\nUSER:", prompt["user"])

    # 导出
    out = Path(__file__).parent.parent / "notes" / "feedback_aggregator_demo.json"
    out.write_text(json.dumps({
        "aggregation": agg,
        "prompt": prompt,
        "piece": piece,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ 导出到 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
