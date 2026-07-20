#!/bin/bash
# hf_env.sh — HF 镜像环境配置(必须 source 之后才能用)
# 用法: source scripts/hf_env.sh
# 或在 Python 里: os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
export HF_ENDPOINT=https://hf-mirror.com
export HF_HOME=/root/autodl-tmp/hf-cache
export TRANSFORMERS_CACHE=/root/autodl-tmp/hf-cache
# 备选:ModelScope 阿里镜像(国内更快,但 API 不同)
# pip install modelscope
echo "HF 镜像配置: HF_ENDPOINT=$HF_ENDPOINT"
echo "HF cache: $HF_HOME"
