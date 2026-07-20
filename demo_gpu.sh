#!/bin/bash
# demo_gpu.sh — CoPiano 稳定 GPU demo 命令链
#
# 解决 quickstart.sh scp 链被 SSH 中断的问题
# 拆分成 5 个独立步骤,每步可重试
#
# 流程:
# 1. 上传测试 MIDI 到 GPU(2 个文件,分别 scp)
# 2. 上传核心 Python 脚本到 GPU(10 个,逐个 scp)
# 3. GPU 端跑 copiano.py(9 步 + 7B LLM + 聚类 + 推荐)
# 4. GPU 端跑 report.py(生成 8 段 Markdown 报告)
# 5. 拷回 JSON + 报告到 Mac
#
# 用法:
#   bash demo_gpu.sh                # 跑 Phase 1+2 完整 demo
#   bash demo_gpu.sh --no-llm      # 不调 LLM,只评估+聚类+推荐
#   bash demo_gpu.sh --piece X     # 改曲目(默认 Minuet in G)
#   bash demo_gpu.sh --skip-upload # 跳过上传(脚本已存在时)
#   bash demo_gpu.sh --skip-run    # 跳过运行(只拷回结果)
#   bash demo_gpu.sh --all         # 包含 Phase 3 history 预置(5 首)

set -e
cd "$(dirname "$0")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

banner() {
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║  CoPiano 稳定 GPU demo                ║"
    echo "║  (解决 quickstart.sh scp 中断问题)    ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
}

# 默认参数
NO_LLM=false
PIECE="Minuet in G"
SKIP_UPLOAD=false
SKIP_RUN=false
USE_HISTORY=false
GPU_HOST="root@connect.bjb2.seetacloud.com"
GPU_PORT="29955"
GPU_PASSWORD="vEOra3BpuGhC"
GPU_DATA="/root/autodl-tmp/copiano/data"
GPU_SCRIPTS="/root/autodl-tmp/copiano/code/scripts"
GPU_PYTHON="/root/autodl-tmp/conda-envs/copiano/bin/python"

# 解析参数
for arg in "$@"; do
    case $arg in
        --no-llm) NO_LLM=true ;;
        --piece=*) PIECE="${arg#*=}" ;;
        --piece) shift; PIECE="$1" ;;
        --skip-upload) SKIP_UPLOAD=true ;;
        --skip-run) SKIP_RUN=true ;;
        --all) USE_HISTORY=true ;;
        --help|-h)
            banner
            echo "用法: bash demo_gpu.sh [options]"
            echo ""
            echo "选项:"
            echo "  --no-llm        不调 LLM,只跑评估 + 聚类 + 推荐"
            echo "  --piece NAME     改曲目(默认: Minuet in G)"
            echo "  --skip-upload    跳过上传(脚本/MIDI 已存在时)"
            echo "  --skip-run       跳过运行(只拷回结果)"
            echo "  --all            预置 Phase 3 history(5 首虚拟)"
            echo "  --help           帮助"
            exit 0 ;;
        *) echo "未知参数: $arg"; exit 1 ;;
    esac
done

banner
echo "曲目: $PIECE"
echo "LLM: $([ "$NO_LLM" = true ] && echo 'NO' || echo 'YES (Qwen 7B)')"
echo "预置 history: $USE_HISTORY"
echo "时间: $(date)"
echo ""

# sshpass 风格:ssh 一次性命令 + expect eof
scp_file() {
    local local_path="$1"
    local remote_path="$2"
    expect -c "
set timeout 30
spawn scp -P $GPU_PORT -o StrictHostKeyChecking=no \"$local_path\" \"$GPU_HOST:$remote_path\"
expect \"password:\"
send \"$GPU_PASSWORD\\r\"
expect eof
" 2>&1 | tail -1
}

ssh_cmd() {
    expect -c "
set timeout ${1:-30}
spawn ssh -p $GPU_PORT -o StrictHostKeyChecking=no -o ConnectTimeout=8 $GPU_HOST \"$2\"
expect \"password:\"
send \"$GPU_PASSWORD\\r\"
expect eof
" 2>&1 | tail -5
}

# 1) 上传测试 MIDI
if [ "$SKIP_UPLOAD" = false ]; then
    echo "→ Step 1/5: 上传测试 MIDI"
    if [ ! -f /tmp/test_ref.mid ] || [ ! -f /tmp/test_user.mid ]; then
        echo "  生成测试 MIDI..."
        python3 scripts/gen_test_midi.py
    fi
    ssh_cmd 10 "mkdir -p $GPU_DATA $GPU_SCRIPTS" > /dev/null
    scp_file /tmp/test_ref.mid $GPU_DATA/
    scp_file /tmp/test_user.mid $GPU_DATA/
    echo -e "  ${GREEN}✓${NC} MIDI 上传完成"
else
    echo "→ Step 1/5: 跳过(已 --skip-upload)"
fi

# 2) 上传核心脚本
if [ "$SKIP_UPLOAD" = false ]; then
    echo ""
    echo "→ Step 2/5: 上传 10 个核心脚本"
    for f in eval_pitch align_score tonnetz_kg style_analyzer llm_feedback feedback_aggregator error_cluster bandit_recommend copiano report; do
        scp_file scripts/$f.py $GPU_SCRIPTS/ > /dev/null
        echo -n "."
    done
    echo ""
    echo -e "  ${GREEN}✓${NC} 10 个脚本上传完成"
fi

# 3) 预置 history(可选)
if [ "$USE_HISTORY" = true ]; then
    echo ""
    echo "→ Step 2.5/5: 预置 Phase 3 history(5 首虚拟)"
    cat > /tmp/copiano_history.json <<'JSON'
[
  {"piece": "Minuet in G", "period": "Baroque", "score": 93.5, "pitch_accuracy": 0.875, "timing_std_ms": 10.8, "timing_mean_ms": -6.3, "velocity_correlation": 0.0, "n_pitch_errors": 1},
  {"piece": "Sonata K.545", "period": "Classical", "score": 78.0, "pitch_accuracy": 0.80, "timing_std_ms": 60.0, "timing_mean_ms": -20.0, "velocity_correlation": 0.3, "n_pitch_errors": 3},
  {"piece": "Für Elise", "period": "Classical", "score": 88.0, "pitch_accuracy": 0.92, "timing_std_ms": 25.0, "timing_mean_ms": 5.0, "velocity_correlation": 0.1, "n_pitch_errors": 1},
  {"piece": "Nocturne Op.9", "period": "Romantic", "score": 65.0, "pitch_accuracy": 0.70, "timing_std_ms": 80.0, "timing_mean_ms": -50.0, "velocity_correlation": 0.2, "n_pitch_errors": 5},
  {"piece": "Träumerei", "period": "Romantic", "score": 82.0, "pitch_accuracy": 0.85, "timing_std_ms": 30.0, "timing_mean_ms": -10.0, "velocity_correlation": 0.4, "n_pitch_errors": 2}
]
JSON
    scp_file /tmp/copiano_history.json $GPU_DATA/
    echo -e "  ${GREEN}✓${NC} history 上传完成"
fi

# 4) 跑 copiano.py + report.py
if [ "$SKIP_RUN" = false ]; then
    echo ""
    echo "→ Step 3/5: GPU 跑 copiano.py(9 步 + 7B LLM + 聚类 + 推荐)"
    EXTRA_FLAGS=""
    if [ "$NO_LLM" = true ]; then
        EXTRA_FLAGS="--no-llm"
    else
        EXTRA_FLAGS="--model qwen/Qwen2.5-7B-Instruct"
    fi
    if [ "$USE_HISTORY" = true ]; then
        EXTRA_FLAGS="$EXTRA_FLAGS --cluster-history --recommend --aggregated"
    fi

    echo "  命令: $EXTRA_FLAGS"
    ssh_cmd 300 "cd $GPU_SCRIPTS && $GPU_PYTHON -u copiano.py $GPU_DATA/test_ref.mid $GPU_DATA/test_user.mid --piece '$PIECE' $EXTRA_FLAGS --output $GPU_DATA/live_demo.json && $GPU_PYTHON -u report.py $GPU_DATA/live_demo.json $GPU_DATA/live_demo_report.md && echo GPU_DONE"

    echo ""
    echo "→ Step 4/5: 跑 report.py(已完成)"
    echo -e "  ${GREEN}✓${NC} GPU 跑通"
else
    echo ""
    echo "→ Step 3-4/5: 跳过(已 --skip-run)"
fi

# 5) 拷回
echo ""
echo "→ Step 5/5: 拷回结果"
scp_file $GPU_DATA/live_demo.json /tmp/
scp_file $GPU_DATA/live_demo_report.md /tmp/
# 也拷到项目 notes/
cp /tmp/live_demo.json /tmp/live_demo_report.md notes/
echo -e "  ${GREEN}✓${NC} 结果已拷回"

# 摘要
echo ""
echo "=== 摘要 ==="
if [ -f /tmp/live_demo.json ]; then
    python3 -c "
import json
r = json.load(open('/tmp/live_demo.json'))
print(f\"曲目: {r['piece']['name']} ({r['piece']['composer']})\")
print(f\"评估: score {r['eval']['score']}, 错音 {r['eval']['n_pitch_errors']}\")
print(f\"风格: {r['style'].get('key', '?')}, 时期 {r['style'].get('period_hint', '?')}\")
if 'cluster' in r:
    print(f\"聚类: K={r['cluster']['n_clusters']}, silhouette {r['cluster']['silhouette_score']}\")
if 'recommendations' in r:
    print(f\"推荐: {len(r['recommendations'])} 首,首推 {r['recommendations'][0]['piece']}\")
if 'llm_response' in r:
    print(f\"LLM 反馈: {len(r['llm_response'])} 字\")
" 2>/dev/null
fi

echo ""
echo "📄 完整报告: notes/live_demo_report.md"
echo "📦 完整 JSON: notes/live_demo.json"
echo "   (或 /tmp/live_demo_*.md / .json)"
echo ""
echo -e "${GREEN}✨ 完成!${NC}"
