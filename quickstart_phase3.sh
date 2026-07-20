#!/bin/bash
# quickstart_phase3.sh — CoPiano Phase 3 一键体验(自适应推荐闭环)
#
# 5 分钟跑完 Phase 1+2+3 完整闭环:
# 1. 检查环境 + 测试 MIDI
# 2. 准备 5 首曲子的虚拟 history(若没有)
# 3. 跑 copiano.py + 聚类 + 推荐(GPU 模式)
# 4. 生成 8 段报告
# 5. 摘要展示
#
# 用法:
#   bash quickstart_phase3.sh                # Mac 端无 LLM
#   bash quickstart_phase3.sh --gpu          # 走 GPU 端(完整 LLM,~3 分钟)
#   bash quickstart_phase3.sh --no-history   # 不预置 history,用户自己跑

set -e
cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

banner() {
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║  CoPiano Phase 3 — 自适应推荐闭环    ║"
    echo "║  5 分钟体验聚类 + Bandit 推荐          ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
}

usage() {
    banner
    echo "用法:"
    echo "  bash quickstart_phase3.sh                # Mac 端,无 LLM"
    echo "  bash quickstart_phase3.sh --gpu          # 走 GPU 4090,完整 LLM"
    echo "  bash quickstart_phase3.sh --no-history   # 不预置 5 首 history"
    echo ""
}

MODE="mac"
PRESET_HISTORY=true
case "${1:-}" in
    --gpu) MODE="gpu" ;;
    --no-history) PRESET_HISTORY=false ;;
    --help|-h) usage; exit 0 ;;
    "") MODE="mac" ;;
    *) echo "未知参数: $1"; usage; exit 1 ;;
esac

banner
echo "模式: $MODE | 预置 history: $PRESET_HISTORY"
echo "时间: $(date)"
echo ""

# 1. 环境
echo "→ Step 1/5: 环境检查"
if ! command -v python3 >/dev/null; then
    echo -e "${RED}❌ python3 未安装${NC}"; exit 1
fi
PY=python3
$PY -c "import sklearn, hdbscan, mido, music21" 2>/dev/null || {
    echo -e "${RED}❌ 缺依赖,跑:${NC}"
    echo "  python3 -m pip install --user scikit-learn hdbscan mido pretty_midi miditok music21"
    exit 1
}
echo -e "  ${GREEN}✓${NC} Python + sklearn + hdbscan + mido + music21"

# 2. 测试 MIDI
echo ""
echo "→ Step 2/5: 测试 MIDI"
if [ ! -f /tmp/test_ref.mid ] || [ ! -f /tmp/test_user.mid ]; then
    $PY scripts/gen_test_midi.py
fi
[ -f /tmp/test_ref.mid ] && [ -f /tmp/test_user.mid ] && \
    echo -e "  ${GREEN}✓${NC} test_ref.mid / test_user.mid" || {
    echo -e "${RED}❌ 测试 MIDI 缺失${NC}"; exit 1
}

# 3. 准备 history
echo ""
echo "→ Step 3/5: 历史数据准备"
HISTORY="/tmp/copiano_history.json"
if [ "$PRESET_HISTORY" = true ]; then
    # 写 5 首虚拟 history(覆盖不同 cluster)
    cat > $HISTORY <<'JSON'
[
  {"piece": "Minuet in G", "period": "Baroque", "score": 93.5, "pitch_accuracy": 0.875, "timing_std_ms": 10.8, "timing_mean_ms": -6.3, "velocity_correlation": 0.0, "n_pitch_errors": 1},
  {"piece": "Sonata K.545", "period": "Classical", "score": 78.0, "pitch_accuracy": 0.80, "timing_std_ms": 60.0, "timing_mean_ms": -20.0, "velocity_correlation": 0.3, "n_pitch_errors": 3},
  {"piece": "Für Elise", "period": "Classical", "score": 88.0, "pitch_accuracy": 0.92, "timing_std_ms": 25.0, "timing_mean_ms": 5.0, "velocity_correlation": 0.1, "n_pitch_errors": 1},
  {"piece": "Nocturne Op.9", "period": "Romantic", "score": 65.0, "pitch_accuracy": 0.70, "timing_std_ms": 80.0, "timing_mean_ms": -50.0, "velocity_correlation": 0.2, "n_pitch_errors": 5},
  {"piece": "Träumerei", "period": "Romantic", "score": 82.0, "pitch_accuracy": 0.85, "timing_std_ms": 30.0, "timing_mean_ms": -10.0, "velocity_correlation": 0.4, "n_pitch_errors": 2}
]
JSON
    echo -e "  ${GREEN}✓${NC} 预置 5 首 history($HISTORY)"
else
    if [ ! -f $HISTORY ]; then
        echo -e "${YELLOW}⚠${NC} history 不存在,需要 --save-history 几次累积"
    else
        N=$(python3 -c "import json; print(len(json.load(open('$HISTORY'))))")
        echo -e "  ${GREEN}✓${NC} 已有 $N 条 history"
    fi
fi

# 4. 跑 copiano + 聚类 + 推荐
echo ""
echo "→ Step 4/5: 端到端 pipeline(评估 + 风格 + 对齐 + KG + LLM + 聚类 + 推荐)"
OUT_JSON="/tmp/copiano_phase3.json"
OUT_MD="/tmp/copiano_phase3_report.md"

if [ "$MODE" = "gpu" ]; then
    echo "  走 GPU (AutoDL 4090)..."
    # 上传测试 MIDI 和 history
    ./scripts/gpu.sh "mkdir -p /root/autodl-tmp/copiano/data" 2>&1 | tail -1
    expect -c "
set timeout 30
spawn scp -P 29955 -o StrictHostKeyChecking=no /tmp/test_ref.mid /tmp/test_user.mid $HISTORY root@connect.bjb2.seetacloud.com:/root/autodl-tmp/copiano/data/
expect \"password:\"
send \"vEOra3BpuGhC\\r\"
expect eof
" 2>&1 | tail -1

    # 上传脚本
    for f in eval_pitch align_score tonnetz_kg style_analyzer llm_feedback feedback_aggregator error_cluster bandit_recommend copiano report; do
        scp -q -P 29955 -o StrictHostKeyChecking=no scripts/$f.py root@connect.bjb2.seetacloud.com:/root/autodl-tmp/copiano/code/scripts/ 2>/dev/null || true
    done

    # 跑
    ./scripts/gpu_run.sh "cd /root/autodl-tmp/copiano/code/scripts && /root/autodl-tmp/conda-envs/copiano/bin/python -u copiano.py /root/autodl-tmp/copiano/data/test_ref.mid /root/autodl-tmp/copiano/data/test_user.mid --piece 'Minuet in G' --model qwen/Qwen2.5-7B-Instruct --aggregated --cluster-history --recommend --output /root/autodl-tmp/copiano/data/copiano_phase3.json 2>&1 && /root/autodl-tmp/conda-envs/copiano/bin/python -u report.py /root/autodl-tmp/copiano/data/copiano_phase3.json /root/autodl-tmp/copiano/data/copiano_phase3_report.md 2>&1" 300 2>&1 | tail -30

    # 拷回
    expect -c "
set timeout 30
spawn scp -P 29955 -o StrictHostKeyChecking=no root@connect.bjb2.seetacloud.com:/root/autodl-tmp/copiano/data/copiano_phase3.json $OUT_JSON
expect \"password:\"
send \"vEOra3BpuGhC\\r\"
expect eof
" 2>&1 | tail -1
    expect -c "
set timeout 30
spawn scp -P 29955 -o StrictHostKeyChecking=no root@connect.bjb2.seetacloud.com:/root/autodl-tmp/copiano/data/copiano_phase3_report.md $OUT_MD
expect \"password:\"
send \"vEOra3BpuGhC\\r\"
expect eof
" 2>&1 | tail -1
else
    echo "  Mac 端跑(无 LLM)..."
    $PY scripts/copiano.py /tmp/test_ref.mid /tmp/test_user.mid \
        --piece "Minuet in G" --no-llm \
        --cluster-history --recommend \
        --output $OUT_JSON
    $PY scripts/report.py $OUT_JSON $OUT_MD
fi

# 5. 摘要
echo ""
echo "→ Step 5/5: 摘要"
if [ -f $OUT_MD ]; then
    SIZE=$(wc -c < $OUT_MD)
    echo -e "  ${GREEN}✓${NC} 报告生成:${OUT_MD} (${SIZE} 字符)"
    echo ""
    echo -e "  ${YELLOW}报告摘要(4 关键段):${NC}"
    echo -e "  ${GREEN}1. 总览:${NC} $(grep -A0 '总分:' $OUT_MD | head -1 | sed 's/.*\*\*//;s/\*\*.*//')"
    echo -e "  ${GREEN}4.7 聚类:${NC} $(grep '簇数' $OUT_MD | head -1 | sed 's/.*| //' | head -c 80)"
    echo -e "  ${GREEN}4.8 推荐:${NC}"
    grep -E "^\| [1-3] " $OUT_MD | head -3 | sed 's/^/      /'
fi

echo ""
echo -e "${YELLOW}💡 下一步${NC}:"
echo "  - 看完整报告: cat $OUT_MD"
echo "  - 看完整 JSON: cat $OUT_JSON | jq"
echo "  - 跑健康检查: bash quickstart.sh --check"
echo "  - 看 USAGE.md: cat USAGE.md"
echo ""
echo -e "${GREEN}✨ Phase 3 完整闭环 demo 完成!${NC}"
