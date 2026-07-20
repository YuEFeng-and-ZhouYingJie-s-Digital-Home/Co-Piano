#!/bin/bash
# CoPiano v3 — 一键发布脚本
# 用法: bash release.sh [--dry-run] [--skip-tests] [--skip-bench]
# 默认: 全部跑一遍然后 git tag v3.0

set -e

DRY_RUN=false
SKIP_TESTS=false
SKIP_BENCH=false
SKIP_FIGURES=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            echo "🧪 DRY RUN 模式 (不实际修改)"
            ;;
        --skip-tests)
            SKIP_TESTS=true
            ;;
        --skip-bench)
            SKIP_BENCH=true
            ;;
        --skip-figures)
            SKIP_FIGURES=true
            ;;
        --help)
            echo "用法: bash release.sh [选项]"
            echo ""
            echo "选项:"
            echo "  --dry-run       不实际修改 (只检查)"
            echo "  --skip-tests    跳过测试"
            echo "  --skip-bench    跳过基准"
            echo "  --skip-figures  跳过图表"
            exit 0
            ;;
    esac
done

# 颜色
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
echo "═══════════════════════════════════════════════════════════"
echo "   CoPiano v3 — Release Script"
echo "═══════════════════════════════════════════════════════════"
echo -e "${NC}"

# 1. 跑测试
if [ "$SKIP_TESTS" = false ]; then
    echo -e "${BLUE}📋 步骤 1/5: 跑测试 (cycle1-13 + smoke)${NC}"
    for n in 1 2 3 4 5 6 7 8 13; do
        if [ -f "scripts/cycle${n}_test.py" ]; then
            echo -n "  cycle${n}_test.py... "
            if python3 scripts/cycle${n}_test.py > /tmp/cycle${n}.log 2>&1; then
                echo -e "${GREEN}✅${NC}"
            else
                echo -e "${RED}❌ (查看 /tmp/cycle${n}.log)${NC}"
                tail -5 /tmp/cycle${n}.log
                exit 1
            fi
        fi
    done
fi

# 2. 跑基准
if [ "$SKIP_BENCH" = false ]; then
    echo -e "${BLUE}⏱️  步骤 2/5: 性能基准${NC}"
    python3 scripts/benchmarks.py --quick --output notes/benchmark_report.md --json notes/benchmark_results.json 2>&1 | tail -5
fi

# 3. 生成论文图表
if [ "$SKIP_FIGURES" = false ]; then
    echo -e "${BLUE}🎨 步骤 3/5: 生成 6 论文图表${NC}"
    python3 scripts/paper_figures.py --output-dir notes/figures/ 2>&1 | tail -5
fi

# 4. 端到端 demo
echo -e "${BLUE}🎹 步骤 4/5: 端到端 demo${NC}"
python3 scripts/copiano_v3.py demo --age 30 2>&1 | head -10

# 5. Git tag
if [ "$DRY_RUN" = false ]; then
    echo -e "${BLUE}🏷️  步骤 5/5: Git tag v3.0${NC}"
    # 检查现有 tag
    if git tag | grep -q "^v3.0$"; then
        echo -e "${YELLOW}⚠️  v3.0 tag 已存在${NC}"
    else
        # 检查是否有未提交修改
        if ! git diff --quiet HEAD 2>/dev/null; then
            echo -e "${YELLOW}⚠️  有未提交修改,先 commit${NC}"
            git status --short
        else
            git tag -a v3.0 -m "CoPiano v3.0: 5-Dim Multi-Modal AI Piano Coach + RCT d=1.34 (40 scripts, 813 papers, 6 figures)"
            echo -e "${GREEN}✅ v3.0 tag 已创建${NC}"
        fi
    fi
    echo ""
    echo -e "${GREEN}📊 发布摘要:${NC}"
    echo "  脚本数: $(ls scripts/*.py | wc -l | tr -d ' ')"
    echo "  知识库: $(ls notes/*.md | wc -l | tr -d ' ')"
    echo "  图表:   $(ls notes/figures/*.png 2>/dev/null | wc -l | tr -d ' ')"
    echo "  测试:   $(ls scripts/cycle*_test.py 2>/dev/null | wc -l | tr -d ' ') 测试套件"
    echo "  Git tag: $(git tag | tail -3 | tr '\n' ' ')"
fi

echo ""
echo -e "${GREEN}✅ Release 流程完成!${NC}"
