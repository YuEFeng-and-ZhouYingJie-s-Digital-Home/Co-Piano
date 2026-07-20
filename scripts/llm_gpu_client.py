"""
llm_gpu_client.py — Mac 端调 GPU 上 Qwen 7B 的客户端

把 OpenAI 风格 messages → GPU 上 llm_call_ms.py → 回复文本

流程:
1. 把 messages 写成 prompt.json(mac /tmp)
2. scp 到 GPU /tmp/
3. ssh 跑 python3 scripts/llm_call_ms.py <model_id> /tmp/prompt.json
4. 解析 stdout(以 ---RESPONSE--- / ---END--- 为界)
5. 清理

用法:
    from llm_gpu_client import call_qwen_gpu
    reply = call_qwen_gpu([
        {"role": "system", "content": "你是 CoPiano"},
        {"role": "user", "content": "你好"},
    ])
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

from gpu_shell import scp_to_gpu, run_on_gpu, GPU_SCRIPTS_DIR, GPU_PWD

# 默认模型
DEFAULT_MODEL = "qwen/Qwen2.5-7B-Instruct"
DEFAULT_MAX_TOKENS = 200
DEFAULT_TIMEOUT = 120  # GPU 加载模型 + 推理可能 30-60s


def _messages_to_prompt(messages: list[dict]) -> dict:
    """把 OpenAI messages 转成 llm_call_ms 需要的 {system, user} 格式

    简单做法:system 取首条 system,user 取最后一条 user
    """
    system = next((m["content"] for m in messages if m["role"] == "system"), "你是 CoPiano,AI 钢琴老师。")
    user_parts = [m["content"] for m in messages if m["role"] == "user"]
    user = "\n\n".join(user_parts) if user_parts else "你好"
    return {"system": system, "user": user}


def call_qwen_gpu(
    messages: list[dict],
    model_id: str = DEFAULT_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """通过 SSH 在 GPU 上调 Qwen,返回生成文本

    Args:
        messages: OpenAI 风格 messages 列表
        model_id: ModelScope/HF 模型 ID
        max_tokens: 最大生成 tokens
        timeout: 超时秒数
    """
    # 1. 写本地 prompt.json
    prompt = _messages_to_prompt(messages)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(prompt, f, ensure_ascii=False)
        local_prompt = f.name

    remote_prompt = "/tmp/copiano_prompt.json"
    try:
        # 2. scp 到 GPU
        scp_to_gpu(local_prompt, remote_prompt, timeout=15)

        # 3. 在 GPU 上跑 llm_call_ms.py
        # 用 cd 到 copiano/code 目录 + copiano conda env
        remote_cmd = (
            f"cd {GPU_SCRIPTS_DIR} 2>/dev/null && "
            f"/root/autodl-tmp/conda-envs/copiano/bin/python3 "
            f"llm_call_ms.py {model_id} {remote_prompt} {max_tokens} 2>&1"
        )
        out = run_on_gpu(remote_cmd, timeout=timeout)

        # 4. 解析输出(以 ---RESPONSE--- / ---END--- 为界)
        m = re.search(r"---RESPONSE---\s*\n(.*?)\n\s*---END---", out, re.DOTALL)
        if m:
            return m.group(1).strip()

        # 兜底:如果没找到标记,返回整个 stdout(去掉加载日志)
        # 启发式:取最后 1000 字符(生成结果通常在末尾)
        tail = out.strip().split("\n")[-5:]
        return "\n".join(tail).strip()
    finally:
        Path(local_prompt).unlink(missing_ok=True)


# ----- 直接给 voice_dialog 用 -----
def patch_voice_dialog_with_gpu():
    """把 voice_dialog.call_llm 的 backend='gpu' 真正接通"""
    import voice_dialog

    def gpu_llm(messages, backend="mock", **kwargs):
        if backend != "gpu":
            return voice_dialog._mock_llm(messages) if backend == "mock" else None
        try:
            t0 = time.time()
            reply = call_qwen_gpu(messages)
            dt = time.time() - t0
            print(f"[gpu-llm] ✅ {dt:.1f}s, {len(reply)} chars", file=sys.stderr)
            return reply
        except Exception as e:
            print(f"[gpu-llm] ❌ {e}", file=sys.stderr)
            return voice_dialog._mock_llm(messages)

    voice_dialog.call_llm = gpu_llm


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="跑一个测试对话")
    args = parser.parse_args()

    if args.test:
        msgs = [
            {"role": "system", "content": "你是 CoPiano,AI 钢琴老师。简洁回复,中文为主。"},
            {"role": "user", "content": "你好,简单介绍一下你自己。"},
        ]
        t0 = time.time()
        reply = call_qwen_gpu(msgs)
        print(f"=== Q (sent via GPU) ===")
        for m in msgs:
            print(f"[{m['role']}] {m['content']}")
        print(f"\n=== A (from Qwen 7B on GPU, {time.time()-t0:.1f}s) ===")
        print(reply)
