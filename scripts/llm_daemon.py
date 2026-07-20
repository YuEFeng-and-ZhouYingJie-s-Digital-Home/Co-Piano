"""
llm_daemon.py — GPU 端 LLM 持久化服务(stdlib http.server,免装 Flask)

跑在 GPU 上,模型常驻内存,响应 /chat POST 请求。

启动(GPU 端):
    cd /root/autodl-tmp/copiano/code
    nohup /root/autodl-tmp/conda-envs/copiano/bin/python3 -u llm_daemon.py \\
        --model qwen/Qwen2.5-7B-Instruct --port 8765 > /tmp/llm_daemon.log 2>&1 &

客户端(Mac 端 via SSH):
    ssh gpu "curl -s -X POST http://localhost:8765/chat \\
        -H 'Content-Type: application/json' \\
        -d '{\"system\": \"...\", \"user\": \"...\", \"max_tokens\": 200}'"

优势:模型只加载一次,后续请求 3-5s 即可返回(纯推理时间)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# 必须用 copiano conda env(MODELSCOPE_CACHE 已经设)
import os
os.environ.setdefault("MODELSCOPE_CACHE", "/root/autodl-tmp/ms-cache")


class LLMService:
    """Qwen 7B 服务类(模型常驻)"""

    def __init__(self, model_id: str):
        import torch
        from modelscope import snapshot_download
        from transformers import AutoTokenizer, AutoModelForCausalLM

        self.tokenizer = None
        self.model = None
        self.model_id = model_id

        print(f"[daemon] loading {model_id} ...", flush=True)
        t0 = time.time()
        model_path = snapshot_download(model_id, cache_dir=os.environ["MODELSCOPE_CACHE"], revision="master")
        print(f"[daemon] model path: {model_path}", flush=True)

        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path, torch_dtype=torch.float16, trust_remote_code=True
        )
        if torch.cuda.is_available():
            self.model = self.model.to("cuda")
        print(f"[daemon] loaded in {time.time()-t0:.1f}s, GPU mem: {torch.cuda.memory_allocated()/1024**3:.2f} GiB", flush=True)

    def chat(self, system: str, user: str, max_tokens: int = 200) -> tuple[str, float]:
        """生成回复,返回 (text, elapsed_seconds)"""
        import torch
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        if hasattr(self.tokenizer, "apply_chat_template"):
            text = self.tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        else:
            text = f"<|system|>\n{system}\n<|user|>\n{user}\n<|assistant|>\n"
        inp = self.tokenizer(text, return_tensors="pt").to(self.model.device)

        t0 = time.time()
        with torch.no_grad():
            out = self.model.generate(
                **inp,
                max_new_tokens=max_tokens,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        gen = self.tokenizer.decode(out[0][inp.input_ids.shape[1]:], skip_special_tokens=True)
        return gen.strip(), time.time() - t0


# 全局服务(模型只加载一次)
SERVICE: LLMService = None


class ChatHandler(BaseHTTPRequestHandler):
    """HTTP 处理器"""

    def log_message(self, format, *args):
        """覆盖默认日志(用 stderr)"""
        sys.stderr.write(f"[{time.strftime('%H:%M:%S')}] {self.address_string()} {format % args}\n")
        sys.stderr.flush()

    def do_GET(self):
        """健康检查"""
        if self.path == "/health":
            self._json_response({"status": "ok", "model": SERVICE.model_id if SERVICE else "loading"})
        else:
            self._json_response({"error": "GET only /health"}, code=404)

    def do_POST(self):
        """聊天"""
        if self.path != "/chat":
            self._json_response({"error": "POST only /chat"}, code=404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            req = json.loads(body)
            system = req.get("system", "你是 CoPiano,AI 钢琴老师。")
            user = req.get("user", "")
            max_tokens = int(req.get("max_tokens", 200))

            if not user:
                self._json_response({"error": "user field required"}, code=400)
                return

            text, dt = SERVICE.chat(system, user, max_tokens)
            self._json_response({
                "text": text,
                "elapsed_s": round(dt, 2),
                "chars": len(text),
            })
        except Exception as e:
            self._json_response({"error": str(e)}, code=500)

    def _json_response(self, obj: dict, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen/Qwen2.5-7B-Instruct")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1", help="默认只 listen localhost(SSH 内访问)")
    args = parser.parse_args()

    global SERVICE
    SERVICE = LLMService(args.model)

    server = ThreadingHTTPServer((args.host, args.port), ChatHandler)
    print(f"[daemon] listening on http://{args.host}:{args.port}", flush=True)
    print(f"[daemon] send POST /chat with {{system, user, max_tokens}}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[daemon] shutting down", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
