"""
llm_call.py — LLM 推理调用(基于 HF transformers,支持镜像)

用法:
    python3 llm_call.py <model_id> <prompt_json>
    # prompt_json 来自 llm_feedback.py 输出

支持镜像:
    - HF_ENDPOINT 自动设 hf-mirror.com
    - 也可指定 MS(ModelScope 阿里)MODEL_ID 前缀
"""
from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path

# 镜像 + cache
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HOME", "/root/autodl-tmp/hf-cache")
os.environ.setdefault("TRANSFORMERS_CACHE", "/root/autodl-tmp/hf-cache")


def load_model(model_id: str, dtype: str = "float16"):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    torch_dtype = {"float16": torch.float16, "bfloat16": torch.bfloat16, "float32": torch.float32}.get(dtype, torch.float16)
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=torch_dtype, trust_remote_code=True
    )
    if torch.cuda.is_available():
        model = model.to("cuda")
    return tok, model


def chat(tok, model, system: str, user: str, max_new_tokens: int = 200):
    import torch
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    # Qwen 风格 / 标准 chat template
    if hasattr(tok, "apply_chat_template"):
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    else:
        text = f"<|system|>\n{system}\n<|user|>\n{user}\n<|assistant|>\n"
    inp = tok(text, return_tensors="pt").to(model.device)
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(
            **inp,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tok.eos_token_id,
        )
    gen = tok.decode(out[0][inp.input_ids.shape[1]:], skip_special_tokens=True)
    return gen, time.time() - t0


def main():
    if len(sys.argv) < 3:
        print("Usage: llm_call.py <model_id> <prompt_json> [max_tokens]", file=sys.stderr)
        return 1
    model_id = sys.argv[1]
    prompt_path = Path(sys.argv[2])
    max_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 250
    prompt = json.loads(prompt_path.read_text(encoding="utf-8"))

    print(f"[llm_call] model: {model_id}", file=sys.stderr)
    print(f"[llm_call] HF_ENDPOINT: {os.environ.get('HF_ENDPOINT')}", file=sys.stderr)
    print(f"[llm_call] prompt source: {prompt_path}", file=sys.stderr)

    t0 = time.time()
    tok, model = load_model(model_id)
    print(f"[llm_call] loaded in {time.time()-t0:.1f}s, mem: {__import__('torch').cuda.memory_allocated()/1024**3:.2f} GiB", file=sys.stderr)

    gen, dt = chat(tok, model, prompt["system"], prompt["user"], max_tokens)
    print(f"[llm_call] generated in {dt:.1f}s, {len(gen)} chars", file=sys.stderr)
    print("---RESPONSE---")
    print(gen)
    print("---END---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
