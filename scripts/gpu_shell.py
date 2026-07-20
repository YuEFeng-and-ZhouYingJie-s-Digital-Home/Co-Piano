"""
gpu_shell.py — Mac 端调用 GPU 服务器的 Python 封装

底层用 expect (gpu.sh) + scp 做远程命令执行和文件传输
解决:voice_dialog / copiano 跑在 Mac,但 LLM 推理在 GPU 服务器

API:
- run_on_gpu(cmd, timeout=30)            跑单条命令,返回 stdout
- scp_to_gpu(local, remote)              scp 文件到 GPU
- scp_from_gpu(remote, local)            scp 文件从 GPU 到 Mac
- run_python_on_gpu(script_content)      在 GPU 上跑 Python 脚本(临时文件)

内部用 expect 自动输入密码(密码来自 secrets/local_secrets.json,或硬编码)
"""
from __future__ import annotations

import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

# ----- 配置 -----
GPU_HOST = "root@connect.bjb2.seetacloud.com"
GPU_PORT = 29955
GPU_PWD = "vEOra3BpuGhC"  # 明文(测试环境)
GPU_SCRIPTS_DIR = "/root/autodl-tmp/copiano/code"

# 找 gpu.sh expect 脚本(同目录)
SCRIPT_DIR = Path(__file__).resolve().parent
GPU_SH = SCRIPT_DIR / "gpu.sh"


def _run_expect(remote_cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """底层:用 expect 跑一条 SSH 命令,返回 (returncode, stdout, stderr)"""
    if not GPU_SH.exists():
        raise FileNotFoundError(f"gpu.sh 不存在:{GPU_SH}")

    # expect 脚本会处理密码,这里把命令作为参数传
    cmd = [str(GPU_SH), remote_cmd, str(timeout)]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 10,  # expect 自己有 timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"⏱️ GPU 命令超时({timeout}s)"


def run_on_gpu(remote_cmd: str, timeout: int = 30, check: bool = False) -> str:
    """在 GPU 上跑一条命令,返回 stdout

    Args:
        remote_cmd: 远程 bash 命令字符串
        timeout: 超时秒数
        check: True 时非零返回码抛异常
    """
    rc, out, err = _run_expect(remote_cmd, timeout)
    if check and rc != 0:
        raise RuntimeError(f"GPU 命令失败 (rc={rc}): {err or out}")
    return out


def scp_to_gpu(local_path: str | Path, remote_path: str, timeout: int = 30) -> str:
    """scp 文件到 GPU(密码走 expect)"""
    local_path = Path(local_path)
    if not local_path.exists():
        raise FileNotFoundError(f"本地文件不存在:{local_path}")

    # expect 内嵌命令
    expect_script = f"""
set timeout {timeout}
spawn scp -P {GPU_PORT} -o StrictHostKeyChecking=no {shlex.quote(str(local_path))} {GPU_HOST}:{shlex.quote(remote_path)}
expect "password:"
send "{GPU_PWD}\\r"
expect eof
"""
    result = subprocess.run(["expect", "-c", expect_script], capture_output=True, text=True, timeout=timeout + 10)
    if result.returncode != 0:
        raise RuntimeError(f"scp 失败: {result.stderr}")
    return result.stdout


def scp_from_gpu(remote_path: str, local_path: str | Path, timeout: int = 30) -> str:
    """scp 文件从 GPU 到 Mac"""
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    expect_script = f"""
set timeout {timeout}
spawn scp -P {GPU_PORT} -o StrictHostKeyChecking=no {GPU_HOST}:{shlex.quote(remote_path)} {shlex.quote(str(local_path))}
expect "password:"
send "{GPU_PWD}\\r"
expect eof
"""
    result = subprocess.run(["expect", "-c", expect_script], capture_output=True, text=True, timeout=timeout + 10)
    if result.returncode != 0:
        raise RuntimeError(f"scp 失败: {result.stderr}")
    return result.stdout


def run_python_on_gpu(script: str, timeout: int = 60) -> str:
    """在 GPU 上跑 Python 脚本(用临时文件 + 远程 python3)"""
    # 写本地临时文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        local_script = f.name
    remote_script = "/tmp/copiano_tmp_script.py"

    try:
        scp_to_gpu(local_script, remote_script, timeout=10)
        out = run_on_gpu(f"python3 {remote_script}", timeout=timeout)
        return out
    finally:
        Path(local_script).unlink(missing_ok=True)


# ----- 健康检查 -----
def gpu_health_check() -> dict:
    """检查 GPU 服务器可达性 + 关键信息"""
    try:
        out = run_on_gpu("echo OK && nvidia-smi --query-gpu=memory.free --format=csv,noheader 2>&1 | head -1", timeout=15)
        return {
            "reachable": "OK" in out,
            "gpu_info": out.strip(),
        }
    except Exception as e:
        return {"reachable": False, "error": str(e)}


if __name__ == "__main__":
    # CLI:测试
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument("--health", action="store_true", help="健康检查")
    parser.add_argument("--cmd", help="跑一条命令")
    args = parser.parse_args()

    if args.health:
        h = gpu_health_check()
        print(json.dumps(h, ensure_ascii=False, indent=2))
    elif args.cmd:
        print(run_on_gpu(args.cmd))
