"""
llm_self_eval.py — LLM 自我评估(让 LLM 评价自己生成的反馈质量)

设计思路:
- 评估对象:之前生成的 llm_response
- 评估维度(4 维,各 1-5 分):
  1. 具体性(specificity):是否提到具体小节/音符/动作
  2. 准确性(accuracy):描述的错音/问题是否正确
  3. 可执行性(actionability):建议是否可立即执行
  4. 鼓励性(supportive):语气是否肯定 + 有温度
- 输出:JSON 评分 + 改进建议

应用:
- 自动评估反馈质量,作为 Phase 2 完成度指标
- 在 1.5B vs 7B 等模型对比时,定量打分
- 反馈循环:用自评改进 prompt

创新点:
- "元评估"思路(LLM-as-a-judge)
- 4 维度量化,可比对
- 闭环:自评 → 改进 prompt → 重生成 → 重新评分
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# ModelScope 配置
os.environ.setdefault("MODELSCOPE_CACHE", "/root/autodl-tmp/ms-cache")


EVAL_PROMPT = """你是一位钢琴教学评估专家。请评估以下 AI 教师给学生写的钢琴反馈。

## 评估维度(各 1-5 分)

1. **具体性** (specificity): 反馈是否提到具体的小节号、音符、动作
   1=泛泛而谈,5=精确指向
2. **准确性** (accuracy): 描述的错音/问题是否与评估结果一致
   1=胡言乱语,3=部分正确,5=完全准确
3. **可执行性** (actionable): 建议是否可立即执行
   1=空话,5=详细步骤
4. **鼓励性** (supportive): 语气是否肯定 + 有温度
   1=纯批评,3=中性,5=温暖 + 启发

## 评估结果(JSON 输出,严格按格式)

JSON 字段:
- specificity: 1-5
- accuracy: 1-5
- actionable: 1-5
- supportive: 1-5
- total: 4-20(4 项之和)
- comments: 一句话评价,指出最强和最弱维度
- improvements: 具体如何改进(10-30 字)

## 反馈内容(待评估)

```
__FEEDBACK__
```

## 评估依据(评分对照)

```
__CONTEXT__
```

请输出 JSON(只输出 JSON,不要其他文字):
"""


def build_eval_prompt(feedback: str, context: dict) -> str:
    """构造自评 prompt(用占位符替换避免 format() 冲突)"""
    ctx_str = json.dumps(context, ensure_ascii=False, indent=2)
    return EVAL_PROMPT.replace("__FEEDBACK__", feedback).replace("__CONTEXT__", ctx_str)


def call_self_eval(feedback: str, context: dict, model_id: str = "qwen/Qwen2.5-7B-Instruct", max_tokens: int = 300) -> dict:
    """调 LLM 评估反馈(通过 ModelScope)"""
    import subprocess
    prompt = build_eval_prompt(feedback, context)

    # 写 prompt 到临时文件
    tmp = "/tmp/copiano_eval_prompt.json"
    Path(tmp).write_text(json.dumps({
        "system": "你是一位钢琴教学评估专家,严格按 JSON 格式输出评估结果。",
        "user": prompt,
    }, ensure_ascii=False), encoding="utf-8")

    # 调 llm_call_ms(走 ModelScope)
    p = subprocess.run(
        ["/root/autodl-tmp/conda-envs/copiano/bin/python",
         "/root/autodl-tmp/copiano/code/llm_call_ms.py",
         model_id, tmp, str(max_tokens)],
        capture_output=True, text=True, timeout=300,
    )
    if p.returncode != 0:
        raise RuntimeError(f"LLM call failed: {p.stderr[:300]}")

    text = p.stdout
    if "---RESPONSE---" in text:
        text = text.split("---RESPONSE---")[1].split("---END---")[0].strip()

    # 尝试解析 JSON(容忍 markdown 包装)
    cleaned = text.strip()
    # 去掉 ```json ... ``` 包装
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # 删第一行 ```json 和最后一行 ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    # 找第一个 { 到最后一个 }
    try:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start:end+1])
    except json.JSONDecodeError:
        pass

    return {"raw": text, "parse_error": "无法解析 JSON"}


def demo():
    """演示:评估之前 1.5B 和 7B 的反馈"""
    print("=== LLM 自评 demo ===\n")

    # 1) 1.5B 反馈(从 llm_comparison.md 拿)
    feedback_15b = """**关键肯定**: 学生在演奏中展现了极高的音乐理解能力和技巧水平,特别是对巴洛克时期的细腻情感表达。

**关键问题**: 小节 1: 弹成了 3,导致了半音上的错误。这不仅影响了音准,还破坏了旋律的连贯性和流畅性。

**原因解释**: 在巴洛克时期,装饰音(如 trill 和 mordent)通常没有固定的时值,需要根据具体的音乐情境来决定使用的时间长度。弹错半音会导致整个旋律的不和谐感。

**练习建议**: 重复练习小节 1,慢速练习逐步提高速度,确保每个音符都准确无误。"""

    feedback_7b = """很好,你已经掌握了大部分的音符和节奏。但在小节1中,你将第4拍弹成了3,这是一个半音的错误。在巴洛克时期,准确把握每个音符的音高非常重要,因为这直接影响到作品的和谐与美感。你可以尝试单独练习这个小节,重点放在第4拍上,确保弹出正确的音高。比如,你可以先慢速弹奏,专注于这个音,然后再逐渐加快速度。这样可以帮助你更好地理解和记忆正确的音高。"""

    context = {
        "piece": "Minuet in G (Bach, Baroque, 难度 2)",
        "eval": {
            "score": 93.5,
            "pitch_accuracy": 0.875,
            "n_pitch_errors": 1,
            "n_pitch_errors_detail": "小节 1: ref_pitch=64 → user_pitch=63 (E → D#, 半音差)"
        },
        "kg_period": "Baroque",
        "kg_period_style": "通奏低音主导,对位严密,装饰音即兴,常用羽管键琴音色",
    }

    # 在 GPU 端跑
    for label, fb in [("1.5B", feedback_15b), ("7B", feedback_7b)]:
        print(f"\n--- 评估 {label} 反馈 ---")
        try:
            result = call_self_eval(fb, context, model_id="qwen/Qwen2.5-7B-Instruct")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"FAIL: {e}")
        time.sleep(1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        # CLI 模式
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("feedback_file", help="反馈文本文件路径")
        ap.add_argument("--context", help="评估依据 JSON 文件")
        ap.add_argument("--model", default="qwen/Qwen2.5-7B-Instruct")
        args = ap.parse_args()
        fb = Path(args.feedback_file).read_text(encoding="utf-8")
        ctx = json.loads(Path(args.context).read_text(encoding="utf-8")) if args.context else {}
        r = call_self_eval(fb, ctx, model_id=args.model)
        print(json.dumps(r, indent=2, ensure_ascii=False))
