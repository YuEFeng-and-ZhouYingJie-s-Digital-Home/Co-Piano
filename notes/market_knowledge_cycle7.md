# Phase 6 CYCLE 7 — 7 天课程深度扩展 调研知识库

> **目标**: 把 v3.0 5 维模块 (音高/表现力/手型/银发/视奏) 整合为统一 7 天自适应课程
> **日期**: 2026-07-21
> **方向**: 现有 curriculum.py 只排 "主曲 + 复习" 2 段,无多模态/无间隔复习/无自适应

---

## 1. 调研范围

| 维度 | 内容 | 来源 |
|------|------|------|
| 间隔复习 | 扇贝网遗忘曲线 + Anki 算法 | 扇贝产品文档 |
| AI 自适应 | Take Space AI + DSuit 智能选择 | takespace.com |
| 钢琴产品 | SAMICK KPOP Piano / Simply Piano / Flowkey | 行业产品 |
| 教学理论 | Maslow 需求层次 / Bloom 分类学 / Deliberate Practice | 教学经典 |
| v3.0 现状 | 5 维模块已实现,缺统一调度 | CoPiano 内部 |

---

## 2. 标杆产品

### 2.1 SAMICK KPOP Piano APP (三益乐器)
- **5 大练习模式**:五线谱 / 简谱 / 游戏 / 视奏 / 跟弹
- **8 大辅助功能**:
  - 速度调节 (0.5x-2x)
  - 选定区域反复练
  - 自动翻谱
  - 分手练习
  - 自由移调
  - 无线蓝牙
  - AI 实时纠错 (节拍/准确度/速度三维反馈)
  - 评分系统
- **曲库**:KPOP 100首 + 古典 1000首
- **AI 反馈**:节拍/准确度/演奏速度 三维分析

### 2.2 Simply Piano (JoyTunes)
- **课程模式**:传统课程 + 流行曲 + 视奏
- **AI 反馈**:实时音准 + 节奏
- **进度**:分章节 课程,12 章约 200+ 节
- **缺**:无多模态 (手型/表现力)

### 2.3 Flowkey
- **视频 + 跟弹**:真人示范
- **3 难度**:Beginner / Intermediate / Advanced
- **曲库**:1500+ 流行 + 古典
- **缺**:无 AI 自适应,固定难度

---

## 3. 教学理论 3 大支柱

### 3.1 间隔重复 (Spaced Repetition)
- **算法**:Ebbinghaus 遗忘曲线 — t 时刻记忆保留 R = e^(-t/S)
- **实践**:SM-2 算法 (Anki) — 根据回忆难度调整下次复习间隔
- **钢琴应用**:
  - 一首曲子 1 天后复习 (R~0.4)
  - 3 天后再复习 (R~0.6)
  - 7 天后 (R~0.8)
  - 14 天后 (R~0.9)
  - 30 天后 (R~0.95)

### 3.2 刻意练习 (Deliberate Practice, Ericsson 1993)
- 4 要素:
  1. **明确目标** (specific goal)
  2. **专注** (focused attention)
  3. **即时反馈** (immediate feedback)
  4. **走出舒适区** (stretch beyond comfort)
- **钢琴应用**:
  - 每日 1-2 个小目标 (不是大目标)
  - 弱项专练占 20-30%
  - 主曲 30-40%
  - 复习 20-30%

### 3.3 多模态学习 (Multimodal Learning)
- 视觉 + 听觉 + 触觉 + 动觉 + 认知
- **钢琴应用**:
  - 视觉:看谱 + 视奏
  - 听觉:听示范 + 听自己
  - 触觉:键感
  - 动觉:手型/姿势
  - 认知:调性/和声分析

---

## 4. v3.0 现状 + 整合空白

### 4.1 已有 5 维模块
1. **音高** (eval_pitch.py + midi_analyzer.py) — 错音/音准/节奏
2. **表现力** (expressiveness_analyzer.py, C3) — 9 维 (timing/dynamics/articulation/pedal/...)
3. **手型** (hand_pose_analyzer.py, C4) — 9 维 (wrist/arch/curl/thumb/...)
4. **银发模式** (senior_mode.py, C5) — 4 开关 (TTS/LLM/timeout/encouragement)
5. **视奏** (sight_reading_trainer.py, C6) — 4 难度 × 3 模式 × 3 输入

### 4.2 整合空白
- **0 统一调度**:5 个模块各自独立,无 daily plan
- **0 间隔复习**:无 spaced repetition
- **0 自适应难度**:curriculum 用固定 4 档
- **0 弱项检测**:weak_areas 只用 pitch errors
- **0 银发整合**:senior mode 与 curriculum 解耦
- **0 进度追踪**:无 daily goals + achievement 系统

### 4.3 CoPiano 差异化
- **唯一多模态自适应**:业界首个整合 5 维的 AI 钢琴课程
- **间隔复习**:类 Anki 但专用于音乐
- **弱项检测**:用 expressiveness/hand_pose 多维数据
- **银发整合**:senior mode 自动按 age 触发
- **每日目标**:具体可量化 (e.g. "Bach Prelude m.4-8 错音 < 1")

---

## 5. Cycle 7 stage 2 实施目标

### 5.1 模块: `scripts/curriculum_v2.py`

### 5.2 核心类
- `DayPlanV2` (扩展 DayPlan + 多模态 blocks)
- `BlockSpec` (单一练习块:类型/时长/目标/链接到具体模块)
- `WeekPlanV2` (7 天 + weekly goals + spaced repetition schedule)
- `AdaptivePlanner` (整合 student_db + 5 维 + senior + 间隔复习)
- `SpacedRepetition` (类 SM-2 算法)
- `WeaknessDetector` (从 5 维数据检测弱项)

### 5.3 6 类练习块 (基于 5 维模块)
| 类型 | 时长 | 模块 | 目的 |
|------|------|------|------|
| warmup_pitch | 3-5min | eval_pitch | 音阶/琶音热身 |
| warmup_hand | 2-3min | hand_pose | 手型放松 |
| expressiveness | 5-8min | expressiveness | 表现力专练 |
| sight_reading | 5-10min | sight_reading | 视奏训练 |
| main_piece | 15-20min | midi_analyzer | 主曲打磨 |
| review_piece | 5-10min | midi_analyzer | 间隔复习 |
| weakness_drill | 3-5min | 多模块联动 | 弱项专练 |
| cooldown_relax | 2-3min | 自由弹奏 | 放松 |

### 5.4 自适应算法
1. **每日评估** → 5 维分数
2. **检测弱项** → top 3 弱项领域
3. **间隔复习** → SM-2 计算每首曲子下次复习时间
4. **难度调整** → 整体分数 ≥ 85 自动升档
5. **银发适配** → age ≥ 60 简化语言 + 加长 + 鼓励

### 5.5 数据流
```
StudentDB (历史) + 5 维分数
   ↓
AdaptivePlanner
   ↓
WeekPlanV2 (7 天 × 6 块)
   ↓
voice_dialog (每日播报) + student_db.record_session
```

### 5.6 voice_dialog 集成
- "我的课程"/"今天练什么"/"查看计划" → 读出当天计划
- "标记完成"/"练完了" → 标记 + 下一天
- "跳过"/"换一首" → 调整

---

## 6. 调研对位 (CoPiano 创新点)

| 现有方案 | 局限 | CoPiano 创新 |
|---------|------|------------|
| Simply Piano 12 章 | 无自适应,固定课程 | 每日自适应重排 |
| Flowkey 1500 曲 | 无弱项检测 | 5 维弱项专练 |
| SAMICK 8 功能 | 无多模态整合 | 5 维统一调度 |
| 扇贝间隔复习 | 单词用,不适配音乐 | 音乐专用 SM-2 |
| Anki SM-2 | 通用,无模态 | 多模态 + 音乐知识图谱 |

**CoPiano curriculum_v2 创新定位**:
> "业界首个 5 维多模态自适应 7 天 AI 钢琴课程,整合音高/表现力/手型/银发/视奏 + 间隔复习 (SM-2) + 弱项专练 + 银发适配,7 天一周动态调整"

---

## 7. 风险与依赖

| 风险 | 缓解 |
|------|------|
| 5 模块集成复杂度 | 独立 Optional import,失败 fallback |
| LLM 调用慢 | 课程生成 0s (内置规则) |
| student_db 数据少 | 默认 7 天计划 (无历史也跑) |
| SM-2 算法复杂 | 简化版: 1/3/7/14/30 天固定间隔 |
| 银发模式冲突 | senior_mode 独立 patch,不破坏 plan |

---

## 8. 预期效果 (量化)

| 指标 | Day 1-2 | Day 3-5 | Day 6-7 |
|------|---------|---------|---------|
| 每日总时长 | 30 min | 35 min | 40 min |
| 模块覆盖 | 3/5 | 4/5 | 5/5 |
| 弱项专练 | 1 块 | 2 块 | 2 块 |
| 间隔复习 | — | 1 首 | 2-3 首 |
| 升档阈值 | — | acc ≥ 0.85 | acc ≥ 0.90 |

---

## 9. Cycle 7 完整时间线

| 阶段 | 状态 | 产出 |
|------|------|------|
| Stage 1 调研 | ✅ 本文件 | 知识库 (5K) |
| Stage 2 实现 | ⏳ 下步 | curriculum_v2.py (15K) |
| Stage 3 测试 | ⏳ 第 3 步 | cycle7_test.py (10K) + 5 维集成 + 间隔复习 + 银发 |

**总产出预估**: ~25K 代码,7 天 6 块,5 维整合,SM-2 间隔,银发适配
