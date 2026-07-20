# Phase 6 CYCLE 6 — 识谱训练 调研知识库

> **目标**: 调研"AI 钢琴识谱训练"的市场+教学+技术,定位 CoPiano v4 视奏模块
> **日期**: 2026-07-21
> **方向**: Cycle 1 调研识为 #1 初学者痛点 (不知练什么/不会识谱), MuseFlow 标杆赛道

---

## 1. 调研范围

| 维度 | 内容 | 来源 |
|------|------|------|
| 国际标杆 | TypePiano.org (随机音符 + 真曲挑战) | 官网 + 9 用户评价 |
| 国内产品 | 五线谱入门 / 小马 AI / 钢琴教练 | 行业百科 |
| 教学法 | Landmark / Interval / Pattern 3 大流派 | Bunnag 2005 博士论文 |
| 技术 | music21 / TinyNotation / WebMIDI | MIT 官方 |
| AI 集成 | 实时反馈 + 模式识别 + 渐进难度 | 多方综合 |

---

## 2. 标杆产品: TypePiano.org (2026 最新)

### 2.1 创始人动机
- 自学钢琴的成年人,被五线谱"数格子"严重拖慢
- "我需要的不是更多乐理,而是反复视觉-动作训练,像学打字一样"
- = 5/9 用户 5.0 评分

### 2.2 核心机制
- **3 种练习路径**:
  1. 日常训练 (无限视奏,随机音符刷反应)
  2. 乐曲挑战 (欢乐颂/致爱丽丝 等真曲,逐句解锁)
  3. 入门教程 (五线谱基础)
- **3 键位输入**:
  - 电脑键盘 1-7 (C-B)
  - 手机触摸 (虚拟键盘)
  - MIDI 键盘 (WebMIDI API, Chrome)
- **反馈机制**:
  - 即时音效 (按键马上响)
  - 正确高亮 / 错误红色
  - 光标自动前进 (正确才走)

### 2.3 数据追踪
- 准确率 (正确/总数)
- 速度 (音符/分钟)
- 连击数 (streak)
- 历史曲线 (进步可视化)

### 2.4 教学法支持
- Landmark method: 中央 C 锚点,向上下导航
- 不依赖 3-5 个月,几周可初步识谱
- 建议每天 10 分钟短时高频训练

---

## 3. 国内代表产品

### 3.1 五线谱入门 app
- **4 模式**:
  1. 五线谱练习 (随机 10 音符 + 警告音 + 3 次错误提示)
  2. 单手弹奏 (按节奏弹)
  3. 双手弹奏 (自由演奏)
  4. 双人弹奏 (反向双键盘)
- **可调设置**: 键盘大小 / 音名显示 / 黑键 / 节奏速度

### 3.2 小马 AI 陪练
- **功能**: 识谱练习 + 识谱游戏 + 听音练习 + 节奏模仿
- 适合 6-12 岁,高精 AI 识别

### 3.3 钢琴教练
- 自由弹奏 + 自动生成五线谱
- 24h 智能陪练

### 3.4 共同短板
- 0 商业竞品做 **AI 实时识谱反馈 + 周期化训练 + 个性化难度**
- 多数是"识谱游戏"而非"系统训练"
- 多数是儿童向, 成人向 几乎空白

---

## 4. 教学法 3 大流派 (Bunnag 2005 博士论文)

### 4.1 Landmark method (地标法)
- 锚定 5-6 个固定音 (中央 C, G, F, 高音 G, 低音 C 等)
- 看到新音时, **以最近地标为参照**
- 适合初学者建立空间感

### 4.2 Interval recognition (音程识别)
- 不识别单个音,而是 **识别音之间的形状/距离**
- 看到"上跳 2 度" → 知道下一个音
- 适合中高级,提速明显

### 4.3 Pattern recognition (模式识别)
- 整段识别为常见曲调模式 (Stair-step, 拱形, 重复等)
- 不需要逐音思考
- 适合高级,几乎瞬时反应

### 4.4 综合建议
- 入门: Landmark + 慢速单手
- 进阶: Interval + 真曲
- 高级: Pattern + 复杂乐曲
- **每阶段都要有反馈和统计**

---

## 5. music21 库 (MIT, 2009 至今)

### 5.1 核心类
- `note.Note("C4")` 创建音符
- `chord.Chord(["E3", "C4", "G4"])` 创建和弦
- `stream.Stream()` 容器
- `stream.Measure(number=N)` 小节
- `stream.Score()` 总谱

### 5.2 TinyNotation 简单乐谱
```
4/4 C4 D4 E4 F4 G4 A4 B4 c4
```
- 大写 = 低音谱号区
- 小写 = 高音谱号区
- 数字 = 时值 (4 = 四分, 8 = 八分)

### 5.3 优势
- 强大 (interval, key, roman numeral, voice leading)
- 直接解析 MusicXML / MIDI / abc
- Pythonic API

### 5.4 CoPiano 集成
- **不强制依赖** (music21 装不上就降级)
- 用纯 Python 实现基础 (note name, pitch number)
- music21 装上时启用高级 (interval, key analysis)

---

## 6. WebMIDI 实时输入

### 6.1 API 简介
- Chrome 浏览器内置 WebMIDI API
- 连接 MIDI 设备后 `navigator.requestMIDIAccess()`
- 接收 `note on/off` 事件 (pitch, velocity, timing)

### 6.2 教学应用
- 看到音符 → 按下对应键
- 正确 → 前进; 错误 → 闪烁红色
- 实时反馈 (< 100ms 延迟)

### 6.3 备选输入
- 电脑键盘 (1-7 = C-B)
- 鼠标点击虚拟键盘
- 触摸 (iPad/手机)

---

## 7. CoPiano 现状 + 识谱空白

### 7.1 已有
- `eval_pitch.py` 错音检测
- `align_score.py` 乐谱对齐
- `curriculum.py` 7 天自适应
- `voice_dialog.py` 实时语音对话
- `teaching_engine.py` 教学反馈

### 7.2 识谱空白
- **0 主动识谱训练**: 没有"看谱→按键"循环
- **0 难度递进**: curriculum 没细化到识谱维度
- **0 节奏控制**: 只测对错,没测速度
- **0 streak/统计**: 没连续成功记录
- **0 真曲挑战**: curriculum 用片段,没系统乐曲

### 7.3 CoPiano 差异化
- **AI 老师讲解**: 不只显示"对/错",还讲"为什么"
- **3 法融合**: Landmark/Interval/Pattern 自动切换
- **4 难度渐进**: 4 个 difficulty levels
- **可调输入**: 电脑键/MIDI/虚拟键盘都支持
- **Voice 集成**: "开始识谱训练" 语音命令
- **L2 教学对齐**: 与 expressiveness / hand_pose 多维评分同步

---

## 8. Cycle 6 stage 2 实施目标

### 8.1 模块: `scripts/sight_reading_trainer.py`

### 8.2 核心类
- `Note` (pitch + octave + accidental)
- `SightReadingTrainer` (生成 + 验证 + 统计)
- `DifficultyConfig` (4 档)
- `SessionStats` (accuracy / streak / time / bpm)

### 8.3 4 难度级别
| Level | 音域 | 升降号 | 调 | 节奏 |
|-------|------|--------|-----|------|
| Beginner | C4-E5 | 0 (C major) | C | 自由 |
| Elementary | A3-G5 | ≤ 1 sharp/flat | G/F | 4/4 |
| Intermediate | F3-A5 | ≤ 2 | D/Bb | 3/4, 4/4 |
| Advanced | C3-C6 | ≤ 4 | 4 升降 | 复合拍 |

### 8.4 3 大模式
- **Random Notes**: 5-20 随机音符
- **Interval Drill**: 5-20 音程序列 (二度三度等)
- **Real Piece**: 简化版 Mozart/Bach 片段

### 8.5 4 步循环
1. 显示音符 (ASCII art 谱面)
2. 用户按键 (电脑键 1-7 或 MIDI)
3. 反馈 (✓/✗ 音效 + 颜色)
4. 前进 (正确 → 下一个 / 错误 → 闪烁)

### 8.6 集成
- `voice_dialog` 关键词: "识谱训练" / "练视奏" / "sight reading"
- `student_db` 记录: 每日训练时长 + accuracy + streak
- `curriculum` 第 5-7 天加入视奏环节

---

## 9. 调研对位 (CoPiano 创新点)

| 现有产品 | 局限 | CoPiano 创新 |
|---------|------|------------|
| TypePiano.org | 无 AI 反馈/中文 | AI 老师 + 鼓励式反馈 + 中文/英文 |
| 五线谱入门 | 仅警告音,无讲解 | LLM 解释"为什么这个是 D" |
| 小马 AI | 儿童向 | 成人向 + 银发模式 (Cycle 5 集成) |
| Simply Piano | 弹曲子,不练视奏 | 专项视奏训练 |
| Flowkey | 真曲跟弹,无系统 | 系统化视奏 + 真曲挑战 |

**CoPiano 视奏模块创新定位**:
> "业界第一个为成人定制的 AI 古典钢琴视奏训练系统,3 法融合 (Landmark/Interval/Pattern) + 4 难度渐进 + 真曲挑战 + LLM 即时讲解,WebMIDI/电脑键/虚拟键盘 3 模式输入"

---

## 10. 风险与依赖

| 风险 | 缓解 |
|------|------|
| music21 装不上 | 纯 Python 实现核心 (note name, pitch number) |
| MIDI 设备未连接 | 电脑键盘 fallback (1-7) |
| LLM 响应慢 | 直答 0s (内置 6 个常见错误解释) |
| 用户不知道开始 | voice_dialog 关键词 + 默认推荐 |
| 真曲 MIDI 受版权 | 自生成简化版 (8-16 小节) |
| 难度跳跃 | 4 档渐进 + 连续 3 次正确自动升档 |

---

## 11. 预期效果 (量化)

| 指标 | Beginner | Elementary | Intermediate | Advanced |
|------|----------|------------|--------------|----------|
| 训练时长 | 5-10 min | 10-15 min | 15-20 min | 20+ min |
| 目标 accuracy | 70% | 80% | 90% | 95% |
| 目标 BPM | 30-40 | 50-60 | 70-80 | 90-100 |
| 升档阈值 | 80% | 90% | 95% | 98% |

---

## 12. Cycle 6 完整时间线 (预估)

| 阶段 | 状态 | 产出 |
|------|------|------|
| Stage 1 调研 | ✅ 本文件 | 知识库 (5.5K) |
| Stage 2 实现 | ⏳ 下步 | sight_reading_trainer.py (12K) |
| Stage 3 测试 | ⏳ 第 3 步 | cycle6_test.py (10K) + 4 难度验证 |

**总产出预估**: ~27K 代码,4 难度渐进,3 模式,voice 集成
