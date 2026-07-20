# CoPiano v3 — Real User RCT Protocol

> **目标**: 将 v3.0 模拟 RCT (d=1.34) 升级为真实用户验证
> **预计时长**: 8 周 (招募 1 周 + 干预 1 周 + 分析 1 周 + 撰写 5 周)
> **样本量**: 60 用户 (30 control + 30 treatment)
> **状态**: Protocol v1.0 (待 IRB 批准)

---

## 1. 研究问题 (Research Question)

**主问题**: 相比无课程对照组,CoPiano v3 多模态自适应课程是否能在 7 天内显著提升用户的 5 维钢琴评估分数?

**子问题**:
1. 不同年龄组 (25-45 vs 60-70) 是否受益不同?
2. 不同初始水平 (beginner < 70 vs intermediate 70-85) 的提升幅度?
3. 5 维之间是否有"溢出效应" (e.g., 主曲训练提升 sight_reading)?
4. 银发模式 (age ≥ 60) 是否真正提升老年用户体验?

## 2. 假设 (Hypotheses)

**H1 (主假设)**: 7 天后 treatment 组 5 维综合分显著高于 control 组 (Cohen's d ≥ 0.5, p<0.05)

**H2 (维度假设)**: 5 维中至少 3 维 (含 rhythm, hand_pose) 显著优于 control (p<0.05)

**H3 (年龄假设)**: treatment 对 60+ 用户的提升 > 25-45 用户 (银发模式有效)

**H4 (水平假设)**: treatment 对 beginner (综合分 < 70) 的提升 > intermediate 用户 (差距更大)

**H5 (溢出假设)**: 主曲训练 (D1 pitch) 显著提升 sight_reading (D4) (跨维度迁移)

**H6 (银发体验假设)**: 60+ 用户报告银发模式的可用性评分 ≥ 4/5 (5 分制)

## 3. 样本 (Sample)

### 3.1 招募
- **目标**: 60 用户
- **来源**:
  - 钢琴教师推荐 (3 个城市: 北京/上海/深圳)
  - 在线广告 (小红书/知乎/微博)
  - 老年大学合作 (北京 5 所)
- **时长**: 1 周
- **筛选标准**:
  - 年龄 25-70
  - 钢琴学习经验 6 个月 - 5 年
  - 能使用 MIDI 键盘 (提供测试设备)
  - 每周可投入 5+ 小时
- **排除标准**:
  - 专业钢琴演奏者 (>5 年经验)
  - 有手部/听力障碍
  - 同期参与其他音乐研究

### 3.2 样本量计算
- **基础**: 检测 d=0.5 (medium),α=0.05, power=0.80
- **公式**: n = 2 × (z_α/2 + z_β)² / d² ≈ 2 × 7.85 / 0.25 = 63
- **实际**: 60 (略小,考虑 5% 流失)
- **配对**: 30 control + 30 treatment
- **分层**: 50/50 混合 adult (25-45) + senior (60-70)

## 4. 随机化 (Randomization)

### 4.1 分组
- **方法**: 简单随机化 (computer-generated)
- **工具**: `random.Random(seed=42)` 在 `test_data_generator.py` 中验证
- **平衡**: 分层按 (age group × sex) 平衡
- **盲法**: 单盲 — 数据分析者不知道分组,用户知道

### 4.2 实施
```python
from test_data_generator import generate_cohort
cohort = generate_cohort(n_per_group=30, days=7, seed=42)
# 自动产生 user_id (c001-c030 + t001-t030)
# 预先生成,实验开始前随机化
```

## 5. 干预 (Intervention)

### 5.1 Control 组 (无课程)
- **行为**: 自由练习,不提供课程
- **跟踪**: 每天上传任意 MIDI (≤ 30 min)
- **评估**: 仅 5 维评分,无反馈
- **时长**: 7 天

### 5.2 Treatment 组 (CoPiano v3 完整)
- **行为**: 按 7 天课程练习
- **课程**: `curriculum_v2.generate_week_plan()` 输出
- **支持**: voice_dialog (5 模块关键词)
- **反馈**: 5 维 + LLM (Qwen 7B) + 银发 (auto)
- **时长**: 7 天

### 5.3 共变量控制
- 两组都获得:
  - MIDI 键盘 (Yamaha P-45,价值 ¥3000)
  - 节拍器软件 (CoPiano `metronome.py`)
  - 5 维评估 (无反馈版本)
  - 同样的每日练习时长 (30 min/day)
- 差异:
  - Control: 自由练习
  - Treatment: 课程 + 反馈 + 银发

## 6. 测量 (Measurements)

### 6.1 主要结局
- **5 维综合分** (5 dim 加权平均): 0-100
- **测量时间**: Day 0 (pre) + Day 7 (post)
- **工具**: `eval_pitch + expressiveness_analyzer + hand_pose_analyzer + sight_reading_trainer + senior_mode`

### 6.2 次要结局
- 每日练习时长 (自动记录)
- 每日各块完成度 (curriculum_v2 stats)
- 跨维度迁移 (H5)
- 银发体验问卷 (H6): 5 分制 10 题

### 6.3 数据流
```
MIDI 录音 → eval → 5 维分数 → student_db
                            ↓
                  curriculum_v2 调整 (treatment)
                            ↓
                  voice_dialog 反馈 (treatment)
```

## 7. 统计分析 (Statistical Analysis)

### 7.1 检验
- **主检验**: Welch's t-test (treatment vs control post scores)
- **效应量**: Cohen's d
- **统计软件**: `ab_test_harness.py` (纯 Python,无 scipy 依赖)
- **显著性**: p<0.05 (主), p<0.01 (次,Bonferroni 校正)

### 7.2 假设检验
- **H1**: 综合分独立样本 t-test
- **H2**: 5 维分别 t-test + FDR 校正
- **H3**: 60+ 子样本 vs 25-45 子样本 t-test
- **H4**: 低分 vs 高分亚组 t-test
- **H5**: 跨维度 Pearson 相关
- **H6**: 单组问卷得分 (1-sample t vs 4)

### 7.3 效应量解释
- d < 0.2: negligible
- 0.2-0.5: small
- 0.5-0.8: medium
- 0.8+: large

### 7.4 与 v3.0 模拟对比
- **模拟预期**: d=1.34 (cycle 14, 真实化数据)
- **真实预期**: d=0.5-1.0 (考虑现实摩擦)
- **文献基准**: Kulik & Fletcher 2016 ITS d=0.41
- **成功阈值**: d ≥ 0.5 (优于 ITS 主流)

## 8. 实施时间表 (Timeline)

| 周 | 任务 |
|----|------|
| W1 | 招募 + 筛选 + MIDI 键盘寄送 + 知情同意 |
| W2 | Day 0 baseline 评估 + 随机化 + 培训 |
| W3 | 7 天干预 (W3 周一-周日) |
| W4 | Day 7 评估 + 问卷 + 设备回收 |
| W5 | 数据清洗 + 统计分析 |
| W6-W7 | 报告撰写 (补充论文) |
| W8 | arxiv 提交 (v3 论文最终版) |

## 9. 伦理 (Ethics)

### 9.1 IRB 申请
- 提交机构: 北京师范大学教育学部 / 中央音乐学院
- 关键文件: 知情同意 + 数据使用 + 撤回权利
- 风险评估: 极低 (无侵入性操作,纯数据采集)

### 9.2 数据保护
- 匿名化: user_id (c001/t001)
- 数据存储: 国内服务器 (不跨境)
- 知情同意: 7 项必读 + 数字签名
- 撤回: 任何时候可要求删除数据

### 9.3 设备安全
- MIDI 键盘 3C 认证
- 软件开源可审计
- 银发用户安全使用培训

## 10. 风险与缓解 (Risks)

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 招募不足 | 中 | 高 | 3 个城市 + 在线 + 老年大学 |
| 流失率高 (>20%) | 中 | 中 | 每日提醒 + ¥100 完成奖励 |
| 设备故障 | 低 | 中 | 备用设备 + 远程支持 |
| 用户作弊 (代弹) | 低 | 高 | 视频监控 + 异常检测 |
| 银发用户难适应 | 中 | 中 | 上门培训 + 简化界面 |
| MIDI 录制失败 | 低 | 低 | 自动重试 + 备用通道 |

## 11. 成本估算 (Budget)

| 项目 | 单价 | 数量 | 总额 |
|------|------|------|------|
| MIDI 键盘 | ¥3,000 | 60 | ¥180,000 |
| 招募奖励 | ¥100 | 60 | ¥6,000 |
| 上门培训 (银发) | ¥500 | 20 | ¥10,000 |
| 数据存储 (1 年) | ¥500 | - | ¥500 |
| 论文发表费 (OA) | $2,000 | 1 | ¥14,000 |
| **总计** | | | **¥210,500** |

## 12. 论文发表 (Publication Plan)

### 12.1 目标期刊/会议
- **首选**: arXiv cs.HC / cs.SD (即时)
- **次选**: NIME 2027 (New Interfaces for Musical Expression)
- **第三**: CHI 2027 (ACM CHI)

### 12.2 论文结构 (v3.0 → 真实数据升级)
1. Abstract (基于真实数据)
2. Introduction
3. Related Work (813 papers 综述)
4. 5-Dim Multi-Modal System
5. Experiments (真实 RCT)
6. Discussion
7. Conclusion
8. Appendix (代码 + 数据 + 图表)

### 12.3 数据可用性
- 完整数据: GitHub release
- 匿名化: 用户可选择
- 长期保存: 5 年

## 13. 立即行动 (Immediate Next Steps)

1. ☐ **W0 (本周)**: 联系 3 位合作教师,确认合作意向
2. ☐ **W0 (本周)**: 准备 IRB 申请材料
3. ☐ **W0 (本周)**: 联系 60 台 MIDI 键盘供应商
4. ☐ **W1 (下周)**: 启动招募 + 知情同意流程
5. ☐ **W2**: 培训 + baseline

---

## 附录 A: 知情同意书模板

```
研究项目: CoPiano v3 多模态 AI 钢琴教练效果验证
负责人: [作者] ([机构])
联系人: [email]

研究目的: 验证 CoPiano v3 多模态自适应课程在 7 天内对钢琴学习效果的提升
时长: 7 天干预 + 30 分钟评估/天
风险: 极低 (无侵入性操作,纯数据采集)
收益: 7 天免费使用 CoPiano v3 + ¥100 完成奖励
数据使用: 匿名化后用于学术研究和开源发布
撤回: 任何时候可要求删除数据,无任何后果

我已阅读并理解上述内容,自愿参与本研究。

签名: ___________  日期: ___________
```

## 附录 B: 测试设备清单

| 设备 | 型号 | 数量 | 单价 |
|------|------|------|------|
| MIDI 键盘 | Yamaha P-45 | 30 | ¥3,000 |
| USB MIDI 接口 | Roland UM-ONE | 60 | ¥200 |
| 头戴式耳机 (录音) | Audio-Technica ATH-M50x | 10 (备用) | ¥1,200 |

## 附录 C: 数据采集表

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | str | ✓ | c001-c030 / t001-t030 |
| age | int | ✓ | 25-70 |
| age_group | str | ✓ | adult / senior |
| sex | str | ✓ | M / F / other |
| experience_years | float | ✓ | 0.5-5 |
| device_model | str | ✓ | MIDI 键盘型号 |
| daily_minutes | int | ✓ | 实际练习时长 |
| daily_pieces | int | ✓ | 每日弹的曲子数 |
| day_0_pitch | float | ✓ | baseline 音准 |
| day_0_expressiveness | float | ✓ | baseline 表现力 |
| day_0_hand_pose | float | ✓ | baseline 手型 |
| day_0_rhythm | float | ✓ | baseline 节奏 |
| day_0_sight_reading | float | ✓ | baseline 视奏 |
| day_7_5dim | dict | ✓ | 5 维终评 |
| senior_satisfaction | int | (only 60+) | 1-5 |

---

*本协议 v1.0 草稿,2026-07-21*
*待 IRB 批准 + 钢琴教师合作确认后启动*
*项目位置: `~/piano-ai-corpus/`*
