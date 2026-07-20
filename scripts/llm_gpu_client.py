"""
llm_gpu_client.py — Mac 端调 GPU 上 Qwen 7B 的客户端(via HTTP 持久化 daemon)

底层:
- GPU 端跑 llm_daemon.py,模型常驻,监听 127.0.0.1:8765
- Mac 通过 SSH 跑 `curl http://localhost:8765/chat` 调

这样:模型只加载一次,后续请求 3-5s(纯推理时间)

用法:
    from llm_gpu_client import call_qwen_gpu
    reply = call_qwen_gpu([
        {"role": "system", "content": "你是 CoPiano"},
        {"role": "user", "content": "你好"},
    ])
"""
from __future__ import annotations

import json
import re
import time
from typing import Optional

from gpu_shell import run_on_gpu, GPU_HOST

DAEMON_URL = "http://127.0.0.1:8765"
DEFAULT_MAX_TOKENS = 200
DEFAULT_TIMEOUT = 90  # daemon 模型已加载,主要时间在推理


def _messages_to_prompt(messages: list[dict]) -> dict:
    """OpenAI messages → {system, user}"""
    system = next((m["content"] for m in messages if m["role"] == "system"), "你是 CoPiano,AI 钢琴老师。")
    user_parts = [m["content"] for m in messages if m["role"] == "user"]
    user = "\n\n".join(user_parts) if user_parts else "你好"
    return {"system": system, "user": user}


def call_qwen_gpu(
    messages: list[dict],
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    """通过 GPU 端 daemon 调 Qwen,返回生成文本

    Args:
        messages: OpenAI 风格 messages
        max_tokens: 最大生成 tokens
        timeout: SSH 调用超时(秒)

    Returns:
        生成的回复文本(出错时返回带 [gpu-error] 前缀的字符串)
    """
    prompt = _messages_to_prompt(messages)
    body = json.dumps({**prompt, "max_tokens": max_tokens}, ensure_ascii=False)

    # 转义单引号给 shell
    body_escaped = body.replace("'", "'\\''")

    # SSH 调 curl
    curl_cmd = (
        f"curl -s -X POST {DAEMON_URL}/chat "
        f"-H 'Content-Type: application/json' "
        f"-d '{body_escaped}' "
        f"--max-time {timeout - 5}"
    )
    try:
        out = run_on_gpu(curl_cmd, timeout=timeout)
    except Exception as e:
        return f"[gpu-error] {e}"

    # 过滤 expect 输出(gpu.sh 会输出 spawn / password 提示行)
    # 真实 stdout 在 password 之后
    if "password:" in out:
        out = out.split("password:", 1)[1]
    # 去除可能的前后空白和首行提示
    out = out.strip()

    # 解析 JSON 响应
    try:
        resp = json.loads(out.strip())
    except json.JSONDecodeError:
        return f"[gpu-error] 非 JSON 响应: {out[:200]}"

    if "error" in resp:
        return f"[gpu-error] {resp['error']}"

    return resp.get("text", "")


def gpu_daemon_status() -> dict:
    """查 daemon 状态(健康检查 + 模型信息)"""
    out = run_on_gpu(f"curl -s {DAEMON_URL}/health --max-time 5", timeout=15)
    try:
        return json.loads(out.strip())
    except Exception:
        return {"reachable": False, "raw": out[:200]}


# ----- 注入 voice_dialog -----
def patch_voice_dialog_with_gpu():
    """把 voice_dialog.call_llm 的 backend='gpu' 真正接通"""
    import voice_dialog

    def gpu_llm(messages, backend="mock", **kwargs):
        if backend != "gpu":
            if backend == "mock":
                return voice_dialog._mock_llm(messages)
            return None
        try:
            t0 = time.time()
            reply = call_qwen_gpu(messages)
            dt = time.time() - t0
            if "[gpu-error]" in reply:
                print(f"[gpu-llm] ❌ {reply}", file=__import__("sys").stderr)
                return voice_dialog._mock_llm(messages)
            print(f"[gpu-llm] ✅ {dt:.1f}s, {len(reply)} chars", file=__import__("sys").stderr)
            return reply
        except Exception as e:
            print(f"[gpu-llm] ❌ {e}", file=__import__("sys").stderr)
            return voice_dialog._mock_llm(messages)

    voice_dialog.call_llm = gpu_llm


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="跑一个测试对话")
    parser.add_argument("--status", action="store_true", help="查 daemon 状态")
    parser.add_argument("--speed", action="store_true", help="测 3 次推理速度")
    args = parser.parse_args()

    if args.status:
        print(json.dumps(gpu_daemon_status(), ensure_ascii=False, indent=2))
    elif args.test:
        msgs = [
            {"role": "system", "content": "你是 CoPiano,AI 钢琴老师。简洁回复,中文为主。"},
            {"role": "user", "content": "你好,简单介绍一下你自己。"},
        ]
        t0 = time.time()
        reply = call_qwen_gpu(msgs)
        print(f"=== A (from Qwen 7B on GPU, {time.time()-t0:.1f}s) ===")
        print(reply)
    elif args.speed:
        print("=== 连续 3 次推理速度测试 ===")
        msgs = [
            {"role": "system", "content": "你是 CoPiano,AI 钢琴老师。简洁回复。"},
            {"role": "user", "content": "用一句话介绍巴洛克时期的钢琴风格。"},
        ]
        for i in range(3):
            t0 = time.time()
            reply = call_qwen_gpu(msgs)
            print(f"[{i+1}] {time.time()-t0:.1f}s: {reply[:100]}")
