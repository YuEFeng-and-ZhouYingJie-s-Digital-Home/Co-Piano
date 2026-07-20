# CoPiano Cycle 3 知识库(2026-07-20)

> 调研角度:钢琴**表现力评估**——行业弱项 #2 + 古典钢琴核心
> 数据源:Werner Goebl 论文 / Repp 1996 / 豆丁 / 触键技巧论文
> 关键发现:**表现力 = 古典钢琴的灵魂,AI 行业空白**

---

## 一、表现力 7 大维度(基于学术+行业共识)

### 1.1 触键角度 (Touch Angle)
- **90°(垂直)**: 金石之声, 明亮穿透
- **50-70°(中度)**: 柔和浪漫(莫扎特/海顿常用)
- **30°(贴键)**: 朦胧悠远(德彪西/印象派)
- **评估**: MIDI 不直接记录角度,但**可通过 velocity std 间接推**(角度大 = 力度大 = 音色尖锐)

### 1.2 触键力度 (Touch Force / Velocity)
- 维度:指尖 / 手腕 / 前臂 / 全臂(4 种发力点)
- 评估:**velocity mean + std + range**(越大 = 越表现力)

### 1.3 触键速度 (Touch Speed)
- 快速:明亮颗粒(巴洛克 / 颗粒性乐句)
- 慢速:柔和悠长(浪漫派 / 歌唱性)
- 评估:**onset 到 peak velocity 的时间差**(MIDI 推算)

### 1.4 触键高度 (Touch Height)
- 高抬指:力度大,音色集中
- 不抬指:柔和,音色空灵
- 评估:**间接通过 velocity 推算**

### 1.5 触键深度 (Touch Depth)
- 弹到底:饱满(激昂乐句)
- 弹到中部:漂浮(印象派)
- 评估:**MIDI 不直接记录**,暂跳过

### 1.6 Rubato(速度变化)
- **古典时期**:rubato 受限(海顿/莫扎特)
- **浪漫时期**:rubato 自由(肖邦/李斯特)
- 评估:**Local Tempo Variation**(LTV) = IOI 标准差 / 平均
  - < 5%: 古典风格
  - 5-15%: 古典晚期 / 早期浪漫
  - > 15%: 浪漫/自由风格

### 1.7 动态对比 (Dynamics Range)
- **pp → ff 跨度**:力度范围
- 评估:**max velocity - min velocity**(0-127)
  - < 30: 单一力度(机械)
  - 30-60: 有对比
  - 60-100: 强表现力
  - 100-127: 戏剧性对比(浪漫派)

### 1.8 声部平衡 (Voicing) — 经典研究
- **Melody Lead**(Werner Goebl, Repp 1996): 主旋律比伴奏**提前 30ms**
- Velocity Difference: 主旋律**比伴奏力度大**20-40%
- 评估:**旋律 note vs 伴奏 note 的时间差 + 力度差**

### 1.9 触键后放松 (Post-touch Release)
- 立即放松:清晰颗粒(贝多芬)
- 保持紧张:压抑沉闷(肖邦叙事曲)
- 评估:**release velocity + 间隔**变化

---

## 二、学术研究核心参考

### 2.1 Werner Goebl(2001)"Melody Lead"
- 主旋律在多声部中**提前约 30ms** 演奏
- 高级演奏家效果更明显(初学者不明显)
- 是**速度差异**还是**力度差异**引起?— Repp 1996 答:力度

### 2.2 Repp 1996
- 速度-力度相关性:**高**(R² > 0.7)
- melody lead 主要由 velocity difference 解释
- 不是 pianist 主动的 expressive device,而是 piano action 的物理特性

### 2.3 SaxEx (Lopez de Mantaras)
- 萨克斯表现力 case-based reasoning
- 用 metrical strength + note duration 检索相似
- **不解释为什么**(黑盒)— CoPiano 优势:可解释

### 2.4 KTH Rule System (Friberg)
- 6 大规则:力度曲线 / rubato / articulation / 音高调整 / 踏板 / 微观结构
- 已被业界采用(SaxEx 底层)

### 2.5 Cambridge GameTalk(2025)
- AI 谈判博弈 + 多轮策略
- **跟表现力无关**,但对话策略可借鉴(AI 老师)
  - 内部状态评估 / 状态相对表现 / 影响机会

---

## 三、CoPiano 现状对位

| 维度 | L1/L2 现状 | Cycle 3 可加 |
|------|-----------|-----------|
| Velocity profile | ✅ velocity mean + std + correlation | 加 **range + dynamic contrast** |
| Rubato | ⚠️ 简单 std | 加 **LTV(局部速度变化)+ 风格匹配** |
| Touch angle | ❌ 无 | 通过 velocity 间接推 |
| Touch speed | ❌ 无 | 通过 onset→peak 时间 |
| Voicing (melody lead) | ❌ 无 | **加**(基于 Goebl/Repp) |
| Articulation (legato/staccato) | ❌ 无 | 通过 note gap |
| Release | ⚠️ note offset | 加 **release velocity** |

**CoPiano v2.0 缺 7/9 表现力维度** — 这是行业空白 + 用户痛点。

---

## 四、Cycle 3 实践目标(选定)

### 4.1 模块:`scripts/expressiveness_analyzer.py`

**目标**: MIDI 多维表现力分析,输出 0-100 整体分数 + 9 维度细分

**9 维度**:
1. velocity_mean (平均力度)
2. velocity_std (力度变化)
3. dynamic_range (max-min,动态对比)
4. ltv (Local Tempo Variation, rubato)
5. voicing_balance (旋律 vs 伴奏力度差)
6. melody_lead_ms (旋律提前 ms)
7. touch_speed (onset→peak,推算触键速度)
8. articulation (staccato/legato 比例)
9. release_var (释放变化)

**输出**:
- JSON:9 维度原始值 + 0-100 综合分
- Markdown 报告:对比期望风格(巴洛克 vs 浪漫给出建议)
- voice_dialog 集成:"评估我刚才的演奏" → 自动跑

### 4.2 调研对位

| 行业弱项 | CoPiano 加此模块后 |
|---------|-------------------|
| 节奏评估僵化 | ✅ LTV + 风格匹配 |
| 音色/强弱/情感评估弱 | ✅ velocity profile + dynamic range |
| 声部平衡评估无 | ✅ voicing_balance + melody_lead |
| 个性化指导不足 | ✅ 风格匹配建议(巴洛克 vs 浪漫) |

### 4.3 教学意义

学生问"我弹的怎么样"时,CoPiano 原来答:
> "你这段 92.0 分,错音 0 个"(单维)

加表现力后答:
> "你这段 92.0 分,错音 0 个。**表现力 76 分(满分 100),其中:**
> - 动态对比 9/10(从 pp 到 ff 跨度广)
> - Rubato 8/10(有自由节奏变化,符合浪漫派风格)
> - 声部平衡 5/10(主旋律力度比伴奏大 15%,建议提升到 25-30%)
> - **建议:加强主旋律表现,中段(小节 12-16) 旋律提前 20ms 可强化主题**"

**真正的"AI 老师"反馈**——具体到维度、具体到建议、具体到风格。

---

## 五、Cycle 3 路线图

| 阶段 | 内容 | 状态 |
|------|------|------|
| 1. 调研 (本轮) | ✅ 表现力 7 维度 + 学术经典 + 行业空白 | ✅ |
| 2. 实践 (下轮) | ⏳ expressiveness_analyzer.py 9 维度 | ⏳ |
| 3. 测试 (再下轮) | ⏳ 12 场景 + 不同风格对比 | ⏳ |

---

## 六、CoPiano 知识库累计

| Cycle | 主题 | 文档 |
|------|------|------|
| 1 | 30+ AI 钢琴产品 + 6 维度对位 | market_knowledge.md |
| 2 | SWOT + 用户行为 + 6 改进候选 | market_knowledge_cycle2.md |
| 3 | 表现力 7 维度 + 学术经典 | market_knowledge_cycle3.md |

论文累计:**813 篇**(693 + 120)
脚本累计:**28 个**(原 17 + 7 Cycle 1-2 + 即将加 Cycle 3)
Git commits:**8 个**(Phase 6)
