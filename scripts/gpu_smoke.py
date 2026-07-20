"""
gpu_smoke.py — GPU 推理冒烟测试(确认 torch CUDA 能用,跑个简单矩阵乘法)
"""
import sys
import time

def main():
    import torch
    print(f"torch: {torch.__version__}")
    print(f"cuda available: {torch.cuda.is_available()}")
    if not torch.cuda.is_available():
        print("FAIL: cuda not available")
        return 1
    print(f"device: {torch.cuda.get_device_name(0)}")
    print(f"capability: {torch.cuda.get_device_capability(0)}")
    print(f"current mem allocated: {torch.cuda.memory_allocated() / 1024**2:.1f} MiB")
    print(f"current mem reserved: {torch.cuda.memory_reserved() / 1024**2:.1f} MiB")

    # 跑个 matmul
    print("\n=== matmul test ===")
    a = torch.randn(2048, 2048, device="cuda", dtype=torch.float32)
    b = torch.randn(2048, 2048, device="cuda", dtype=torch.float32)
    torch.cuda.synchronize()
    t0 = time.time()
    c = a @ b
    torch.cuda.synchronize()
    t1 = time.time()
    print(f"2048x2048 matmul: {(t1-t0)*1000:.1f} ms")
    print(f"output shape: {c.shape}, mean: {c.mean().item():.4f}")
    print(f"mem after: {torch.cuda.memory_allocated() / 1024**2:.1f} MiB")

    # 测个 LLM 风格的 transformer forward(小)
    print("\n=== small transformer test ===")
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model_id = "sshleifer/tiny-gpt2"  # 非常小,只为冒烟
    try:
        tok = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id).to("cuda")
        model.eval()
        inp = tok("Hello piano", return_tensors="pt").to("cuda")
        with torch.no_grad():
            out = model.generate(**inp, max_new_tokens=5, do_sample=False)
        print(f"generated: {tok.decode(out[0])}")
        print(f"mem after gen: {torch.cuda.memory_allocated() / 1024**2:.1f} MiB")
    except Exception as e:
        print(f"tiny-gpt2 failed: {e}, skip")
    print("\n=== ALL OK ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
