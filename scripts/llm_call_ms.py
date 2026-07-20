"""
llm_call_ms.py — ModelScope 阿里镜像版 LLM 调用

ModelScope 优势:
- 阿里云国内,网络极稳定
- Qwen 系列原生支持
- API 简单: snapshot_download + AutoModel

用法:
    python3 llm_call_ms.py <model_id> <prompt_json> [max_tokens]
    # 例: python3 llm_call_ms.py qwen/Qwen2.5-1.5B-Instruct /path/to/prompt.json
"""
from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path

# ModelScope cache
os.environ.setdefault("MODELSCOPE_CACHE", "/root/autodl-tmp/ms-cache")
Path("/root/autodl-tmp/ms-cache").mkdir(parents=True, exist_ok=True)


def download_model(model_id: str):
    from modelscope import snapshot_download
    print(f"[ms] downloading {model_id} ...", file=sys.stderr, flush=True)
    t0 = time.time()
    p = snapshot_download(
        model_id,
        cache_dir=os.environ["MODELSCOPE_CACHE"],
        revision="master",
    )
    print(f"[ms] downloaded to {p} in {time.time()-t0:.1f}s", file=sys.stderr, flush=True)
    return p


def load_model(model_path: str):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    tok = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, torch_dtype=torch.float16, trust_remote_code=True
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
        print("Usage: llm_call_ms.py <model_id> <prompt_json> [max_tokens]", file=sys.stderr)
        return 1
    model_id = sys.argv[1]
    prompt_path = Path(sys.argv[2])
    max_tokens = int(sys.argv[3]) if len(sys.argv) > 3 else 250
    prompt = json.loads(prompt_path.read_text(encoding="utf-8"))

    print(f"[llm_call_ms] model: {model_id}", file=sys.stderr, flush=True)
    print(f"[llm_call_ms] MODELSCOPE_CACHE: {os.environ.get('MODELSCOPE_CACHE')}", file=sys.stderr, flush=True)

    t0 = time.time()
    model_path = download_model(model_id)
    tok, model = load_model(model_path)
    print(f"[llm_call_ms] loaded in {time.time()-t0:.1f}s, mem: {__import__('torch').cuda.memory_allocated()/1024**3:.2f} GiB", file=sys.stderr, flush=True)

    gen, dt = chat(tok, model, prompt["system"], prompt["user"], max_tokens)
    print(f"[llm_call_ms] generated in {dt:.1f}s, {len(gen)} chars", file=sys.stderr, flush=True)
    print("---RESPONSE---")
    print(gen)
    print("---END---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
