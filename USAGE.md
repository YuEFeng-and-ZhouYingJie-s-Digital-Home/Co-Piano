# CoPiano 使用指南

> **5 分钟从 0 到完整 AI 钢琴教练体验** — 47 轮 cron 推进后的最终交付
>
> **Phase 1+2+3 全部完结** — 评估 / 反馈 / 自适应 完整闭环

---

## ⚡ 一行启动(最常用)

```bash
cd ~/piano-ai-corpus

# Mac 端无 LLM(~5 秒)
bash quickstart.sh

# GPU 端 + 完整 LLM(~3 分钟)
bash quickstart.sh --gpu

# 健康检查
bash quickstart.sh --check
```

---

## 📦 项目结构

```
piano-ai-corpus/
├── README.md              # 项目说明
├── USAGE.md               # 本文件(使用指南)
├── plan.md                # 完整开发方案
├── progress.md            # 22 轮 cron 决策日志
├── quickstart.sh          # 一键体验(5 步)
├── index.md               # 113 篇 arxiv 论文清单
├── core_papers.md         # 高相关 Top80 摘要
├── relevance_ranking.md   # 全打分排序
│
├── papers/                # 138 篇 arxiv 论文元数据
│
├── scripts/               # 14 个核心 Python 脚本
│   ├── copiano.py              ⭐ 端到端 CLI(主入口)
│   ├── eval_pitch.py           🎵 MIDI 评估
│   ├── align_score.py          📐 乐谱对齐
│   ├── style_analyzer.py       🎼 风格分析
│   ├── tonnetz_kg.py           📚 乐理 KG(241 节点)
│   ├── llm_feedback.py         🤖 LLM Prompt 组装
│   ├── llm_call_ms.py          ⚡ ModelScope 调 Qwen
│   ├── feedback_aggregator.py  📊 多小节聚合
│   ├── report.py               📄 Markdown 报告
│   ├── llm_self_eval.py        🔍 LLM 自评
│   ├── health_check.py         ✅ 13/13 健康检查
│   ├── midi_capture.py         🎤 实时 MIDI 采集
│   ├── gen_test_midi.py        🧪 测试 MIDI 生成
│   ├── fetch_arxiv.py          🔍 arxiv 抓取
│   └── gpu.sh                  🔧 SSH helper
│
├── notes/
│   ├── kg_export.json          # 乐理 KG 导出
│   ├── feedback_prompt_demo.json  # LLM prompt 样例
│   ├── copiano_7b_demo_report.md  # 7B 完整 demo 报告
│   ├── copiano_full_report.md     # 双 LLM 完整报告
│   ├── last_demo_run.json        # 端到端 demo 输出
│   ├── llm_comparison.md         # 1.5B vs 7B 对比
│   ├── phase2_report.md          # Phase 1+2 完成报告
│   ├── experiments.md / weekly-log.md
│
└── experiments/            # 实验数据(待用)
```

---

## 🎯 核心功能(4 层架构)

### L1 多模态感知
- **MIDI 评估** (`eval_pitch.py`):错音 / 节奏 / 力度 / 完整度
- **乐谱对齐** (`align_score.py`):DTW 算法,17 个对齐点
- **MIDI 实时采集** (`midi_capture.py`):list / record / watch 三种模式

### L2 风格评估
- **风格分析** (`style_analyzer.py`):调性 / 速度 / 拍号 / 织体
- **时期线索启发式**:Baroque / Classical / Romantic 自动判断
- **KG RAG** (`tonnetz_kg.py`):241 节点 / 9 类型 / 6 查询函数

### L3 自适应推荐 ✅
- **错误模式聚类** (`error_cluster.py`):KMeans + HDBSCAN,8 维特征
- **Contextual Bandit** (`bandit_recommend.py`):UCB 算法 + 5 cluster 策略
- **反馈聚合器** (`feedback_aggregator.py`):多小节 + 全曲级综合
- 自动识别错音热点 / 弱项小节 / 强项小节
- 自动生成整体判断 + 下一步推荐

### L4 LLM 教学反馈
- **Prompt 组装** (`llm_feedback.py`):评估 + KG RAG → 结构化 prompt
- **Qwen 7B 推理** (`llm_call_ms.py`):14.23 GiB,3.0s 171 字
- **双 LLM 反馈**:小节级 + 全曲级(用 `--aggregated`)
- **LLM 自评** (`llm_self_eval.py`):4 维评分闭环

---

## 📖 典型使用场景

### 场景 1:快速验证系统(~5 秒)
```bash
bash quickstart.sh
# 输出:/tmp/copiano_demo_report.md
cat /tmp/copiano_demo_report.md
```

### 场景 2:完整 LLM demo(~3 分钟,推荐)
```bash
bash quickstart.sh --gpu
# 自动:scp 测试 MIDI → GPU 跑 copiano.py → 调 Qwen 7B → 拷回报告
```

### 场景 3:自己的 MIDI 文件
```bash
# 把你的 MIDI 放 /tmp/
cp my_recording.mid /tmp/user.mid
cp reference_performance.mid /tmp/ref.mid

# 跑端到端
python3 scripts/copiano.py /tmp/ref.mid /tmp/user.mid \
  --piece "Minuet in G" \
  --model qwen/Qwen2.5-7B-Instruct \
  --aggregated \
  --output /tmp/my_result.json

# 生成报告
python3 scripts/report.py /tmp/my_result.json /tmp/my_report.md
cat /tmp/my_report.md
```

### 场景 4:接 MIDI 键盘实时评估
```bash
# 1) 接 USB-MIDI 转换器到 Mac
# 2) 列设备
python3 scripts/midi_capture.py list
# 输出:[0] USB MIDI Device

# 3) 录音
python3 scripts/midi_capture.py record /tmp/my_playing.mid USB
# 弹完 Ctrl+C 停止

# 4) 评估
python3 scripts/copiano.py reference.mid /tmp/my_playing.mid --piece "..."
```

### 场景 5:批量评估多首
```bash
for piece in "Minuet in G" "Nocturne Op.9 No.2" "Für Elise"; do
  python3 scripts/copiano.py data/${piece}_ref.mid data/${piece}_user.mid \
    --piece "$piece" --no-llm --output results/${piece}.json
done

# 生成所有报告
for f in results/*.json; do
  python3 scripts/report.py "$f" "${f%.json}.md"
done
```

### 场景 5.5:Phase 3 自适应推荐(完整闭环)
```bash
# 1) 多次评估累积历史
for piece in "Minuet in G" "Sonata K.545" "Für Elise" "Nocturne Op.9" "Träumerei"; do
  python3 scripts/copiano.py ref.mid user.mid --piece "$piece" --no-llm --save-history
done

# 2) 跑聚类 + 推荐 + 报告
python3 scripts/copiano.py ref.mid user.mid --piece "Minuet in G" \
  --no-llm --cluster-history --recommend \
  --output /tmp/p3_demo.json
python3 scripts/report.py /tmp/p3_demo.json /tmp/p3_demo_report.md

# 输出报告(8 段,含聚类 + 推荐)
cat /tmp/p3_demo_report.md
```

**报告新增段落**:
- **4.7 错误模式聚类** — 5 首曲子的簇 ID 分布
- **4.8 下一步推荐** — Bandit 推荐的 3 首下一首 + UCB 评分

### 场景 6:LLM 自评(反馈质量评估)
```bash
# 把反馈写到文件
cat > /tmp/feedback.txt <<'EOF'
你这段肖邦第 13 小节左手应该再轻一点,像在叹息。
EOF

# 跑自评
python3 scripts/llm_self_eval.py /tmp/feedback.txt --context eval.json
# 输出:JSON 评分 + 改进建议
```

---

## 🛠️ 维护命令

### 健康检查
```bash
python3 scripts/health_check.py           # 13/13 基础
python3 scripts/health_check.py --llm-check  # 含 LLM 加载
python3 scripts/health_check.py --quick     # 快速模式
```

### GPU 操作
```bash
# 看 GPU 状态
./scripts/gpu.sh "nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv"

# 看 Qwen 7B 状态
./scripts/gpu.sh "ps aux | grep python | head -5"

# 手动跑 LLM
./scripts/gpu.sh "/root/autodl-tmp/conda-envs/copiano/bin/python /root/autodl-tmp/copiano/code/llm_call_ms.py qwen/Qwen2.5-7B-Instruct /tmp/prompt.json 300"
```

### 重装环境(如果出问题)
```bash
# GPU 端 conda env 重装
./scripts/gpu.sh "/root/autodl-tmp/conda-envs/copiano/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 60 mido pretty_midi miditok music21"

# Mac 端依赖
python3 -m pip install --user mido python-rtmidi pretty_midi librosa music21
```

---

## 🧪 已知限制 + 未来工作

### 限制
1. **数据自产限制**: 测试 MIDI 是合成的,真实钢琴数据需用户接 MIDI 键盘
2. **macOS 实时 MIDI 采集**: 需 USB-MIDI 转换器(脚本可立即用)
3. **LLM 上下文窗口**: Qwen 7B 是 32K 上下文,大型乐曲可能需分段
4. **风格识别 0.71 置信度**: 简单启发式,可训练 ML 模型改进
5. **UCB 评分需真实数据**: Bandit 初始全部 "inf",需用户练新曲后给奖励

### 未来工作(Phase 4+)
- [x] ~~错误模式聚类~~ ✅ Phase 3 完成
- [x] ~~Contextual Bandit 推荐~~ ✅ Phase 3 完成
- [ ] 表现力评估(微调 PianoCoRe 数据)
- [ ] MAESTRO 数据集训练(供 AMT 基线)
- [ ] 实时反馈(< 200ms,Mac 流式推理)
- [ ] 视频手型(MediaPipe Hands + Pose)
- [ ] Mac App(SwiftUI)
- [ ] Web 端(Next.js)
- [ ] arxiv 投稿草稿(基于 47 轮 cron 产出)

---

## 📊 性能指标

| 模块 | 时间 | 资源 |
|------|------|------|
| MIDI 评估 | < 100ms | Mac |
| 乐谱对齐 | ~50ms | Mac |
| 风格分析 | ~500ms | Mac |
| KG RAG | < 10ms | Mac |
| Prompt 组装 | < 10ms | Mac |
| **错误聚类** | **< 50ms** | **Mac** |
| **Bandit 推荐** | **< 10ms** | **Mac** |
| Qwen 7B 推理 | 3.0s / 171 字 | GPU 14G |
| 端到端(无 LLM) | < 1s | Mac |
| 端到端(含 LLM) | ~6s | Mac + GPU |
| 端到端(完整 9 步 + LLM + 聚类 + 推荐) | ~10s | Mac + GPU |
| 双 LLM 反馈 | ~10s | GPU |
| LLM 自评 | ~3s | GPU |
| 健康检查 | ~3s | Mac |

---

## 🔗 关键文件位置

| 文件 | 用途 |
|------|------|
| `quickstart.sh` | **一行启动** |
| `scripts/copiano.py` | 端到端 CLI(主入口) |
| `scripts/health_check.py` | 健康检查 |
| `plan.md` | 完整开发方案 |
| `progress.md` | 22 轮 cron 决策日志 |
| `notes/phase2_report.md` | Phase 1+2 完成报告 |
| `notes/copiano_full_report.md` | 双 LLM 完整报告(7B) |
| `notes/llm_comparison.md` | 1.5B vs 7B 对比 |
| `notes/kg_export.json` | 241 节点乐理 KG 导出 |

---

## 📞 常见问题

**Q: 报告里拍号显示 `<music21.meter.TimeSignature 4/4>` 怎么办?**
A: 已修复(用 `ratioString` 字段)。如果还看到,跑 `python3 -m pip install --user --upgrade music21`

**Q: GPU 端 7B 加载慢?**
A: 第一次 ~5 分钟,加载后缓存。后续 3.0s 推理。

**Q: 想换更大的 LLM?**
A: `copiano.py --model qwen/Qwen2.5-14B-Instruct`(需要 28G 显存,可能不够)

**Q: MIDI 设备没显示?**
A: 检查 USB-MIDI 转换器连接,或用 IAC Driver 创虚拟设备(Mac 音频 MIDI 设置)

**Q: 想增加 KG 知识?**
A: 编辑 `scripts/tonnetz_kg.py` 的 PIECES / COMPOSERS / PERIODS,或扩展为外部 JSON

---

## 🎓 论文参考(精选 10)

| ID | 引用 |
|----|------|
| 2405.13527 | End-to-End Real-World Polyphonic Piano A2S(AMT SOTA) |
| 2605.06627 | PianoCoRe(钢琴 MIDI 数据集) |
| 2606.12282 | PianoKontext(表现力渲染) |
| 2601.11968 | MuseAgent(LLM 音乐理解) |
| 2606.22708 | Libretto(LLM 音乐结构) |
| 2605.20014 | Audio-to-Score Alignment |
| 2511.03425 | SyMuPe(表现力符号化) |
| 2606.20198 | Pitch Spelling Classical Piano |
| 2605.13431 | Text2Score |
| 2606.13626 | Bach Generative |

详见 `core_papers.md`(Top80 摘要)。

---

*CoPiano - 让 AI 老师"会因材施教"。47 轮 cron 推进,Phase 1+2+3 完整端到端跑通。*
*项目位置: `~/piano-ai-corpus/`*
