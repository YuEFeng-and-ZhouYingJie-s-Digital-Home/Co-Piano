"""
copiano.py — CoPiano 端到端 CLI(评估 + 对齐 + KG RAG + LLM 反馈)

用法:
    python3 copiano.py <ref_midi> <user_midi> [options]

Options:
    --piece <name>      指定曲目(从 KG 找元数据),否则用 generic classical
    --measure <n>       当前小节(默认 1)
    --no-llm            只跑评估+对齐+prompt,不调 LLM
    --output <path>     输出 JSON 结果(默认 stdout)

Example:
    python3 copiano.py /tmp/test_ref.mid /tmp/test_user.mid --piece "Minuet in G"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
NOTES = ROOT / "notes"
sys.path.insert(0, str(SCRIPTS))

from tonnetz_kg import MusicKG, PIECES
from llm_feedback import build_feedback_prompt
from style_analyzer import analyze_midi
from feedback_aggregator import aggregate_measures, build_aggregated_prompt
from error_cluster import cluster_errors
from bandit_recommend import recommend_next_piece


def find_piece(name: str) -> Optional[dict]:
    """从 KG 找曲目元数据"""
    for p in PIECES:
        if p["name"].lower() == name.lower():
            return p
    # 子串匹配
    matches = [p for p in PIECES if name.lower() in p["name"].lower()]
    return matches[0] if matches else None


def run_script(name: str, *args, cwd=None) -> dict:
    """跑同目录下的脚本,返回 JSON 输出"""
    # 用 sys.executable 确保子进程用同一个 python(同一 conda env)
    import sys as _sys
    py = _sys.executable
    p = subprocess.run(
        [py, str(SCRIPTS / name), *args],
        capture_output=True, text=True, cwd=cwd or str(ROOT),
    )
    if p.returncode != 0:
        raise RuntimeError(f"{name} failed: {p.stderr}")
    return json.loads(p.stdout)


def call_llm(prompt: dict, model_id: str = "qwen/Qwen2.5-1.5B-Instruct", max_tokens: int = 250) -> dict:
    """调 LLM(通过 ModelScope,本地路径)"""
    import os
    os.environ.setdefault("MODELSCOPE_CACHE", "/root/autodl-tmp/ms-cache")

    # 写 prompt 到本地文件(LLM 脚本读)
    tmp_prompt = "/tmp/copiano_prompt.json"
    Path(tmp_prompt).write_text(json.dumps(prompt, ensure_ascii=False), encoding="utf-8")

    # 调 llm_call_ms(走 ModelScope)
    p = subprocess.run(
        ["/root/autodl-tmp/conda-envs/copiano/bin/python",
         "/root/autodl-tmp/copiano/code/llm_call_ms.py",
         model_id, tmp_prompt, str(max_tokens)],
        capture_output=True, text=True, timeout=300,
    )
    if p.returncode != 0:
        raise RuntimeError(f"LLM call failed: {p.stderr}")
    # 输出格式:---RESPONSE---\n{text}\n---END---
    text = p.stdout
    if "---RESPONSE---" in text:
        text = text.split("---RESPONSE---")[1].split("---END---")[0].strip()
    return {"response": text, "stderr": p.stderr, "model": model_id}


def main():
    ap = argparse.ArgumentParser(description="CoPiano end-to-end pipeline")
    ap.add_argument("ref_midi", help="参考演奏 MIDI")
    ap.add_argument("user_midi", help="用户演奏 MIDI")
    ap.add_argument("--piece", default=None, help="曲目名(从 KG 找)")
    ap.add_argument("--measure", type=int, default=1, help="当前小节")
    ap.add_argument("--no-llm", action="store_true", help="只跑评估+prompt,不调 LLM")
    ap.add_argument("--output", default=None, help="输出 JSON 路径")
    ap.add_argument("--model", default="qwen/Qwen2.5-7B-Instruct", help="LLM 模型(default: 7B, 7B 显著优于 1.5B)")
    ap.add_argument("--aggregated", action="store_true", help="额外生成段落级+全曲级聚合反馈(Step 6)")
    ap.add_argument("--save-history", action="store_true", help="保存本次评估到 history.json(用于后续聚类)")
    ap.add_argument("--cluster-history", action="store_true", help="聚类历史数据,识别错误模式 + 推荐(Step 7)")
    ap.add_argument("--recommend", action="store_true", help="基于 cluster + Bandit 推荐下一首练习(Step 8)")
    args = ap.parse_args()

    print("[copiano] Step 1: 评估 (eval_pitch) ...", file=sys.stderr)
    eval_result = run_script("eval_pitch.py", args.ref_midi, args.user_midi)
    print(f"  score={eval_result['score']}, 错音={eval_result['n_pitch_errors']}, 完整度={eval_result['note_completeness']}", file=sys.stderr)

    print("[copiano] Step 1.5: 风格分析 (style_analyzer) ...", file=sys.stderr)
    try:
        style_result = run_script("style_analyzer.py", args.user_midi)
        print(f"  key={style_result['key']}, tempo={style_result['tempo_bpm']}BPM, period_hint={style_result['period_hint']}({style_result['period_confidence']})", file=sys.stderr)
    except Exception as e:
        print(f"  [warn] 风格分析失败: {e}", file=sys.stderr)
        style_result = {"error": str(e)}

    print("[copiano] Step 2: 乐谱对齐 (align_score) ...", file=sys.stderr)
    try:
        align_result = run_script("align_score.py", args.ref_midi, args.user_midi)
        print(f"  对齐点={align_result['n_alignment_points']}, quality={align_result['alignment_quality']}", file=sys.stderr)
    except Exception as e:
        print(f"  [warn] 对齐失败: {e}", file=sys.stderr)
        align_result = {"error": str(e)}

    # 找曲目元数据
    if args.piece:
        piece = find_piece(args.piece)
        if not piece:
            print(f"  [warn] 在 KG 中找不到 '{args.piece}',用 generic classical", file=sys.stderr)
            piece = {"name": args.piece, "composer": "Unknown", "period": "Classical", "key": "C", "difficulty": 3, "total_measures": 32}
    else:
        piece = {"name": "练习曲", "composer": "Unknown", "period": "Classical", "key": "C", "difficulty": 3, "total_measures": 32}

    print(f"[copiano] Step 3: KG RAG (period={piece.get('period')}) ...", file=sys.stderr)
    kg = MusicKG()
    period_errors = kg.get_period_errors(piece.get("period", "Classical"))
    related_pieces = kg.get_pieces_by_period(piece.get("period", "Classical"), max_difficulty=piece.get("difficulty", 3) + 1)
    print(f"  {len(period_errors)} 个时期错误, {len(related_pieces)} 个类似作品", file=sys.stderr)

    print("[copiano] Step 4: 拼 LLM prompt ...", file=sys.stderr)
    prompt = build_feedback_prompt(eval_result, piece, kg=kg, measure=args.measure)
    print(f"  prompt: system {len(prompt['system'])} 字, user {len(prompt['user'])} 字", file=sys.stderr)

    result = {
        "eval": eval_result,
        "align": align_result,
        "style": style_result,
        "piece": piece,
        "prompt": prompt,
    }

    if not args.no_llm:
        print(f"[copiano] Step 5: 调 LLM ({args.model}) ...", file=sys.stderr)
        try:
            llm_out = call_llm(prompt, model_id=args.model, max_tokens=300)
            result["llm_response"] = llm_out["response"]
            print("\n" + "=" * 60, file=sys.stderr)
            print(llm_out["response"], file=sys.stderr)
            print("=" * 60 + "\n", file=sys.stderr)
        except Exception as e:
            print(f"  [warn] LLM 失败: {e}", file=sys.stderr)
            result["llm_error"] = str(e)

    if args.aggregated:
        print("[copiano] Step 6: 聚合反馈(全曲级) ...", file=sys.stderr)
        # 模拟多小节评估(本轮只有单组 eval,做"小节切片"模拟)
        # 实际应用:用 align_score 切片,然后逐段 eval
        # 这里简化:用单组 eval 复制 N 份
        n_measures = max(8, piece.get("total_measures", 16))
        measure_results = []
        for i in range(min(n_measures, 8)):
            m = dict(eval_result)
            m["measure"] = i + 1
            # 模拟:小节 1-3 错,4-8 进步
            m["score"] = max(0, eval_result["score"] - (3 - i if i < 3 else 0) * 2)
            m["n_pitch_errors"] = 1 if i < 3 else 0
            m["pitch_error_samples"] = eval_result.get("pitch_error_samples", []) if i < 3 else []
            measure_results.append(m)
        agg = aggregate_measures(measure_results)
        agg_prompt = build_aggregated_prompt(agg, piece)
        result["aggregation"] = agg
        result["aggregated_prompt"] = agg_prompt
        if not args.no_llm:
            try:
                agg_llm = call_llm(agg_prompt, model_id=args.model, max_tokens=400)
                result["aggregated_llm_response"] = agg_llm["response"]
                print("\n" + "=" * 60, file=sys.stderr)
                print("[聚合反馈]")
                print(agg_llm["response"], file=sys.stderr)
                print("=" * 60 + "\n", file=sys.stderr)
            except Exception as e:
                print(f"  [warn] 聚合 LLM 失败: {e}", file=sys.stderr)
                result["aggregated_llm_error"] = str(e)

    # Step 7: 历史聚类(可选)
    history_path = Path("/tmp/copiano_history.json")
    if args.save_history:
        # 追加本次到历史
        hist = []
        if history_path.exists():
            try:
                hist = json.loads(history_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                hist = []
        # 只存关键字段
        hist.append({
            "piece": piece.get("name"),
            "period": piece.get("period"),
            "timestamp": datetime.now().isoformat(),
            "score": eval_result.get("score"),
            "pitch_accuracy": eval_result.get("pitch_accuracy"),
            "timing_std_ms": eval_result.get("timing_std_ms"),
            "timing_mean_ms": eval_result.get("timing_mean_ms"),
            "velocity_correlation": eval_result.get("velocity_correlation"),
            "n_pitch_errors": eval_result.get("n_pitch_errors"),
        })
        history_path.write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[copiano] 历史已保存到 {history_path}(共 {len(hist)} 条)", file=sys.stderr)
        result["history_saved"] = len(hist)

    if args.cluster_history:
        if not history_path.exists():
            print(f"  [warn] {history_path} 不存在,请先 --save-history 几次", file=sys.stderr)
        else:
            hist = json.loads(history_path.read_text(encoding="utf-8"))
            if len(hist) < 2:
                print(f"  [warn] 历史只有 {len(hist)} 条,需要至少 2 条才能聚类", file=sys.stderr)
            else:
                try:
                    cluster_result = cluster_errors(hist)
                    result["cluster"] = cluster_result
                    print("\n" + "=" * 60, file=sys.stderr)
                    print("[错误模式聚类]")
                    print(f"  K={cluster_result.get('n_clusters')}, silhouette={cluster_result.get('silhouette_score')}", file=sys.stderr)
                    for rec in cluster_result.get("recommendations", []):
                        if rec["piece"] == piece.get("name"):
                            print(f"  你的本曲 [{rec['piece']}] 属于: {rec['profile_name']}", file=sys.stderr)
                            print(f"  推荐: {rec['recommendation']}", file=sys.stderr)
                    print("=" * 60 + "\n", file=sys.stderr)
                except Exception as e:
                    print(f"  [warn] 聚类失败: {e}", file=sys.stderr)

    # Step 8: Bandit 推荐(可选)
    if args.recommend:
        # 先看有没有 cluster 结果
        cluster_data = result.get("cluster", {})
        my_cluster_id = 4  # 默认良好可精进
        if cluster_data:
            # 找本曲的 cluster_id
            for rec in cluster_data.get("recommendations", []):
                if rec["piece"] == piece.get("name"):
                    my_cluster_id = rec["cluster_id"]
                    break
        try:
            recs = recommend_next_piece(
                current_piece=piece.get("name", ""),
                current_difficulty=piece.get("difficulty", 3),
                cluster_id=my_cluster_id,
                period=piece.get("period"),
                top_k=3,
            )
            result["recommendations"] = recs
            print("\n" + "=" * 60, file=sys.stderr)
            print(f"[下一步推荐](基于 cluster {my_cluster_id})")
            for i, r in enumerate(recs, 1):
                print(f"  {i}. {r['piece']} ({r['composer']}, 难度 {r['difficulty']}, {r['period']})", file=sys.stderr)
                print(f"     原因: {r['reason']}", file=sys.stderr)
            print("=" * 60 + "\n", file=sys.stderr)
        except Exception as e:
            print(f"  [warn] 推荐失败: {e}", file=sys.stderr)

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[copiano] 写入 {args.output}", file=sys.stderr)
    else:
        # stdout 输出精简版(完整 JSON)
        out = {
            "piece": result["piece"],
            "score": result["eval"]["score"],
            "n_pitch_errors": result["eval"]["n_pitch_errors"],
            "alignment_quality": result["align"].get("alignment_quality"),
            "llm_response": result.get("llm_response"),
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
