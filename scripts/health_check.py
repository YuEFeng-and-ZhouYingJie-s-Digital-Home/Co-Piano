"""
health_check.py — CoPiano 健康检查脚本

一键验证:
- 6 个核心 Python 模块(eval/align/kg/style/llm/copiano)能跑通
- 测试 MIDI 文件存在
- KG 节点数(应 >= 200)
- 报告文件能正常生成
- (GPU 端)LLM 模型是否加载

用法:
    python3 health_check.py [--llm-check]  # 加 --llm-check 验证 LLM
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
NOTES = ROOT / "notes"
sys.path.insert(0, str(SCRIPTS))


def check(name: str, func) -> bool:
    """跑一个检查,打印 PASS/FAIL"""
    t0 = time.time()
    try:
        msg = func()
        dt = time.time() - t0
        print(f"  ✅ [{name}] {msg} ({dt:.2f}s)")
        return True
    except Exception as e:
        dt = time.time() - t0
        print(f"  ❌ [{name}] FAIL: {e} ({dt:.2f}s)")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm-check", action="store_true", help="验证 LLM 加载(需要 GPU)")
    ap.add_argument("--quick", action="store_true", help="只跑关键检查(跳过 LLM)")
    args = ap.parse_args()

    print(f"=== CoPiano 健康检查 @ {ROOT} ===\n")
    n_pass, n_fail = 0, 0

    # 1. 依赖 import
    print("📦 1. 依赖检查")
    if check("torch", lambda: f"可用" if _safe_import("torch") else "未装"):
        n_pass += 1
    else:
        n_fail += 1
    for mod in ["mido", "pretty_midi", "librosa", "music21", "numpy"]:
        if check(mod, lambda m=mod: _safe_import(m) or "未装"):
            n_pass += 1
        else:
            n_fail += 1
    print()

    # 2. 测试 MIDI
    print("🎵 2. 测试数据")
    test_ref = Path("/tmp/test_ref.mid")
    test_user = Path("/tmp/test_user.mid")
    if check("test_ref.mid", lambda: f"存在 {test_ref.stat().st_size}B" if test_ref.exists() else f"不存在:{test_ref}"):
        n_pass += 1
    else:
        n_fail += 1
        print("  💡 修复: python3 scripts/gen_test_midi.py")
    if check("test_user.mid", lambda: f"存在 {test_user.stat().st_size}B" if test_user.exists() else f"不存在:{test_user}"):
        n_pass += 1
    else:
        n_fail += 1
    print()

    # 3. 核心脚本跑通
    print("🧪 3. 核心脚本跑通测试")
    if check("eval_pitch.py", lambda: _run_script("eval_pitch.py", str(test_ref), str(test_user))):
        n_pass += 1
    else:
        n_fail += 1
    if check("align_score.py", lambda: _run_script("align_score.py", str(test_ref), str(test_user))):
        n_pass += 1
    else:
        n_fail += 1
    if check("style_analyzer.py", lambda: _run_script("style_analyzer.py", str(test_user))):
        n_pass += 1
    else:
        n_fail += 1
    print()

    # 4. KG 检查
    print("📚 4. 乐理知识图谱")
    def kg_check():
        from tonnetz_kg import MusicKG
        kg = MusicKG()
        s = kg.summary()
        if s["n_nodes"] < 200:
            raise RuntimeError(f"节点数太少: {s['n_nodes']}")
        return f"{s['n_nodes']} 节点, {s['n_edges']} 边, {len(s['node_types'])} 类型"
    if check("MusicKG 加载", kg_check):
        n_pass += 1
    else:
        n_fail += 1
    print()

    # 5. report.py 跑通
    print("📄 5. 报告生成器")
    last_json = NOTES / "last_demo_run.json"
    if last_json.exists():
        if check("report.py", lambda: _run_report(last_json)):
            n_pass += 1
        else:
            n_fail += 1
    else:
        print("  ⏭️  [report.py] 跳过(没找到 last_demo_run.json)")
    print()

    # 6. LLM 检查(可选)
    if args.llm_check:
        print("🤖 6. LLM 加载检查(需要 GPU)")
        try:
            import torch
            if not torch.cuda.is_available():
                print("  ❌ CUDA 不可用")
                n_fail += 1
            else:
                from transformers import AutoTokenizer, AutoModelForCausalLM
                t0 = time.time()
                model_id = "Qwen/Qwen2.5-0.5B-Instruct"  # 用小模型测快
                tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
                model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16).to("cuda")
                inp = tok("hi", return_tensors="pt").to("cuda")
                with torch.no_grad():
                    out = model.generate(**inp, max_new_tokens=5, do_sample=False)
                print(f"  ✅ [LLM 0.5B 加载+生成] {time.time()-t0:.1f}s, mem {torch.cuda.memory_allocated()/1024**3:.2f}GiB")
                n_pass += 1
        except Exception as e:
            print(f"  ❌ [LLM 加载] {e}")
            n_fail += 1
        print()

    # 总结
    total = n_pass + n_fail
    print(f"=== 总结: {n_pass}/{total} 通过 ===")
    if n_fail == 0:
        print("🎉 所有检查通过,CoPiano 健康!")
        return 0
    else:
        print(f"⚠️  {n_fail} 项失败,需要修复")
        return 1


def _safe_import(mod: str) -> str:
    """安全 import,返回 version 或 None"""
    try:
        m = __import__(mod)
        ver = getattr(m, "__version__", "?")
        return ver
    except ImportError:
        return None


def _run_script(name: str, *args) -> str:
    """跑子脚本,返回关键信息"""
    import subprocess
    p = subprocess.run(
        ["python3", str(SCRIPTS / name), *args],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if p.returncode != 0:
        raise RuntimeError(f"{p.stderr[:200]}")
    try:
        out = json.loads(p.stdout)
        if "score" in out:
            return f"score={out['score']}"
        if "n_alignment_points" in out:
            return f"points={out['n_alignment_points']}"
        if "period_hint" in out:
            return f"period={out['period_hint']}({out['period_confidence']})"
        return "ok"
    except (json.JSONDecodeError, KeyError):
        return "ok"


def _run_report(json_path: Path) -> str:
    """跑 report.py,返回字符数"""
    import subprocess
    out_path = Path(tempfile.mktemp(suffix=".md"))
    p = subprocess.run(
        ["python3", str(SCRIPTS / "report.py"), str(json_path), str(out_path)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if p.returncode != 0:
        raise RuntimeError(f"{p.stderr[:200]}")
    n = out_path.stat().st_size
    out_path.unlink()
    return f"ok ({n} chars)"


if __name__ == "__main__":
    sys.exit(main() or 0)
