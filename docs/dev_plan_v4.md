# CoPiano v4 — iPhone App + Website 开发方案

> **Pivot 时刻**: 2026-07-21 14:00 — 用户决定从 CLI/Python 转向 iPhone App + 网站
> **资源假设**: 用户自有域名 + 服务器
> **开发目标**: 6 个月内发布 iOS App + 公开网站 (含 marketing + 用户后台)
> **与 v3.0 关系**: 复用 5 维评估核心算法 (D1-D5) + 7 天课程 + RCT 验证数据

---

## 1. 总体架构 (System Architecture)

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户端 (Client Layer)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐                  ┌──────────────────┐        │
│  │   iOS App         │                  │   Website        │        │
│  │   SwiftUI         │                  │   Next.js 14     │        │
│  │   iOS 16+         │                  │   (App Router)   │        │
│  │   Camera + MIDI   │                  │   Web MIDI API   │        │
│  └────────┬─────────┘                  └────────┬─────────┘        │
│           │                                       │                  │
└───────────┼───────────────────────────────────────┼──────────────────┘
            │ HTTPS/WSS                            │ HTTPS/WSS
            │                                       │
┌───────────┼───────────────────────────────────────┼──────────────────┐
│           │      API Gateway / Edge Layer         │                  │
│  ┌────────▼──────────────────────────────────────▼─────────┐         │
│  │  Nginx Reverse Proxy + Let's Encrypt SSL                  │         │
│  │  api.copiano.com (FastAPI)  app.copiano.com (Next.js)     │         │
│  │  copiano.com (Marketing)  admin.copiano.com (Dashboard)  │         │
│  └────────────────────────┬──────────────────────────────────┘         │
│                           │                                          │
│  ┌────────────────────────▼──────────────────────────────────┐         │
│  │     Backend API (FastAPI + Python)                        │         │
│  │     - 5 维评估 (复用 v3.0 Python 模块)                    │         │
│  │     - LLM proxy (Qwen 7B / GPT-4)                        │         │
│  │     - WebSocket (实时反馈)                              │         │
│  │     - Auth (JWT)                                         │         │
│  └────────┬──────────────────────┬───────────────────────┘         │
│           │                      │                                  │
│  ┌────────▼─────────┐    ┌───────▼──────────┐                      │
│  │ PostgreSQL 16    │    │ Redis 7          │                      │
│  │ users/scores/     │    │ session/cache    │                      │
│  │ sessions/courses  │    │ rate_limit       │                      │
│  └──────────────────┘    └──────────────────┘                      │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │  Storage Layer                                                │     │
│  │  - S3 / MinIO: MIDI files, audio recordings, hand pose videos │     │
│  │  - CDN (CloudFront / Cloudflare) for static assets           │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │  ML/LLM Layer                                                │     │
│  │  - Qwen 7B / GPT-4 API for feedback generation              │     │
│  │  - 5 维评估模型 (Python, run as sidecar)                   │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                       │
│              Backend Hosted on User's Server                          │
└───────────────────────────────────────────────────────────────────────┘
```

## 2. 域名 & 服务器配置

### 2.1 域名规划

| 子域名 | 用途 | 技术栈 |
|--------|------|--------|
| `copiano.com` | Marketing 主页 | Next.js 14 (Static) |
| `app.copiano.com` | 用户 Web App | Next.js 14 (App Router) |
| `api.copiano.com` | Backend API | FastAPI + Nginx |
| `admin.copiano.com` | 管理后台 | Next.js 14 + Auth |
| `docs.copiano.com` | API 文档 | FastAPI auto-docs |

DNS 配置 (用户自有域名):
```
A     copiano.com         → <SERVER_IP>
A     app.copiano.com     → <SERVER_IP>
A     api.copiano.com     → <SERVER_IP>
A     admin.copiano.com   → <SERVER_IP>
A     docs.copiano.com    → <SERVER_IP>
CNAME www.copiano.com     → copiano.com
TXT   _dmarc              → v=DMARC1; p=reject
```

### 2.2 服务器规格建议 (用户自有)

| 角色 | 配置 | 数量 | 月费估算 (云) |
|------|------|------|---------------|
| Web (Nginx + Next.js) | 2 vCPU / 4 GB | 1 | ¥100-200 |
| API (FastAPI + 模型) | 4 vCPU / 16 GB / GPU 可选 | 1 | ¥500-2000 |
| Database (PostgreSQL) | 2 vCPU / 8 GB / 100 GB SSD | 1 | ¥200-500 |
| Cache (Redis) | 1 vCPU / 2 GB | 1 | ¥50-100 |
| Storage (S3 兼容) | 1 TB | 1 | ¥30-100 |
| **合计** | | **5** | **¥880-2900/月** |

或自建服务器 (一次性):
- 单台物理机: 32 GB RAM + 8 vCPU + 1 TB SSD + GPU (RTX 4090) ≈ ¥15,000-25,000
- 适合 100-1000 用户规模

## 3. iPhone App 详细规划

### 3.1 技术栈
- **语言**: Swift 5.9+
- **UI 框架**: SwiftUI (iOS 16+)
- **架构**: MVVM + Combine
- **本地存储**: SwiftData / CoreData
- **网络**: URLSession + async/await
- **WebSocket**: Starscream
- **音频**: AVFoundation
- **MIDI**: CoreMIDI
- **手型**: Vision (VisionKit) + ARKit
- **登录**: Sign in with Apple

### 3.2 页面结构 (8 屏)
1. **Onboarding** (3 页): 介绍 / 注册 / 设备连接
2. **Home** (Tab 1): 5 维评估仪表板 + 今日推荐
3. **Practice** (Tab 2): 7 天课程 + 8 块进度
4. **Record** (模态): MIDI 录音 + 5 维即时评估
5. **Feedback** (模态): LLM 反馈 + 改进建议
6. **Progress** (Tab 3): 进度曲线 + 银发模式切换
7. **Sight Reading** (Tab 4): 4 难度视奏训练
8. **Settings** (Tab 5): 账户 / 设备 / 银发 / 帮助

### 3.3 核心 Swift 模块
```swift
// 5 维评估客户端
struct FiveDimEvaluator {
    func evaluate(midi: MIDIFile) async throws -> FiveDimScore
    // D1 pitch / D2 expressiveness / D3 hand_pose / D4 sight_reading / D5 senior
}

// 课程同步
class CurriculumService: ObservableObject {
    @Published var weekPlan: WeekPlanV2?
    @Published var currentBlock: BlockSpec?
    func fetchPlan() async throws
    func markComplete(blockId: String) async
}

// LLM 反馈客户端
class LLMFeedbackClient {
    func streamFeedback(forEvaluation: FiveDimScore) -> AsyncStream<String>
}

// 银发模式
class SeniorModeManager: ObservableObject {
    @Published var active: Bool = false
    @Published var ttsSpeed: Double = 1.0
    @AppStorage("age") var age: Int = 30
    func autoActivateIfNeeded()
}
```

### 3.4 App Store 提交
- **开发者账号**: $99/年 (Apple Developer Program)
- **审核周期**: 1-3 天 (通常)
- **关键审核要点**:
  - 隐私政策 (NSPrivacyAccessedAPIType)
  - 数据收集声明 (App Tracking Transparency)
  - Sign in with Apple 强制 (第三方登录规则)
  - MIDI / 相机 / 麦克风权限描述

## 4. Website 详细规划

### 4.1 技术栈
- **框架**: Next.js 14 (App Router) + React 18
- **样式**: Tailwind CSS 3 + shadcn/ui
- **状态**: Zustand (轻量) + TanStack Query
- **Web MIDI**: Web MIDI API + Web Audio API
- **可视化**: Recharts (5 维雷达图)
- **认证**: NextAuth.js v5 (支持 Apple/Google/微信登录)

### 4.2 页面结构 (5 路由)
```
/                       # Marketing 主页 (Hero + 5 维演示 + 真实 RCT 数据)
/demo                   # 在线 Demo (Web MIDI 试用,无需登录)
/login                  # 登录 (Apple/Google/微信)
/signup                 # 注册 (含 14 天试用)
/app                    # 用户后台 (登录后)
  /app/curriculum       # 7 天课程
  /app/record           # MIDI 录音 + 评估
  /app/feedback         # LLM 反馈历史
  /app/progress         # 进度曲线
  /app/sight-reading    # 视奏训练
  /app/settings         # 账户/银发/订阅
/pricing                # 订阅价格 (免费 + Pro ¥29/月 + Senior 免费)
/api-docs               # API 文档 (自动生成)
/about                  # 团队 / 论文 / 联系方式
/blog                   # 钢琴学习博客 (SEO)
```

### 4.3 关键 Web 组件
```tsx
// 5 维雷达图
<FiveDimRadar scores={scores} />

// 课程进度
<CurriculumWeek
  days={7}
  blocks={blockTypes}
  currentDay={3}
  onComplete={markComplete}
/>

// 实时 MIDI 评估
<MIDIRecorder
  onNote={(pitch, velocity) => updateScore(pitch, velocity)}
  showStaff={true}
  visualFeedback="color-bars"
/>

// 银发模式 UI
<SeniorToggle
  fontSize="2x"
  highContrast
  simplifiedEmoji
  onChange={updateTtsAndLLM}
/>

// LLM 流式反馈
<LLMStream
  message={userInput}
  system={systemPrompt}
  onChunk={(chunk) => appendText(chunk)}
  onComplete={finalize}
/>
```

## 5. Backend API 详细规划

### 5.1 技术栈
- **框架**: FastAPI 0.110+ (async)
- **Python**: 3.11+
- **DB**: PostgreSQL 16 + SQLAlchemy 2.0
- **Cache**: Redis 7
- **LLM**: Qwen 7B (本地) + OpenAI API (备份)
- **Auth**: JWT (PyJWT) + OAuth2
- **WebSocket**: FastAPI native
- **任务队列**: Celery (邮件/统计)
- **监控**: Prometheus + Grafana

### 5.2 API 设计 (REST + WebSocket)

```
REST 端点 (FastAPI):

# 用户
POST   /api/v1/auth/signup            # 注册
POST   /api/v1/auth/login             # 登录 (返回 JWT)
POST   /api/v1/auth/refresh           # 刷新 token
GET    /api/v1/users/me               # 当前用户

# 评估
POST   /api/v1/evaluations            # 提交 MIDI 评估 → 返回 5 维
GET    /api/v1/evaluations/{id}       # 获取评估详情
GET    /api/v1/evaluations/history    # 历史评估

# 课程
GET    /api/v1/curriculum             # 7 天课程
POST   /api/v1/curriculum/blocks/{id}/complete  # 标记完成

# 视奏
POST   /api/v1/sight-reading/session  # 开始视奏
POST   /api/v1/sight-reading/answer   # 提交答案

# LLM 反馈
POST   /api/v1/feedback               # 请求 LLM 反馈
GET    /api/v1/feedback/history       # 反馈历史

# 银发模式
PUT    /api/v1/senior-mode            # 切换银发模式 (auto if age >= 60)

# 订阅
GET    /api/v1/subscription           # 订阅状态
POST   /api/v1/subscription/checkout  # 创建支付会话

WebSocket 端点:
WS     /api/v1/ws/llm                 # LLM 流式响应
WS     /api/v1/ws/evaluate             # 实时评估
```

### 5.3 数据库设计 (PostgreSQL)

```sql
-- 用户表
CREATE TABLE users (
  id UUID PRIMARY KEY,
  email VARCHAR UNIQUE NOT NULL,
  password_hash VARCHAR,
  apple_id VARCHAR UNIQUE,
  age INT,
  senior_mode BOOLEAN DEFAULT FALSE,
  subscription_tier VARCHAR DEFAULT 'free',  -- free / pro / senior
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 评估记录
CREATE TABLE evaluations (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  piece_name VARCHAR,
  midi_url VARCHAR,         -- S3 路径
  pitch_score FLOAT,
  expressiveness_score FLOAT,
  hand_pose_score FLOAT,
  rhythm_score FLOAT,
  sight_reading_score FLOAT,
  llm_feedback TEXT,         -- LLM 反馈
  created_at TIMESTAMP DEFAULT NOW()
);

-- 课程进度
CREATE TABLE curriculum_progress (
  user_id UUID REFERENCES users(id),
  day_num INT,
  block_id VARCHAR,
  completed_at TIMESTAMP,
  PRIMARY KEY (user_id, day_num, block_id)
);

-- 视奏记录
CREATE TABLE sight_reading_sessions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  difficulty VARCHAR,        -- beginner/elementary/intermediate/advanced
  mode VARCHAR,              -- random/interval/piece
  accuracy FLOAT,
  streak INT,
  notes_per_minute FLOAT,
  started_at TIMESTAMP,
  ended_at TIMESTAMP
);

-- 索引
CREATE INDEX idx_evaluations_user_created ON evaluations(user_id, created_at DESC);
CREATE INDEX idx_sight_reading_user ON sight_reading_sessions(user_id, started_at DESC);
```

## 6. 部署架构 (Deployment)

### 6.1 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports: ['80:80', '443:443']
    volumes: ['./nginx.conf:/etc/nginx/nginx.conf', './certs:/etc/nginx/certs']
    depends_on: [api, web, docs]

  api:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://user:pass@postgres:5432/copiano
      REDIS_URL: redis://redis:6379
      QWEN_API_URL: http://qwen:8080
      JWT_SECRET: ${JWT_SECRET}
    depends_on: [postgres, redis, qwen]
    deploy:
      resources: { limits: { cpus: '4', memory: 8G } }

  web:
    build: ./web
    environment: { NEXT_PUBLIC_API_URL: https://api.copiano.com }
    depends_on: [api]

  docs:
    build: ./docs

  postgres:
    image: postgres:16-alpine
    environment: { POSTGRES_PASSWORD: ${DB_PASSWORD} }
    volumes: ['pgdata:/var/lib/postgresql/data']
    deploy:
      resources: { limits: { cpus: '2', memory: 4G } }

  redis:
    image: redis:7-alpine
    deploy:
      resources: { limits: { cpus: '1', memory: 1G } }

  qwen:  # 可选本地 Qwen 7B (无 GPU 时关闭,用 OpenAI API)
    image: modelscope/qwen2.5-7b-instruct
    deploy:
      resources: { limits: { cpus: '4', memory: 16G } }
      reservations: { devices: [{ capabilities: [gpu] }] }

  minio:  # S3 兼容存储
    image: minio/minio
    command: server /data --console-address ":9001"

volumes:
  pgdata:
```

### 6.2 Nginx 配置 (snippet)

```nginx
# /etc/nginx/nginx.conf
upstream api { server api:8000; }
upstream web { server web:3000; }

server {
  listen 443 ssl http2;
  server_name api.copiano.com;
  ssl_certificate /etc/nginx/certs/fullchain.pem;
  ssl_certificate_key /etc/nginx/certs/privkey.pem;

  location / {
    proxy_pass http://api;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }

  location /ws {
    proxy_pass http://api;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
  }
}

server {
  listen 443 ssl http2;
  server_name app.copiano.com;
  location / { proxy_pass http://web; }
}

server {
  listen 443 ssl http2;
  server_name copiano.com www.copiano.com;
  root /var/www/marketing;
  index index.html;
}

# HTTP → HTTPS 重定向
server {
  listen 80;
  server_name _;
  return 301 https://$host$request_uri;
}
```

### 6.3 SSL 证书 (Let's Encrypt)

```bash
# 安装 certbot
apt install certbot python3-certbot-nginx

# 申请证书 (覆盖所有子域名)
certbot --nginx -d copiano.com -d app.copiano.com -d api.copiano.com -d admin.copiano.com -d docs.copiano.com

# 自动续期
echo "0 0 1 * * certbot renew --quiet" | crontab -
```

### 6.4 CI/CD (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: pytest

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /opt/copiano
            git pull
            docker compose build
            docker compose up -d
            docker system prune -f
```

## 7. 实施路线图 (Timeline)

### Phase 7A: 后端 + 网站 (W1-W8, 8 周)
- W1: 服务器配置 + DNS + SSL + Docker + DB
- W2: FastAPI 基础 + Auth + 用户表
- W3: 5 维评估 API (复用 v3.0 Python 模块)
- W4: 课程 API + 视奏 API + LLM 反馈
- W5: Next.js Marketing 主页 + 登录/注册
- W6: Next.js Web App 主体 (5 屏)
- W7: Web MIDI 集成 + 评估界面
- W8: 部署 + 测试 + 性能优化

### Phase 7B: iPhone App (W9-W16, 8 周)
- W9: Xcode 项目初始化 + SwiftUI 架构
- W10: 登录 + 5 维评估 UI + MIDI 集成
- W11: 7 天课程 UI + 视奏训练
- W12: 银发模式 + TTS/ASR 集成
- W13: 手型相机集成 (Vision)
- W14: LLM 反馈 + 实时
- W15: 内部测试 (TestFlight)
- W16: App Store 提交

### Phase 7C: 真实 RCT (W17-W25, 8 周) [与 Phase 7A/B 并行]
- W17: 招募 60 用户
- W18: Day 0 baseline
- W19: 7 天干预
- W20: 终评
- W21: 数据分析
- W22-W24: 论文 v4 撰写
- W25: 投稿 NIME/CHI

## 8. 商业化 (Monetization)

### 8.1 订阅层级

| 层级 | 价格 | 功能 |
|------|------|------|
| **免费** | ¥0 | 5 维评估 (每月 3 次) + 基础反馈 |
| **Pro** | ¥29/月 | 无限评估 + 7 天课程 + LLM 详细反馈 |
| **Senior** | ¥0 | Pro 全部 + 银发模式 + 简化 UI |
| **教师** | ¥99/月 | 班级管理 + 学生进度跟踪 |
| **学校** | ¥999/月 | SSO + 定制课程 + 培训 |

### 8.2 支付集成
- **国内**: 微信支付 + 支付宝 (Ping++ 聚合)
- **海外**: Stripe
- **订阅管理**: 微信支付分账 / Stripe Billing
- **发票**: 微信电子发票 / Stripe Tax

## 9. 团队 (Team)

最小可行团队 (MVP):
- **1 全栈 (你)**: FastAPI + Next.js + iOS
- **1 设计**: UI/UX (Figma)
- **1 兼职**: 内容运营 (钢琴学习内容)

扩展团队 (RCT 启动后):
- **+1 学术顾问**: 钢琴教育/AI 教授
- **+1 商务**: 钢琴教师合作 + 老年大学 BD
- **+1 客服**: 老年用户支持

## 10. 风险与缓解 (Risks)

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| iOS 审核被拒 | 中 | 高 | 提前 2 周准备审核材料 + 隐私政策 |
| 服务器宕机 | 中 | 中 | 云双活 + 监控告警 |
| LLM 成本失控 | 中 | 中 | 本地 Qwen 7B + 缓存 + 限流 |
| 银发用户难上手 | 高 | 高 | 视频教程 + 上门培训 + 简化 UI |
| RCT 招募不足 | 中 | 高 | 3 渠道 + 老年大学 + 钢琴老师 |
| 现金流断裂 | 中 | 高 | 个人储蓄 + 学校合作 + 教育基金 |

## 11. 立即可执行 (W0 任务)

W0 任务 (本周末前完成):
1. [ ] 申请/激活 Apple Developer 账号 ($99)
2. [ ] 注册域名 (如未注册)
3. [ ] 部署 SSL 证书 (Let's Encrypt)
4. [ ] 服务器初始化 (Docker + Nginx + Postgres)
5. [ ] 初始化 GitHub 仓库 (private 优先)
6. [ ] 申请 OpenAI API key (LLM 备份)
7. [ ] 准备 iOS 项目目录结构

## 12. Cron 任务调整

**新规则**:
1. 每个 cron tick 读取 `docs/dev_plan_v4.md` 找下一个 `[PENDING_TASK]`
2. 完成一个任务 → 标 `[DONE: YYYY-MM-DD HH:MM]`
3. 失败 → 标 `[BLOCKED: 原因]`
4. 全部 Phase 7A 任务完成 → 写 `[PHASE_7A_DONE]` 标
5. 见到 `[DONE]` (项目级) → 停止

每个 cron tick 一次只做一件事 (12 分钟上限), 不能跳过。

---

*本文档由 cron 驱动,每 tick 自动推进,见 `docs/dev_plan_v4_tasks.md` 跟踪状态*
*详细技术栈、API、UI 计划见上述章节*
*最后更新: 2026-07-21 14:00 (Cycle 22 — 项目方向 pivot)*
