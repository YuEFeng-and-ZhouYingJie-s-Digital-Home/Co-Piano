# CoPiano v3 — Makefile
# 用法: make <target>
# 默认: make help

# 颜色
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m

# Python
PYTHON ?= python3
SCRIPTS = scripts

.DEFAULT_GOAL := help

.PHONY: help
help: ## 显示帮助
	@echo -e "$(BLUE)CoPiano v3 — Makefile$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# === 安装 ===

.PHONY: install
install: ## 安装核心依赖
	bash setup.sh --core-only

.PHONY: install-full
install-full: ## 安装全部依赖 (含 LLM + Audio + Dev)
	bash setup.sh

.PHONY: install-llm
install-llm: ## + LLM 依赖
	bash setup.sh --llm

.PHONY: install-audio
install-audio: ## + 音频依赖
	bash setup.sh --audio

.PHONY: install-dev
install-dev: ## + 开发依赖
	bash setup.sh --dev

# === 演示 ===

.PHONY: demo
demo: ## 端到端 demo (5 维 + 7d 课程 + RCT + voice)
	$(PYTHON) $(SCRIPTS)/copiano_v3.py demo

.PHONY: demo-senior
demo-senior: ## 端到端 demo (age=65, 银发模式)
	$(PYTHON) $(SCRIPTS)/copiano_v3.py demo --age 65

.PHONY: modules
modules: ## 列出所有 10 模块
	$(PYTHON) $(SCRIPTS)/copiano_v3.py modules

# === 课程 ===

.PHONY: curriculum
curriculum: ## 生成 7 天课程
	$(PYTHON) $(SCRIPTS)/copiano_v3.py curriculum

.PHONY: curriculum-senior
curriculum-senior: ## 7 天课程 (银发)
	$(PYTHON) $(SCRIPTS)/copiano_v3.py curriculum --age 65

# === A/B 测试 ===

.PHONY: abtest
abtest: ## A/B 测试 30/group × 7 days
	$(PYTHON) $(SCRIPTS)/copiano_v3.py abtest --n 30

.PHONY: abtest-quick
abtest-quick: ## A/B 测试 5/group × 3 days (快)
	$(PYTHON) $(SCRIPTS)/copiano_v3.py abtest --n 5 --days 3

.PHONY: scores
scores: ## 5 维评分模拟
	$(PYTHON) $(SCRIPTS)/copiano_v3.py scores

# === 测试 ===

.PHONY: test
test: ## 跑所有 cycle 测试 (8/13)
	@for n in 1 2 3 4 5 6 7 8 13; do \
		echo -e "$(BLUE)cycle$${n}_test:$(NC)"; \
		$(PYTHON) $(SCRIPTS)/cycle$${n}_test.py 2>&1 | tail -3; \
		echo ""; \
	done

.PHONY: test-cycle1
test-cycle1: ## Cycle 1 测试 (节拍器)
	$(PYTHON) $(SCRIPTS)/cycle1_test.py

.PHONY: test-cycle6
test-cycle6: ## Cycle 6 测试 (视奏)
	$(PYTHON) $(SCRIPTS)/cycle6_test.py

.PHONY: test-cycle8
test-cycle8: ## Cycle 8 测试 (A/B)
	$(PYTHON) $(SCRIPTS)/cycle8_test.py

.PHONY: test-all
test-all: ## 跑所有测试 + 详细输出
	@for n in 1 2 3 4 5 6 7 8 13; do \
		echo -e "$(BLUE)═══ cycle$${n}_test ═══$(NC)"; \
		$(PYTHON) $(SCRIPTS)/cycle$${n}_test.py 2>&1 | tail -5; \
		echo ""; \
	done

# === 基准 + 图表 ===

.PHONY: bench
bench: ## 性能基准 (13 模块)
	$(PYTHON) $(SCRIPTS)/benchmarks.py

.PHONY: bench-quick
bench-quick: ## 性能基准 (5 关键模块)
	$(PYTHON) $(SCRIPTS)/benchmarks.py --quick

.PHONY: figures
figures: ## 重新生成 6 论文图表
	$(PYTHON) $(SCRIPTS)/paper_figures.py --output-dir notes/figures/

.PHONY: data
data: ## 生成 60 学生真实化测试数据
	$(PYTHON) $(SCRIPTS)/test_data_generator.py --n 30 --abtest

# === 维护 ===

.PHONY: clean
clean: ## 清理临时文件
	rm -f /tmp/test_*.mid /tmp/cycle*.log
	rm -rf __pycache__/ .pytest_cache/ */__pycache__/ */*/__pycache__/
	@echo -e "$(GREEN)✅ 清理完成$(NC)"

.PHONY: clean-figures
clean-figures: ## 清理图表
	rm -f notes/figures/*.png notes/figures/*.svg notes/figures/*.json
	@echo -e "$(GREEN)✅ 图表清理完成$(NC)"

# === 发布 ===

.PHONY: release
release: ## 一键发布 (测试 + 基准 + 图表 + tag)
	bash release.sh

.PHONY: release-dry
release-dry: ## 发布 dry-run (不实际修改)
	bash release.sh --dry-run

# === 文档 ===

.PHONY: docs
docs: ## 打开文档
	@echo "📚 CoPiano 文档:"
	@echo "  README.md           - 主文档"
	@echo "  CHANGELOG.md        - 变更日志"
	@echo "  notes/arxiv_abstract_v3.md - 论文 v3 草稿"
	@echo "  notes/benchmark_report.md   - 性能报告"
	@echo "  notes/figures/       - 6 论文图表"
	@ls README.md CHANGELOG.md notes/arxiv_abstract_v3.md notes/benchmark_report.md 2>&1 | sed 's/^/  /'

.PHONY: count
count: ## 统计代码行数 + 论文数
	@echo -e "$(BLUE)代码统计:$(NC)"
	@echo "  Python 脚本: $$(find $(SCRIPTS) -name '*.py' | wc -l | tr -d ' ')"
	@echo "  代码行数:   $$(find $(SCRIPTS) -name '*.py' -exec cat {} \; | wc -l | tr -d ' ')"
	@echo "  测试脚本:   $$(find $(SCRIPTS) -name '*test*.py' | wc -l | tr -d ' ')"
	@echo "  知识库:     $$(find notes/ -name '*.md' | wc -l | tr -d ' ')"
	@echo "  论文图表:   $$(ls notes/figures/*.png 2>/dev/null | wc -l | tr -d ' ')"
	@echo ""
	@echo -e "$(BLUE)Git 统计:$(NC)"
	@git log --oneline | head -20
