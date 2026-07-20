# Phase 6 CYCLE 4 — 手型/手姿 调研知识库

> **目标**: 调研"AI 钢琴手型评估"的技术现状 + 学术 + 教学原则,为 Cycle 4 stage 2 实践提供理论支撑
> **日期**: 2026-07-21
> **研究方向**: 从 Cycle 2 SWOT 中识别的"手型/指法监测"行业空白出发

---

## 1. 调研范围

| 维度 | 内容 | 主要来源 |
|------|------|---------|
| 视觉基础 | MediaPipe Hands / OpenPose 21-landmark | Google Research / Stanford |
| 商用设备 | MANUS Metagloves Pro / OptiTrack | 搜维尔 / 行业案例 |
| 教学理论 | Alan Fraser 手型原则 / 钢琴技法 | pianotechnique.org |
| 学术 | Stanford AI 3D hand / Piano Motion | arXiv / 国际期刊 |
| 3D 数据 | UmeTrack 20-joint + 6-DOF wrist | Stanford 2026 |

---

## 2. MediaPipe Hands 核心架构

**21 关键点 + 3D 坐标 (x, y, z) + visibility**:
```
WRIST (0): 手腕基准
THUMB (1-4): 拇指 4 段
INDEX (5-8): 食指 4 段
MIDDLE (9-12): 中指 4 段
RING (13-16): 无名指 4 段
PINKY (17-20): 小指 4 段
```

**两阶段检测**:
1. **Palm Detection (BlazePalm)**: SSD,小目标优化,粗定位手掌
2. **Hand Landmark Estimation**: CNN,21 个 3D 关键点 (z = 相对深度)

**配置参数**:
- `static_image_mode`: False=视频流,True=静态
- `max_num_hands`: 默认 2
- `min_detection_confidence`: 默认 0.5
- `min_tracking_confidence`: 默认 0.5

**关键性能**: 实时 ~30 FPS,CPU 即可跑

---

## 3. 手型分析 — 数学方法

### 3.1 指节弯曲角度(每指 3 段)
```python
def vector_2d_angle(v1, v2):
    angle = math.degrees(math.acos(
        (v1[0]*v2[0] + v1[1]*v2[1]) /
        (math.sqrt(v1[0]**2 + v1[1]**2) * math.sqrt(v2[0]**2 + v2[1]**2))
    ))
    return angle
```

**手指关节序列** (joint_list):
```python
[[8, 7, 6],    # 食指 (PIP/DIP/MCP)
 [12, 11, 10], # 中指
 [16, 15, 14], # 无名指
 [20, 19, 18], # 小指
 [4, 3, 2]]    # 拇指
```

**手势判定阈值**:
- thr_angle = 65° (弯曲)
- thr_angle_s = 49° (伸直)
- thr_angle_thumb = 53° (拇指特殊)

### 3.2 五种典型钢琴手型
| 手型 | 拇指 | 食指 | 中指 | 无名指 | 小指 |
|------|------|------|------|--------|------|
| 握拳 (fist) | 弯 | 弯 | 弯 | 弯 | 弯 |
| 张开 (five) | 直 | 直 | 直 | 直 | 直 |
| 指枪 (gun) | 直 | 直 | 弯 | 弯 | 弯 |
| 点赞 (thumbUp) | 直 | 弯 | 弯 | 弯 | 弯 |
| 数字 2 (two) | 弯 | 直 | 直 | 弯 | 弯 |

---

## 4. 钢琴教学法 — 手型原则 (Alan Fraser)

**核心原则** (从 pianotechnique.org 整理):

### 4.1 手的解剖学
- **27 块骨头 / 29 个关节 / 数万姿态组合**
- **手弓 (Hand Arch)** = 钢琴的"声音"
- **手腕 = 手臂的延伸**,不是独立单元
- **拇指 3 运动方式**:屈/伸/外展(钢琴忌屈)

### 4.2 9 大教学要点
1. **消除"drop"动作** — 不应用力下压琴键
2. **手弓始终存在** — 即使在八度音程
3. **手指 bird beak 形** — 自然弯曲
4. **拇指 corkScrew 旋转** — 主动发力
5. **手掌接触琴键** — 更好"感觉"
6. **慢速压键** — 发大声音
7. **关节弯曲无紧张** — 发挥 MCP 关节
8. **站立动作 (Standing action)** — 弹响亮音
9. **整体姿态整合** — 手指→颈→核心

### 4.3 4 大训练方法
- **Pianimals** (12 基础动作): grasp / poke / walk / roll / hook / cat scratch
- **Weight technique** (重量技术): 利用手臂自然重量
- **Biotensegrity** (生物张拉整体): 张力+压缩平衡
- **Tensegrity in piano**: 琴键+琴锤=张拉链

---

## 5. 商用钢琴动捕设备 (MANUS + OptiTrack)

### 5.1 MANUS Metagloves Pro
- **技术**: 电磁场 (EMF) 指尖追踪
- **优势**: 不受遮挡/漂移影响
- **关键**: 精确捕捉每个指尖的旋转+按压+释放

### 5.2 集成方案
```
[MANUS Gloves]  → 手指级追踪
   +
[OptiTrack]      → 身体级追踪 (6-8 相机,60+ FPS)
   +
[Piano 标记]     → 琴键起始/结束点
   ↓
[后期: Maya/Blender]  → 动画数据
```

### 5.3 性能数据
- 钢琴动画: 动画师手工需要数小时,MANUS 可直接生成
- 录制时间: < 1 小时 (vs 手工 1-2 周)
- 准确度: 跟琴键完美对齐 (后期微调 5-10%)

### 5.4 局限
- **价格**: MANUS Pro ~$10,000+ USD,OptiTrack 套装 ~$50,000+
- **学习曲线**: 需要动捕/Maya 专业知识
- **实时性**: 后处理模式,不能实时反馈教学

---

## 6. Stanford AI 3D Hand Project (2026)

### 6.1 技术方案
- **模型**: UmeTrack Hand Pose
- **参数化**:
  - **20 个手指关节角度**
  - **6-DOF 手腕变换** (3 平移 + 3 旋转)
- **应用**: VR/AR 虚拟环境控制
- **精度**: PA-MPJPE 12.23mm (混合 2D+3D 策略)

### 6.2 性能
- 任务成功率: **71.2%** (vs 3.0% 文字指令)
- 用户控制感: **4.21/7** (vs 1.74/7 文字)
- 帧率: 11 FPS @ H100 GPU,延迟 1.4s
- 数据集: 5824 HOT3D 训练样本 + GigaHands 8x 大

### 6.3 钢琴应用启示
- 20 关节参数化足以覆盖钢琴所有手型需求
- 6-DOF 手腕 = 演奏中手腕的横滚/抬落
- 2D+3D 混合 = 既能几何精确又能视觉直观

---

## 7. CoPiano 现状 + 空白

### 7.1 Phase 4 已有
- `scripts/video_hand_tracker.py` (骨架,OpenCV 肤色 fallback)
- MediaPipe Python 包装装不上(legacy from Phase 4)

### 7.2 调研发现的空白
- **教学理论未编码**: Alan Fraser 9 原则没有被结构化
- **钢琴专用指标缺失**: 通用手势识别 ≠ 钢琴手型
- **实时评分空白**: 没有 0-100 综合分
- **教学反馈生成空白**: LLM 没有接入手型数据
- **左/右手协同**: 商业 MANUS 主打,但 CoPiano 可用关键点估算

### 7.3 CoPiano 差异化机会
- **轻量级方案**: 21 关键点够用,无需 MANUS 商业级
- **教学对齐**: 9 维度评分 = 9 教学原则
- **AI 教师**: LLM 解读手型问题(教学价值高)
- **零成本**: 摄像头 + CPU,无硬件门槛

---

## 8. Cycle 4 stage 2 实施目标

### 8.1 模块名: `scripts/hand_pose_analyzer.py`

### 8.2 9 维钢琴手型分析器
| 维度 | 范围 | 教学对应 |
|------|------|---------|
| 1. wrist_height | 高/中/低 | 手腕弹性 |
| 2. hand_arch | 弯曲度 0-1 | 手弓完整性 |
| 3. finger_curl | 5 指弯曲度 | 触键角度 |
| 4. thumb_position | 内外/高度 | 拇指主动性 |
| 5. palm_contact | 接触面积 | 触感训练 |
| 6. hand_rotation | 内/外翻 | 平行指法 |
| 7. symmetry_LR | 左右手差异 | 协调性 |
| 8. finger_independence | 4/5 指控制 | 弱指训练 |
| 9. relaxation | 紧张度 | 健康演奏 |

### 8.3 0-100 综合分
- 每维 0-100
- 加权: arch(20%) + curl(20%) + thumb(15%) + rotation(15%) + relaxation(15%) + other(15%)

### 8.4 集成
- `patch_voice_dialog_with_hand_pose()`: 用户说"分析我的手型"自动跑
- 输入: 视频/图像/21 关键点 JSON
- 输出: 9 维分数 + 教学建议 + 改进练习
- Mac MediaPipe 优先,无则用 OpenCV 估算

### 8.5 教学反馈 (LLM-ready)
- "拇指外展角度小,主旋律段落建议多练 thumb walks"
- "无名指独立性弱 (4/5 指弯曲差 30°),推荐 Hanon 练习"
- "手弓在八度音程塌陷,练 Pianimals 弯曲 (15 min/day)"

---

## 9. 测试计划 (Cycle 4 stage 3)

### 9.1 测试场景
1. 完美手型 (arch 0.9, curl 75°, thumb 60°) → 95-100 分
2. 紧张手型 (arch 0.4, curl 95°, thumb 25°) → 50-60 分
3. 塌陷手型 (arch 0.2, wrist low, rotation 30°) → 30-40 分
4. 左右不对称 (R arch 0.8, L arch 0.4) → 60-70 分

### 9.2 验证项
- 9 维度分数合理性
- 综合分单调性 (低质量 < 中等 < 高质量)
- LLM 集成稳定性 (无递归)
- 视频处理速度 (≥10 FPS 实时)

---

## 10. 调研对位 (CoPiano 创新点)

| 学术/产品 | 局限 | CoPiano 创新 |
|-----------|------|---------------|
| MediaPipe Hands | 通用手势 | 钢琴 9 维专精 |
| MANUS Pro | $10k+,需要 OptiTrack | 21 关键点就够 |
| Alan Fraser 教学 | 视频/Blog 形式 | 数据驱动+LLM 反馈 |
| Stanford 3D Hand | VR 控制,无音乐应用 | 钢琴教学专项 |
| OptiTrack 动捕 | 后期处理,不能教学 | 实时评分+反馈 |
| Flowkey/Simply Piano | 无手型监测 | **0 商业竞品做 AI 手型** |

**CoPiano 创新定位**:
> "业界第一个开源的 AI 钢琴手型评估系统,基于 MediaPipe 21 关键点 + 9 维度教学评分 + LLM 反馈生成,无需任何商业动捕设备"

---

## 11. 风险与依赖

| 风险 | 缓解 |
|------|------|
| MediaPipe Python 装不上 | OpenCV 关键点估算 fallback (legacy) |
| 摄像头权限/隐私 | 强调本地处理,不上传 |
| 关键点抖动 | 时序滤波 (Kalman / EMA) |
| 钢琴视角受限 | 多角度拼接 (顶部 + 侧面) |
| LLM 反馈延迟 | 直答 0s,LLM 异步生成 |
| 教学价值需验证 | LLM 自评 + 教学专家审阅 |

---

## 12. Cycle 4 完整时间线 (预估)

| 阶段 | 状态 | 产出 |
|------|------|------|
| Stage 1 调研 | ✅ 本文件 | 知识库 (5.4K) |
| Stage 2 实现 | ⏳ 下轮 | hand_pose_analyzer.py (15K) |
| Stage 3 测试 | ⏳ 第 3 轮 | cycle4_test.py (10K) + 4 场景验证 |

**总产出预估**: ~30K 代码,9 维评分,LLM 集成,填补 CoPiano 手型空白
