#!/bin/bash
# quickstart.sh — CoPiano 一键体验脚本
#
# 5 分钟从 0 到完整 demo:
# 1. 检查环境(python / GPU)
# 2. 生成测试 MIDI(若无)
# 3. 跑端到端 demo(评估 + 风格 + 对齐 + KG RAG + 7B LLM + 报告)
# 4. 输出 Markdown 报告
#
# 用法:
#   bash quickstart.sh                # Mac 端跑(无 LLM)
#   bash quickstart.sh --with-llm     # Mac 端拼好 prompt,但不调 LLM
#   bash quickstart.sh --gpu          # 走 GPU 端(SSH 调 AutoDL 4090)
#   bash quickstart.sh --check        # 只跑健康检查,不出报告

set -e
cd "$(dirname "$0")"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

banner() {
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║      CoPiano — AI 古典钢琴教练         ║"
    echo "║      Quickstart (5 分钟体验)            ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
}

usage() {
    banner
    echo "用法:"
    echo "  bash quickstart.sh                # Mac 端跑(MPS,无 LLM)"
    echo "  bash quickstart.sh --with-llm     # Mac 端跑(无 LLM,但拼 prompt)"
    echo "  bash quickstart.sh --gpu          # 走 GPU 端(AutoDL 4090)"
    echo "  bash quickstart.sh --check       # 只跑健康检查"
    echo "  bash quickstart.sh --help        # 帮助"
    echo ""
}

MODE="mac"
case "${1:-}" in
    --gpu) MODE="gpu" ;;
    --check) MODE="check" ;;
    --with-llm) MODE="llm-prompt" ;;
    --help|-h) usage; exit 0 ;;
    "") MODE="mac" ;;
    *) echo "未知参数: $1"; usage; exit 1 ;;
esac

banner
echo "模式: $MODE"
echo "时间: $(date)"
echo ""

# 1. 环境检查
echo "→ Step 1/5: 环境检查"
if ! command -v python3 >/dev/null; then
    echo -e "${RED}❌ python3 未安装${NC}"
    exit 1
fi
PY=python3
PYVER=$($PY --version 2>&1)
echo -e "  ${GREEN}✓${NC} $PYVER"

if [ "$MODE" = "gpu" ]; then
    if ! command -v expect >/dev/null; then
        echo -e "${RED}❌ expect 未安装(brew install expect)${NC}"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} expect 可用"
fi

# 2. 测试 MIDI
echo ""
echo "→ Step 2/5: 测试 MIDI"
if [ ! -f /tmp/test_ref.mid ] || [ ! -f /tmp/test_user.mid ]; then
    echo "  生成测试 MIDI..."
    $PY scripts/gen_test_midi.py
fi
if [ -f /tmp/test_ref.mid ] && [ -f /tmp/test_user.mid ]; then
    echo -e "  ${GREEN}✓${NC} test_ref.mid / test_user.mid 已就绪"
else
    echo -e "${RED}❌ 测试 MIDI 生成失败${NC}"
    exit 1
fi

# 3. 跑端到端
echo ""
echo "→ Step 3/5: 端到端 pipeline"
if [ "$MODE" = "check" ]; then
    $PY scripts/health_check.py
    exit 0
fi

OUT_JSON="/tmp/copiano_demo.json"
OUT_MD="/tmp/copiano_demo_report.md"

if [ "$MODE" = "gpu" ]; then
    echo "  通过 GPU (AutoDL 4090) 跑..."
    # 上传测试 MIDI 到 GPU
    ./scripts/gpu.sh "mkdir -p /root/autodl-tmp/copiano/data" 2>&1 | tail -1
    expect -c "
set timeout 30
spawn scp -P 29955 -o StrictHostKeyChecking=no /tmp/test_ref.mid /tmp/test_user.mid root@connect.bjb2.seetacloud.com:/root/autodl-tmp/copiano/data/
expect \"password:\"
send \"vEOra3BpuGhC\\r\"
expect eof
" 2>&1 | tail -1

    # 上传脚本
    for f in eval_pitch align_score tonnetz_kg style_analyzer llm_feedback feedback_aggregator copiano report; do
        scp -q -P 29955 -o StrictHostKeyChecking=no scripts/$f.py root@connect.bjb2.seetacloud.com:/root/autodl-tmp/copiano/code/scripts/
    done
    echo "  跑 copiano.py + report.py..."
    ./scripts/gpu_run.sh "cd /root/autodl-tmp/copiano/code/scripts && /root/autodl-tmp/conda-envs/copiano/bin/python -u copiano.py /root/autodl-tmp/copiano/data/test_ref.mid /root/autodl-tmp/copiano/data/test_user.mid --piece 'Minuet in G' --model qwen/Qwen2.5-7B-Instruct --aggregated --output /root/autodl-tmp/copiano/data/copiano_demo.json 2>&1 && /root/autodl-tmp/conda-envs/copiano/bin/python -u report.py /root/autodl-tmp/copiano/data/copiano_demo.json /root/autodl-tmp/copiano/data/copiano_demo_report.md 2>&1" 300 2>&1 | tail -30

    # 拷回
    expect -c "
set timeout 30
spawn scp -P 29955 -o StrictHostKeyChecking=no root@connect.bjb2.seetacloud.com:/root/autodl-tmp/copiano/data/copiano_demo.json $OUT_JSON
expect \"password:\"
send \"vEOra3BpuGhC\\r\"
expect eof
" 2>&1 | tail -1
    expect -c "
set timeout 30
spawn scp -P 29955 -o StrictHostKeyChecking=no root@connect.bjb2.seetacloud.com:/root/autodl-tmp/copiano/data/copiano_demo_report.md $OUT_MD
expect \"password:\"
send \"vEOra3BpuGhC\\r\"
expect eof
" 2>&1 | tail -1
elif [ "$MODE" = "llm-prompt" ]; then
    echo "  跑 copiano.py (无 LLM,只拼 prompt)..."
    $PY scripts/copiano.py /tmp/test_ref.mid /tmp/test_user.mid --piece "Minuet in G" --no-llm --output $OUT_JSON
    $PY scripts/report.py $OUT_JSON $OUT_MD
else
    echo "  跑 copiano.py (无 LLM,Mac 端 MPS 不支持 LLM)..."
    $PY scripts/copiano.py /tmp/test_ref.mid /tmp/test_user.mid --piece "Minuet in G" --no-llm --output $OUT_JSON
    $PY scripts/report.py $OUT_JSON $OUT_MD
fi

# 4. 显示摘要
echo ""
echo "→ Step 4/5: 结果摘要"
if [ -f $OUT_MD ]; then
    SIZE=$(wc -c < $OUT_MD)
    echo -e "  ${GREEN}✓${NC} 报告生成:${OUT_MD} (${SIZE} 字符)"
    if [ "$MODE" != "check" ]; then
        # 提取分数
        SCORE=$(grep -E "总分:" $OUT_MD | head -1 | sed 's/.*总分: \([0-9.]*\).*/\1/')
        ERR=$(grep -E "错音准确率" $OUT_MD | head -1 | sed 's/.*错音准确率.*| \([0-9.]*%\).*/\1/')
        PERIOD=$(grep -E "时期线索" $OUT_MD | head -1 | sed 's/.*时期线索.*| \([A-Za-z]*\).*/\1/')
        echo "    - 总分: $SCORE / 100"
        echo "    - 错音: $ERR"
        echo "    - 时期: $PERIOD"
    fi
fi

# 5. 提示
echo ""
echo "→ Step 5/5: 下一步"
echo "  📄 完整报告:$OUT_MD"
echo "  📦 完整 JSON:$OUT_JSON"
echo ""
echo -e "${YELLOW}💡 提示${NC}:"
echo "  - 想看完整报告: cat $OUT_MD"
echo "  - 想看 LLM 反馈(需 GPU): bash quickstart.sh --gpu"
echo "  - 想跑健康检查: bash quickstart.sh --check"
echo "  - 想看 README: cat README.md"
echo ""
echo -e "${GREEN}✨ CoPiano demo 完成!${NC}"
