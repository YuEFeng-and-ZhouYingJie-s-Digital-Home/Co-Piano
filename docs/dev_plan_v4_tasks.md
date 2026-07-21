# CoPiano v4 — 开发任务跟踪 (Cron 自动推进)

> **使用方式**: 每个 cron tick 读取本文档,找第一个 `[PENDING]` 任务,完成后改 `[DONE]`
> **规则**:
> - 一次只做一个任务 (12 分钟上限)
> - 完成 → 标 `[DONE: YYYY-MM-DD HH:MM]`
> - 阻塞 → 标 `[BLOCKED: 原因]`
> - 失败 → 标 `[FAILED: 错误]`,可重试 3 次
> - 全部 Phase 7A 完成 → 写 `[PHASE_7A_DONE]`

---

## Phase 7A: 后端 + 网站 (W1-W8)

### W1: 服务器 + 基础设施

- [BLOCKED: 需用户操作 — Apple Developer 申请] **A1.1**: 申请 Apple Developer 账号 ($99/年)
- [BLOCKED: 需用户操作 — 域名已自有,需提供 DNS 控制台权限] **A1.2**: 注册/确认 copiano.com 域名
- [BLOCKED: 需用户操作 — DNS A 记录] **A1.3**: 配置 DNS 记录 (5 个子域名 A 记录)
- [DONE: 2026-07-21 15:35] **A1.4**: 服务器初始化 (Ubuntu 22.04, Docker, Nginx) — SSH 通, Docker 29.6.2 + Compose v5.3.1 + Nginx 1.18.0 + UFW (22/80/443) + 2G swap + /opt/copiano/ 目录 + Docker log 轮转 (10m×3)
- [BLOCKED: 依赖 A1.3 DNS] **A1.5**: 申请 Let's Encrypt SSL 证书
- [DONE: 2026-07-21 15:38] **A1.6**: 部署 PostgreSQL 16 + Redis 7 — Docker Compose,localhost-only 端口,AOF 持久化,健康检查,密码在 .env (gitignore),2 服务 healthy
- [BLOCKED: 需用户操作 — GitHub 账号] **A1.7**: 创建 GitHub 仓库 (private)
- [BLOCKED: 需用户操作 — OpenAI 账号] **A1.8**: 申请 OpenAI API key (备份 LLM)

> W1 全部 BLOCKED,等待用户提供凭据/账号。Cron 自动从 W2 开始推进。

### W2: FastAPI 基础

- [DONE: 2026-07-21 14:30] **A2.1**: FastAPI 项目结构 (backend/) — main.py + requirements.txt + Dockerfile + README.md + .env.example + 8 冒烟测试全通过
- [DONE: 2026-07-21 14:45] **A2.2**: SQLAlchemy 2.0 模型 (User/Evaluation/Curriculum/SightReadingSession) — 4 张表 + lazy engine + 24 测试全过
- [DONE: 2026-07-21 15:00] **A2.3**: JWT Auth (signup/login/refresh/logout) + /me — bcrypt + PyJWT + 6 端点 + 25 集成测试全过
- [DONE: 2026-07-21 15:08] **A2.4**: OAuth2 (Apple/Google/WeChat 登录) — 6 端点 + PyJWT[crypto] + JWKS 验签 + 22 集成测试全过
- [DONE: 2026-07-21 15:50] **A2.5**: Alembic 数据库迁移 — 初始 migration (d263a44e8ad2) + SQLite/PG 双向测试 + 8 迁移测试 + 真 PG 部署 4 张表 + alembic/README.md
- [DONE: 2026-07-21 16:10] **A2.6**: 基础 middleware (CORS + slowapi rate_limit + structlog logging + RequestID + global exception handler) — 13 测试全过

### W3: 5 维评估 API (复用 v3.0)

- [DONE: 2026-07-21 16:30] **A3.1**: 移植 v3.0 Python 模块到 backend/services/ — eval_pitch + expressiveness + hand_pose + senior_mode 直接复用,evaluation_service 编排 5 维, 20 测试全过
- [PENDING] **A3.2**: /api/v1/evaluations 端点 (MIDI 上传 → 5 维)
- [PENDING] **A3.3**: /api/v1/evaluations/{id} 详情
- [PENDING] **A3.4**: /api/v1/evaluations/history 历史
- [PENDING] **A3.5**: S3/MinIO MIDI 文件存储
- [PENDING] **A3.6**: 评估结果缓存 (Redis)

### W4: 课程 + 视奏 + LLM 反馈 API

- [PENDING] **A4.1**: 移植 curriculum_v2 到 backend/services/
- [PENDING] **A4.2**: /api/v1/curriculum 端点
- [PENDING] **A4.3**: /api/v1/curriculum/blocks/{id}/complete
- [PENDING] **A4.4**: 移植 sight_reading_trainer 到 backend/
- [PENDING] **A4.5**: /api/v1/sight-reading/session + answer
- [PENDING] **A4.6**: 移植 senior_mode + LLM proxy
- [PENDING] **A4.7**: /api/v1/feedback 端点 (LLM 流式)
- [PENDING] **A4.8**: WebSocket /api/v1/ws/llm

### W5: Next.js Marketing 主页

- [PENDING] **A5.1**: Next.js 14 项目初始化 (web/)
- [PENDING] **A5.2**: Tailwind CSS + shadcn/ui 配置
- [PENDING] **A5.3**: Marketing 主页 / (Hero + 5 维 + RCT 数据)
- [PENDING] **A5.4**: /pricing 订阅页
- [PENDING] **A5.5**: /about 团队/论文
- [PENDING] **A5.6**: SEO meta + sitemap.xml
- [PENDING] **A5.7**: 部署到 copiano.com (Nginx 静态)

### W6: Next.js Web App 主体

- [PENDING] **A6.1**: NextAuth.js 配置 (Apple/Google/微信)
- [PENDING] **A6.2**: /login + /signup 页面
- [PENDING] **A6.3**: /app 路由组 (受保护页面)
- [PENDING] **A6.4**: /app/curriculum 7 天课程
- [PENDING] **A6.5**: /app/record MIDI 录音界面
- [PENDING] **A6.6**: /app/feedback 反馈历史
- [PENDING] **A6.7**: /app/progress 进度曲线 (Recharts)
- [PENDING] **A6.8**: /app/sight-reading 视奏训练
- [PENDING] **A6.9**: /app/settings 账户/银发/订阅

### W7: Web MIDI 集成

- [PENDING] **A7.1**: Web MIDI API 集成
- [PENDING] **A7.2**: 实时录音 + 评估
- [PENDING] **A7.3**: 五线谱可视化 (VexFlow 或 OpenSheetMusicDisplay)
- [PENDING] **A7.4**: 银发模式 UI 组件
- [PENDING] **A7.5**: LLM 流式响应 UI
- [PENDING] **A7.6**: PWA 配置 (离线支持)

### W8: 部署 + 测试

- [PENDING] **A8.1**: Docker Compose 生产配置
- [PENDING] **A8.2**: GitHub Actions CI/CD
- [PENDING] **A8.3**: Prometheus + Grafana 监控
- [PENDING] **A8.4**: Sentry 错误追踪
- [PENDING] **A8.5**: 性能压测 (locust.io)
- [PENDING] **A8.6**: 安全审计 (OWASP top 10)
- [PENDING] **A8.7**: 用户文档 /docs
- [PENDING] **A8.8**: 上线公告 (邮件 + 微信)

## Phase 7B: iPhone App (W9-W16)

### W9: Xcode 初始化
- [PENDING] **B9.1**: Xcode 项目 (SwiftUI iOS 16+)
- [PENDING] **B9.2**: MVVM 架构 + Combine
- [PENDING] **B9.3**: SwiftData 本地存储
- [PENDING] **B9.4**: 登录/注册 页面
- [PENDING] **B9.5**: 设备连接 (MIDI 键盘)

### W10-W16: 5 维 + 课程 + 视奏 + 银发 + 手型 + LLM + 测试 + 提交
- (类似 W6 列表,改为 SwiftUI)

## Phase 7C: 真实 RCT (W17-W25)
- (与 7A/7B 并行)
- [PENDING] **C17.1**: 联系 3 城市钢琴教师
- [PENDING] **C17.2**: IRB 申请
- [PENDING] **C17.3**: 60 台 MIDI 键盘采购
- [PENDING] **C18.1**: 招募 + 知情同意
- [PENDING] **C19.1**: 7 天真实干预
- ...

---

## Cron Tick 任务格式

每个 cron tick:
1. 找到第一个 `[PENDING]` 任务
2. 执行 (12 分钟)
3. 改状态:`[PENDING] → [DONE: 2026-07-21 HH:MM]` 或 `[BLOCKED: 原因]`
4. 更新 progress.md
5. git commit

**禁止**:
- 跳多个任务
- 改 `[DONE]` 为 `[PENDING]`
- 同一 tick 内做 > 1 任务

---

*最后更新: 2026-07-21 14:00 (Cycle 22 — 项目 pivot)*
*总任务数: ~60 (Phase 7A 36 + Phase 7B 24 + Phase 7C 10+)*
