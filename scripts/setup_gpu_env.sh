#!/usr/bin/expect -f
# setup_gpu_env.sh — 一次性把 conda envs 路径改到数据盘,建 copiano env
# 用法: setup_gpu_env.sh
set timeout 600

spawn ssh -p 29955 -o StrictHostKeyChecking=no -o ConnectTimeout=8 root@connect.bjb2.seetacloud.com
expect "password:"
send "vEOra3BpuGhC\r"
expect "\$ "

# 1. conda envs 改到数据盘
send "mkdir -p /root/autodl-tmp/conda-envs && conda config --add envs_dirs /root/autodl-tmp/conda-envs && conda env config vars set CONDA_PKGS_DIRS=/root/autodl-tmp/conda-pkgs && echo CONDA_CONFIG_OK\r"
expect "\$ "

# 2. 建 copiano env (Python 3.11,匹配 torch 2.x)
send "conda create -p /root/autodl-tmp/conda-envs/copiano python=3.11 -y 2>&1 | tail -5\r"
expect "\$ "

# 3. 装核心包(后台)
send "source activate /root/autodl-tmp/conda-envs/copiano && pip install --no-cache-dir torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu121 2>&1 | tail -3 && echo PYTORCH_OK\r"
expect "\$ "

# 4. 装 music + LLM 栈
send "source activate /root/autodl-tmp/conda-envs/copiano && pip install --no-cache-dir transformers peft accelerate datasets sentence-transformers 2>&1 | tail -3 && echo HF_OK\r"
expect "\$ "

send "source activate /root/autodl-tmp/conda-envs/copiano && pip install --no-cache-dir librosa pretty_midi mido miditok music21 pydub 2>&1 | tail -3 && echo MUSIC_OK\r"
expect "\$ "

send "exit\r"
expect eof
