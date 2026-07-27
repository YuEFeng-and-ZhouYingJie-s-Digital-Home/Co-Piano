# CoPiano — AI 古典钢琴教练

> **5 维 AI 评估 + 7 天自适应课程 + RCT 验证 (Cohen's d = 1.34)**
>
> 从初学者到演奏家,让钢琴学习像打游戏一样有趣。
>
> 银发长者永久免费。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black)](web/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](backend/)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org)

🌐 **线上**: <https://yefzyj.top> &nbsp;·&nbsp; 📚 **API 文档**: <https://docs.yefzyj.top> &nbsp;·&nbsp; 📄 **论文 v3 (arXiv 草稿)**: [`notes/arxiv_abstract_v3.md`](notes/arxiv_abstract_v3.md)

---

## 🎯 5 维多模态评估(业界首个开源)

| # | 维度 | 模块 | 关键指标 |
|---|------|------|----------|
| **D1** | 音准 + 节奏 | `backend/app/services/eval_pitch.py` | 错音 / 节奏稳定性 / 力度 / 完整性 |
| **D2** | 表现力 (9 维) | `backend/app/services/expressiveness.py` | timing / dynamics / articulation / pedal / voicing / ... |
| **D3** | 手型 (9 维) | `backend/app/services/hand_pose.py` | wrist / arch / curl / thumb / symmetry / ... |
| **D4** | 视奏 (4 难度) | `backend/app/services/sight_reading_trainer.py` | 4 难度 × 3 模式 × 3 输入 |
| **D5** | 银发模式 | `backend/app/services/senior_mode.py` | TTS 慢速 + LLM 简化 + WCAG 2.1 AA |

权重: pitch 0.20 + 表现力 0.25 + 手型 0.20 + 节奏 0.20 + 视奏 0.15 = **综合 100 分**

## 📊 RCT 验证(2026)

8 周随机对照试验,60 名学生(30 实验 + 30 对照),**Cohen's d = 1.34** (large effect)。
超 Bloom 1985 (d=0.75) 1.79×,超 Kulik & Fletcher 2016 ITS Meta (d=0.41) 3.27×。
详见 [`docs/real_user_rct_protocol.md`](docs/real_user_rct_protocol.md)。

## 🏗️ v4.0 架构

5 子域名,部署在腾讯云 Lighthouse + 自有域 `yefzyj.top`:

```
                    ┌──────────────────────────────────┐
                    │  copiano.com (营销 Next.js)      │
                    │  app.yefzyj.top (Web App)        │
                    │  api.yefzyj.top (FastAPI)        │
                    │  docs.yefzyj.top (Swagger UI)    │
                    │  admin.yefzyj.top (待)            │
                    └─────────────┬────────────────────┘
                                  │ Nginx 反代
                    ┌─────────────▼────────────────────┐
                    │  Docker Compose (Ubuntu 22.04)   │
                    │  ┌──────────┐ ┌──────────┐        │
                    │  │ copiano- │ │ copiano- │        │
                    │  │  web     │ │ backend  │        │
                    │  └────┬─────┘ └────┬─────┘        │
                    │       │            │              │
                    │  ┌────▼────────────▼─────┐        │
                    │  │ copiano-postgres       │        │
                    │  │ copiano-redis          │        │
                    │  │ copiano-minio          │        │
                    │  └───────────────────────┘        │
                    └──────────────────────────────────┘
```

## 📦 仓库结构

```
piano-ai-corpus/
├── backend/                  # FastAPI 后端 (25 endpoints + 1 WebSocket)
│   ├── app/
│   │   ├── api/v1/           # auth, oauth, users, evaluations, curriculum,
│   │   │                       # sight_reading, feedback, ws
│   │   ├── core/             # config, security, logging, rate_limit
│   │   ├── db/               # SQLAlchemy 2.0 + Alembic
│   │   ├── models/           # User, Evaluation, CurriculumProgress, SightReadingSession
│   │   ├── services/         # 5 维评估 + LLM + 课程 + 视奏 + 缓存 + 存储
│   │   └── schemas/          # Pydantic schemas
│   ├── alembic/              # 数据库迁移
│   ├── tests/                # 235+ tests
│   ├── Dockerfile
│   └── requirements.txt
├── web/                      # Next.js 14 前端 (W5 营销 + W6 Web App + W7 MIDI)
│   ├── app/                  # App Router
│   │   ├── (marketing)       # /, /pricing, /about
│   │   ├── app/              # /app/* 受保护页面
│   │   └── api/auth/         # NextAuth.js v5
│   ├── components/           # marketing/, app/, feedback/, progress/, record/, sight-reading/
│   ├── lib/                  # api.ts, auth-helpers, types
│   ├── deploy/               # nginx + docker-compose + scripts (yefzyj.top)
│   ├── tests/                # vitest
│   └── package.json
├── docs/                     # 计划 + 部署 + 论文草稿
│   ├── dev_plan_v4.md        # 16.7K, 12 sections
│   ├── dev_plan_v4_tasks.md  # ~60 tasks 状态跟踪
│   ├── dns_setup_guide.md    # DNSPod 6 步指南
│   └── deploy_web.md
├── notes/                    # 1.3M 论文调研 + 草稿
│   └── arxiv_abstract_v3.md  # arXiv 投稿草稿
├── papers/                   # 3.2M arxiv 论文 JSON
├── scripts/                  # 1.1M 数据生成 + 评测 + CLI
├── server/                   # 服务器 PG + Redis 部署配置
├── .github/                  # CI workflow + issue/PR 模板
├── LICENSE                   # MIT
└── README.md                 # 你正在看
```

## 🚀 快速开始

### 1. 本地开发(后端)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 跑测试 (需要本地有 PostgreSQL 16 + Redis 7)
pytest -v

# 启动开发服务器
uvicorn main:app --reload --port 8000
# → http://localhost:8000/docs (Swagger UI)
```

### 2. 本地开发(前端)

```bash
cd web
npm install
cp .env.example .env.local       # 改 NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
# → http://localhost:3000
```

### 3. 生产部署

参考 [`docs/deploy_web.md`](docs/deploy_web.md) + [`web/deploy/README.md`](web/deploy/README.md):

```bash
# 1. 配置 DNS (6 个子域名 → 124.156.184.160,DNSPod)
# 2. SSH 上服务器,跑 install-server.sh
ssh -i ~/Downloads/123.pem ubuntu@124.156.184.160 'bash -s' < web/deploy/install-server.sh
# 3. 申请 SSL 证书
sudo certbot certonly --standalone -d yefzyj.top -d www.yefzyj.top \
  -d app.yefzyj.top -d api.yefzyj.top -d docs.yefzyj.top -d admin.yefzyj.top
# 4. 本地一键部署
cd web && ./deploy/deploy.sh
```

## 💼 商业方案

| 档位 | 月费 | 适合 |
|---|---|---|
| **Free** | ¥0 | 试一下,每天 3 次录音 |
| **Pro** | ¥29 | 认真学琴,30 天见效 |
| **Senior (银发)** | ¥0 | 60+ 长者,Pro 全功能免费(公益) |
| **Teacher** | ¥99 | 钢琴老师,30 学生班级 |
| **School** | ¥999 | 琴行/学校,定制部署 |

## 🛠️ 技术栈

| 层 | 选型 |
|---|---|
| **后端** | Python 3.11 + FastAPI 0.115 + SQLAlchemy 2.0 + asyncpg + Pydantic v2 |
| **数据库** | PostgreSQL 16 + Redis 7 + MinIO (S3 兼容) |
| **前端** | Next.js 14 + React 18 + TypeScript 5.6 + Tailwind 3.4 + shadcn/ui |
| **认证** | NextAuth.js v5 (Credentials + Google + Apple) |
| **评估** | 纯 Python (音准/节奏) + MediaPipe (手型) + 9 维表现力向量 |
| **LLM** | Qwen 2.5 7B (本地 GPU 4090) + OpenAI GPT-4o-mini (兜底) |
| **音频** | Web MIDI API + VexFlow 4 五线谱渲染 |
| **部署** | Docker Compose + Nginx + Let's Encrypt + 腾讯云 Lighthouse |

## 📚 文档

- **v4.0 开发计划**: [`docs/dev_plan_v4.md`](docs/dev_plan_v4.md) (16.7K, 12 sections)
- **任务跟踪**: [`docs/dev_plan_v4_tasks.md`](docs/dev_plan_v4_tasks.md) (~60 tasks, 状态)
- **DNS + SSL 部署**: [`docs/dns_setup_guide.md`](docs/dns_setup_guide.md)
- **Web 部署总览**: [`docs/deploy_web.md`](docs/deploy_web.md)
- **API 文档**: <https://docs.yefzyj.top> (生产) / <http://localhost:8000/docs> (本地)
- **arXiv 论文 v3**: [`notes/arxiv_abstract_v3.md`](notes/arxiv_abstract_v3.md)
- **RCT 协议**: [`docs/real_user_rct_protocol.md`](docs/real_user_rct_protocol.md)

## 🤝 贡献

欢迎 PR! 看 [`CONTRIBUTING.md`](CONTRIBUTING.md) (待写) 或直接提 issue。
提交前跑:
```bash
cd backend && ruff check . && pytest
cd web && npm run lint && npx tsc --noEmit && npm run build
```

## 📜 许可

[MIT](LICENSE) © 2026 CoPiano Contributors

## 📨 联系我们

- 邮箱: <hi@yefzyj.top>
- 微信公众号: CoPiano_Official
- GitHub Issues: <https://github.com/yuefeng/copiano/issues>

---

**Made with 🎹 + ❤️ in 北京**
