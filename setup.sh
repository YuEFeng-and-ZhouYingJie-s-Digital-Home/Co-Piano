#!/bin/bash
# CoPiano v3 — 一键安装脚本
# 用法: bash setup.sh [--core-only] [--llm] [--audio] [--dev]
# 默认: 全部安装

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 默认安装选项
INSTALL_CORE=true
INSTALL_LLM=false
INSTALL_AUDIO=false
INSTALL_DEV=false
INSTALL_FULL=true

# 解析参数
for arg in "$@"; do
    case $arg in
        --core-only)
            INSTALL_FULL=false
            ;;
        --llm)
            INSTALL_LLM=true
            INSTALL_FULL=false
            ;;
        --audio)
            INSTALL_AUDIO=true
            INSTALL_FULL=false
            ;;
        --dev)
            INSTALL_DEV=true
            INSTALL_FULL=false
            ;;
        --help)
            echo "用法: bash setup.sh [--core-only] [--llm] [--audio] [--dev]"
            echo ""
            echo "选项:"
            echo "  --core-only   仅核心依赖 (默认开)"
            echo "  --llm         + LLM (Qwen 7B + faster-whisper)"
            echo "  --audio       + 音频 (sounddevice + librosa)"
            echo "  --dev         + 开发 (pytest + black)"
            echo ""
            echo "默认 (无参数): core + llm + audio + dev (完整)"
            exit 0
            ;;
    esac
done

if [ "$INSTALL_FULL" = true ]; then
    INSTALL_CORE=true
    INSTALL_LLM=true
    INSTALL_AUDIO=true
    INSTALL_DEV=true
fi

# 标题
echo -e "${BLUE}"
echo "  _____          _      ____             "
echo " / ____|        | |    |  _ \            "
echo "| |     ___   __| | ___| |_) | ___  _ __"
echo "| |    / _ \ / _\` |/ _ \  _ < / _ \| '__|"
echo "| |___| (_) | (_| |  __/ |_) | (_) | |   "
echo " \_____\___/ \__,_|\___|____/ \___/|_|   "
echo -e "                                       v3.0${NC}"
echo ""

# 检查 Python
PYTHON=${PYTHON:-python3}
echo -e "${BLUE}📋 环境检查${NC}"
$PYTHON --version || { echo -e "${RED}❌ Python 3.10+ 未安装${NC}"; exit 1; }
echo ""

# 创建 venv (可选,推荐)
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}💡 创建 Python 虚拟环境 venv/ (推荐)${NC}"
    read -p "是否创建? (y/n, 默认 y): " CREATE_VENV
    CREATE_VENV=${CREATE_VENV:-y}
    if [ "$CREATE_VENV" = "y" ]; then
        $PYTHON -m venv venv
        source venv/bin/activate
        echo -e "${GREEN}✅ venv 已创建并激活${NC}"
        PYTHON=python
    fi
fi
echo ""

# 升级 pip
echo -e "${BLUE}📦 升级 pip${NC}"
$PYTHON -m pip install --upgrade pip wheel setuptools 2>&1 | tail -3
echo ""

# Core
if [ "$INSTALL_CORE" = true ]; then
    echo -e "${BLUE}📦 安装 Core 依赖 (numpy, scipy, pretty_midi, music21, ...)${NC}"
    $PYTHON -m pip install -r requirements.txt 2>&1 | tail -3 || {
        # 失败时手动装核心
        $PYTHON -m pip install numpy scipy matplotlib pretty_midi mido music21 scikit-learn edge-tts aiohttp
    }
    echo -e "${GREEN}✅ Core 依赖已安装${NC}"
fi

# LLM
if [ "$INSTALL_LLM" = true ]; then
    echo -e "${BLUE}🤖 安装 LLM 依赖 (torch, transformers, faster-whisper)${NC}"
    $PYTHON -m pip install torch transformers modelscope accelerate faster-whisper 2>&1 | tail -3
    echo -e "${GREEN}✅ LLM 依赖已安装${NC}"
fi

# Audio
if [ "$INSTALL_AUDIO" = true ]; then
    echo -e "${BLUE}🎤 安装 Audio 依赖 (sounddevice, librosa, pydub)${NC}"
    $PYTHON -m pip install sounddevice librosa soundfile pydub 2>&1 | tail -3
    echo -e "${GREEN}✅ Audio 依赖已安装${NC}"
fi

# Dev
if [ "$INSTALL_DEV" = true ]; then
    echo -e "${BLUE}🧪 安装 Dev 依赖 (pytest, black, mypy)${NC}"
    $PYTHON -m pip install pytest pytest-cov mypy black flake8 2>&1 | tail -3
    echo -e "${GREEN}✅ Dev 依赖已安装${NC}"
fi

# 验证
echo ""
echo -e "${BLUE}🔍 验证安装${NC}"
$PYTHON -c "
import sys
print(f'Python: {sys.version.split()[0]}')
deps = []
try:
    import numpy; deps.append(f'numpy {numpy.__version__}')
except: pass
try:
    import pretty_midi; deps.append(f'pretty_midi {pretty_midi.__version__}')
except: pass
try:
    import music21; deps.append(f'music21 {music21.__version__}')
except: pass
try:
    import matplotlib; deps.append(f'matplotlib {matplotlib.__version__}')
except: pass
try:
    import edge_tts; deps.append(f'edge-tts OK')
except: pass
print('已安装:', ', '.join(deps) if deps else '(无)')
"

# 测试 CoPiano
echo ""
echo -e "${BLUE}🎹 测试 CoPiano${NC}"
$PYTHON scripts/copiano_v3.py modules 2>&1 | head -15
echo ""

# 完成
echo -e "${GREEN}"
echo "✅ CoPiano v3 安装完成!"
echo ""
echo "下一步:"
echo "  source venv/bin/activate    # 如果用了 venv"
echo "  python3 scripts/copiano_v3.py demo   # 端到端 demo"
echo "  python3 scripts/copiano_v3.py abtest --n 30   # A/B 测试"
echo ""
echo "详细文档: README.md + CHANGELOG.md"
echo -e "${NC}"
