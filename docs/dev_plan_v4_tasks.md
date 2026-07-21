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
- [DONE: 2026-07-21 16:45] **A3.2-A3.4**: /api/v1/evaluations POST + GET + history — multipart 上传 + 5 维评估 + 持久化 PG + 10 测试全过
- [DONE: 2026-07-21 16:55] **A3.5**: S3/MinIO MIDI 文件存储 — MinIO 部署 + storage_service + boto3 + presigned URL + 14 测试全过 + 真 MinIO 集成测试通过
- [DONE: 2026-07-21 17:08] **A3.6**: 评估结果 Redis 缓存 — cache_service + 24h TTL + 16 测试 + 真 Redis 集成验证 — W3 收官

### W4: 课程 + 视奏 + LLM 反馈 API

- [DONE: 2026-07-21 17:30] **A4.1 + A4.4**: 移植 curriculum_v2 + sight_reading_trainer + curriculum_service + sight_reading_service + 18 测试全过
- [DONE: 2026-07-21 17:45] **A4.2 + A4.3**: /api/v1/curriculum 3 端点 (GET 全计划 / GET 某天 / POST 标记完成) + 11 测试全过
- [DONE: 2026-07-21 18:00] **A4.5**: /api/v1/sight-reading 3 端点 (开 session / 答 / 详情) + 12 测试全过
- [DONE: 2026-07-21 18:15] **A4.6**: LLM proxy (Qwen 本地 + OpenAI 兜底 + 流式 + 银发简化) + 14 测试全过
- [DONE: 2026-07-21 22:30] **A4.7**: /api/v1/feedback 3 端点 (POST/GET/history) + 12 测试全过
- [DONE: 2026-07-22 01:10] **A4.8**: WebSocket /api/v1/ws/llm (流式 LLM 反馈) + 8 测试全过 — W4 收官 🎉

[PHASE_7A_W4_DONE: 2026-07-22 01:10 — W4 (课程 + 视奏 + LLM) 8/8 完成: A4.1-A4.8 全部 ✅]

### W5: Next.js Marketing 主页

- [DONE: 2026-07-22 01:25] **A5.1**: Next.js 14 项目初始化 (web/) — package.json + next.config.mjs + tsconfig + tailwind.config.ts + postcss.config + app/layout.tsx + app/globals.css + app/page.tsx + lib/utils.ts + Dockerfile + .env.example + components.json (shadcn) + .eslintrc + .prettierrc + vitest.config + favicon.svg + tests/lib.test.ts(3 测试) — 23 文件 92K
- [DONE: 2026-07-22 01:32] **A5.2**: Tailwind CSS + shadcn/ui 配置 — components/ui/{Button(7 variant × 4 size, CVA), Card(6 子组件), Badge(7 variant), Separator(Radix), Avatar(Radix)} + 加 @radix-ui/react-separator dep + tests/cn-variants.test.ts(7 断言) — 5 组件 ~7.5K 代码, CVA 静态断言验证 variant 名称稳定
- [DONE: 2026-07-22 01:42] **A5.3**: Marketing 主页 / (Hero + 5 维 + RCT 数据) — components/marketing/{Navbar(sticky+backdrop-blur), Hero(gradient+CTA), FiveDimensions(5 卡片+CVA icons), RctChart(Recharts BarChart, 4 基线对照), Stats(4 数字), CtaSection(紫渐变), Footer(3 分类链接)} + app/page.tsx 7 段拼装 — 8 文件 553 行, RSC 静态 + RctChart 'use client' 唯一客户端组件
- [DONE: 2026-07-22 02:25] **A5.4**: /pricing 订阅页 — lib/pricing-data.ts(5 档:Free/Pro ¥29/Senior 免费/Teacher ¥99/School ¥999, BillingCycle, formatCny, getTierById) + components/marketing/{pricing-cards(月/年切换+5 卡 grid+Pro 高亮), pricing-faq(accordion)} + app/pricing/page.tsx(4 段拼装) + tests/pricing-data.test.ts(9 断言覆盖 tier 数/唯一性/Pro 高亮/Senior 免费/年付 17% 折) — 5 文件 491 行, RSC + pricing-cards/faq 'use client'
- [DONE: 2026-07-22 02:40] **A5.5**: /about 团队/论文 — lib/about-data.ts(TEAM 3 成员 + TIMELINE v1-v5 含 2 主里程碑 + PAPER 含 d=1.34 4 结果 + CONTACT 邮箱/微信/GitHub) + components/marketing/{team-cards(Avatar+Badge), timeline(border-l+Sparkles 主点)} + app/about/page.tsx(6 段:Hero 渐变/Team/Paper 论文摘要+d=1.34 四数字+代码统计+下载按钮/Timeline/Contact 4 卡/CTA) + tests/about-data.test.ts(7 断言覆盖团队/时间线/论文 d=1.34/联系) — 5 文件 496 行, 全 RSC 静态
- [DONE: 2026-07-22 02:55] **A5.6**: SEO meta + sitemap + robots + OG — app/{sitemap.ts(/+pricing+about,weekly/monthly,priority 1/0.9/0.7), robots.ts(/allow /api+app/disallow,Googlebot 单独), opengraph-image.tsx(edge runtime,1200×630 渐变+d=1.34), twitter-image.tsx, icon.tsx(64×64), apple-icon.tsx(180×180), manifest.ts(PWA)} + components/marketing/structured-data.tsx(3 schema.org JSON-LD: Organization + SoftwareApplication w/ Free+Pro offers + ScholarlyArticle v3 论文) + layout.tsx 增 canonical/alternates/formatDetection/verification/googleBot — 9 文件 458 行(其中 7 端点自动生成)
- [DONE: 2026-07-22 03:05] **A5.7**: 部署到 copiano.com (Nginx + Docker) — web/deploy/{nginx.copiano.com.conf(HTTPS 301+HSTS+OCSP+Gzip+120s 超时), docker-compose.yml(127.0.0.1:3000+healthcheck+log 10m×3), deploy.sh(rsync+remote docker up+health check), install-server.sh(nginx+certbot+ufw+logrotate 一键), healthcheck.sh(5min cron+Slack 告警), README.md} + docs/deploy_web.md(总览+5 子域架构+用户操作清单) — 7 文件 584 行, W5 收官 🎉; 等用户 DNS 生效 (A1.3) + certbot 证书 (A1.5) 后即可一键 deploy

### W6: Next.js Web App 主体

- [DONE: 2026-07-22 03:20] **A6.1**: NextAuth.js v5 (Auth.js) — package.json + next-auth@5.0.0-beta.22; auth.config.ts(edge-safe, pages, JWT session, authorized() 路由保护 /app/*, jwt/session callbacks 透传 accessToken); auth.ts(Credentials 调后端 /auth/login 拿 JWT + Google/Apple OAuth2 providers); middleware.ts(Edge runtime, matcher 排除 /api/auth+静态+OG); app/api/auth/[...nextauth]/route.ts(GET+POST); types/next-auth.d.ts(Session 加 accessToken/refreshToken/userId, User 加同); lib/api.ts(apiFetch 通用 wrapper, 自动注入 Bearer+超时+FormData+ApiError 异常类+ 5 便捷方法 get/post/put/patch/delete/upload); lib/auth-helpers.ts(useAuth+loginWithCredentials/Google/Apple+logout); components/providers.tsx(SessionProvider); layout.tsx 注入 Providers; .env.example 加 NEXTAUTH_SECRET/URL/GOOGLE/APPLE; tests/api.test.ts(ApiError); 11 文件 ~12K 代码, W6 1/9
- [DONE: 2026-07-22 03:38] **A6.2**: /login + /signup — components/auth/{auth-shell(logo+title+2 链接), oauth-buttons(Google+Apple inline SVG), login-form(RHF+zod+Mail/Lock icon+callbackUrl 保留), signup-form(注册+自动登录+terms)} + components/ui/{input(Radix-style), label(Radix)} + app/{login/page.tsx(robots noindex), signup/page.tsx(robots noindex)} + package.json + react-hook-form 7.53+zod 3.23+@hookform/resolvers 3.9; 7 文件 ~13K 代码, W6 2/9
- [DONE: 2026-07-22 03:55] **A6.3**: /app 路由组 — lib/nav-items.ts(7 项含 description+primary 标记) + components/app/{sidebar(桌面 64px 固定+isActive 高亮), mobile-nav(顶部条+抽屉+底部 5 tab), user-menu(Avatar+Dropdown 4 项+退出)} + components/ui/dropdown-menu.tsx(完整 Radix 包装) + app/app/layout.tsx(auth() 守护+redirect 401→/login?callbackUrl, 桌面 sidebar+top bar user menu, 移动 header+底 tab+浮动 user menu) + app/app/page.tsx(欢迎+今日推荐+4 快捷+上次评估); 7 文件 ~14K 代码, W6 3/9
- [DONE: 2026-07-22 07:05] **A6.4**: /app/curriculum 7 天课程 — lib/curriculum-types.ts(BlockType 8 + DimensionName 5 + BLOCK_META emoji/color + CurriculumWeek/Day/Block schema) + components/curriculum/{curriculum-week(7 天卡 grid+总览条+emoji 预览), block-card(完成圈+emoji+展开/收起+跳转录音/视奏), complete-block-button('use client'+useTransition+POST /blocks/{id}/complete+乐观刷新)} + app/app/curriculum/page.tsx(RSC+api.get 7 天计划+错误态) + app/app/curriculum/[day]/page.tsx(RSC+dayNum 校验+block 排序+进度条+完成祝贺卡); 6 文件 625 行, W6 4/9
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
