"""
llm_feedback.py — L4 LLM 教学反馈生成器(基于 KG 的 RAG + 评估结果)

设计:
- 输入:评估结果(eval_pitch JSON)+ 乐谱对齐结果(align_score JSON)+ 乐谱元数据
- 中间:从 KG 查"这段时期 + 难度"的风格 + 错误模式 + 推荐练习
- 输出:结构化 prompt → LLM 生成"风格化讲解"(可解释反馈)

分两层:
1. 离线(本脚本):拼 prompt,不调 LLM
2. 在线(llm_call): 调 Qwen 生成反馈

为最大化创新性,设计"双层 RAG":
- RAG1:从 KG 拉"相关知识"(风格/错误/进行)
- RAG2:从用户历史错误模式拉"个性化建议"

LLM 反馈 prompt 模板(中英混合,因为乐理术语英文更准):
- system: 角色 + 教学风格约束
- user: 评估结果 + KG 上下文 + 任务
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

# 复用 tonnetz_kg
sys.path.insert(0, str(Path(__file__).parent))
from tonnetz_kg import MusicKG, PIECES, COMPOSERS


# === 风格化教学 prompt 模板 ===

SYSTEM_PROMPT_ZH = """你是一位有 30 年经验的古典钢琴教师,熟悉巴洛克、古典、浪漫三个时期。
你的教学风格:
- 先肯定学生做得好的地方(必须)
- 然后指出具体问题(音/节奏/力度/表现力)
- 解释"为什么"(乐理或风格根据)
- 给出可执行的练习建议(具体到音/小节)
- 用比喻和具体例子,避免抽象术语
- 简短(200 字以内),不要用"加油""你可以的"等空话
"""

USER_PROMPT_TEMPLATE_ZH = """## 教学场景
学生正在练习:{piece_name}({composer},{period}时期,难度{level})
当前小节:{measure} / 总小节数:{total_measures}
调性:{key}

## 评估结果(来自 MIDI 自动评估)
- 总分:{score} / 100
- 错音率:{pitch_accuracy:.1%} ({n_pitch_errors} 个错音)
- 节奏偏差:均值 {timing_mean_ms:+.1f}ms,标准差 {timing_std_ms:.1f}ms
- 力度相关性:{velocity_correlation:.2f}
- 完整度:{note_completeness:.1%}

## 错音细节(最多 5 个)
{pitch_errors}

## 节奏异常小节(若有)
{timing_outliers}

## 乐理知识上下文(RAG 检索)
### 时期风格
{period_style}

### 该时期常见错误
{period_errors}

### 类似作品
{related_pieces}

## 你的任务
写一段简短(150-250 字)、有温度、有"为什么"的教学反馈。
要求:
1. 一句话肯定(必须)
2. 指出 1-2 个最关键的具体问题(具体到小节/音)
3. 解释为什么这是问题(乐理/风格)
4. 给出 1 个可立即练习的建议
"""


def build_feedback_prompt(
    eval_result: dict,
    piece_meta: dict,
    kg: Optional[MusicKG] = None,
    measure: int = 1,
) -> dict:
    """根据评估结果 + 乐谱元数据 + KG,生成 LLM 反馈 prompt"""
    if kg is None:
        kg = MusicKG()

    period = piece_meta.get("period", "Classical")
    composer = piece_meta.get("composer", "Unknown")
    piece_name = piece_meta.get("name", "Unknown")
    key = piece_meta.get("key", "C")
    level = piece_meta.get("difficulty", 3)
    total_measures = piece_meta.get("total_measures", 16)

    # RAG 检索
    period_style = kg.get_style_for_period(period)
    period_errors = kg.get_period_errors(period)
    related = kg.get_pieces_by_period(period, max_difficulty=level + 1)[:3]
    related_str = "\n".join([
        f"  - {p['name']} ({p['composer']}, 难度 {p['difficulty']})" for p in related
    ]) or "  (无)"

    # 错音细节
    errs = eval_result.get("pitch_error_samples", [])
    if errs:
        err_strs = []
        for e in errs[:5]:
            if e["type"] == "wrong":
                err_strs.append(f"  - 小节 {measure}: {e.get('ref_note','?')} → 弹成了 {e.get('user_note','?')}(半音差)")
            elif e["type"] == "missing":
                err_strs.append(f"  - 小节 {measure}: 漏音 {e.get('ref_pitch','?')}")
            elif e["type"] == "extra":
                err_strs.append(f"  - 小节 {measure}: 多音 {e.get('user_pitch','?')}")
        pitch_errors_str = "\n".join(err_strs) or "  (无)"
    else:
        pitch_errors_str = "  (无)"

    # 节奏异常(简化:std > 50ms 标为不稳)
    timing_outliers = []
    if eval_result.get("timing_std_ms", 0) > 80:
        timing_outliers.append("  - 节奏稳定性差(std>80ms),建议节拍器从 60 BPM 练起")
    if abs(eval_result.get("timing_mean_ms", 0)) > 100:
        timing_outliers.append(f"  - 整体偏 {('快' if eval_result['timing_mean_ms']<0 else '慢')}(>{100}ms),可能没跟节拍器")
    timing_outliers_str = "\n".join(timing_outliers) or "  (无明显异常)"

    # 错误字符串
    pe_str = "\n".join([
        f"  - {e['name']}: {e['desc']}" for e in period_errors
    ]) or "  (无)"

    # 拼 user prompt
    user_prompt = USER_PROMPT_TEMPLATE_ZH.format(
        piece_name=piece_name,
        composer=composer,
        period=period,
        level=level,
        measure=measure,
        total_measures=total_measures,
        key=key,
        score=eval_result.get("score", 0),
        pitch_accuracy=eval_result.get("pitch_accuracy", 0),
        n_pitch_errors=eval_result.get("n_pitch_errors", 0),
        timing_mean_ms=eval_result.get("timing_mean_ms", 0),
        timing_std_ms=eval_result.get("timing_std_ms", 0),
        velocity_correlation=eval_result.get("velocity_correlation", 0),
        note_completeness=eval_result.get("note_completeness", 0),
        pitch_errors=pitch_errors_str,
        timing_outliers=timing_outliers_str,
        period_style=period_style,
        period_errors=pe_str,
        related_pieces=related_str,
    )

    return {
        "system": SYSTEM_PROMPT_ZH,
        "user": user_prompt,
        "meta": {
            "piece": piece_name,
            "composer": composer,
            "period": period,
            "measure": measure,
            "score": eval_result.get("score", 0),
        },
    }


def demo():
    """演示:用 test_ref vs test_user 的评估结果,生成 prompt"""
    import subprocess
    # 跑 eval_pitch 得到测试结果
    r = subprocess.run(
        ["python3", str(Path(__file__).parent / "eval_pitch.py"),
         "/tmp/test_ref.mid", "/tmp/test_user.mid"],
        capture_output=True, text=True, cwd=str(Path(__file__).parent.parent)
    )
    if r.returncode != 0:
        print(f"eval_pitch failed: {r.stderr}")
        return
    eval_result = json.loads(r.stdout)

    # Bach Minuet in G 元数据
    piece = {
        "name": "Minuet in G",
        "composer": "Bach",
        "period": "Baroque",
        "key": "G",
        "difficulty": 2,
        "total_measures": 32,
    }

    prompt = build_feedback_prompt(eval_result, piece)
    print("=== SYSTEM ===")
    print(prompt["system"])
    print("\n=== USER ===")
    print(prompt["user"])
    print("\n=== META ===")
    print(json.dumps(prompt["meta"], indent=2, ensure_ascii=False))

    # 导出到文件,后续 LLM 调用直接读
    out = Path(__file__).parent.parent / "notes" / "feedback_prompt_demo.json"
    out.write_text(json.dumps(prompt, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✓ 导出到 {out}")


if __name__ == "__main__":
    demo()
