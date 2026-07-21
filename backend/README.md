# CoPiano v4 — Backend (FastAPI)

> AI 古典钢琴教练 — 后端 API 服务
> 5 维多模态评估 + 7 天课程 + 银发模式 + LLM 流式反馈

## 快速开始

### 1. 安装依赖

```bash
cd backend/
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env,填入 DATABASE_URL / JWT_SECRET / OPENAI_API_KEY 等
```

### 3. 启动开发服务器

```bash
# 方式 1: 直接运行
python main.py

# 方式 2: uvicorn (热重载)
uvicorn main:app --reload --port 8000

# 访问:
#   - API:        http://localhost:8000/
#   - Swagger UI: http://localhost:8000/docs
#   - ReDoc:      http://localhost:8000/redoc
#   - Health:     http://localhost:8000/health
```

### 4. Docker

```bash
docker build -t copiano-api .
docker run -p 8000:8000 --env-file .env copiano-api
```

## 项目结构

```
backend/
├── main.py                    # FastAPI 入口 (Phase 7A W2 — A2.1)
├── requirements.txt           # 依赖 (fastapi, sqlalchemy, redis, ...)
├── Dockerfile                 # 生产镜像
├── .env.example               # 环境变量模板
├── README.md                  # 本文件
│
├── app/                       # (A2.2+ 填充)
│   ├── api/
│   │   └── v1/
│   │       ├── auth.py        # A2.3 JWT
│   │       ├── users.py       # A2.2
│   │       ├── evaluations.py # A3.2-A3.4
│   │       ├── curriculum.py  # A4.2-A4.3
│   │       ├── sight_reading.py # A4.5
│   │       ├── feedback.py    # A4.7
│   │       ├── senior_mode.py # A4.6
│   │       └── subscription.py
│   ├── core/                  # 配置 / 安全
│   ├── db/                    # SQLAlchemy session / Alembic
│   ├── services/              # 业务逻辑 (v3.0 模块移植)
│   │   ├── eval_pitch.py      # D1 — 音高
│   │   ├── expressiveness.py  # D2 — 表现力
│   │   ├── hand_pose.py       # D3 — 手型
│   │   ├── rhythm.py          # D4 — 节奏
│   │   ├── sight_reading.py   # D5 — 视奏
│   │   ├── curriculum.py      # 自适应课程
│   │   ├── senior_mode.py     # 银发模式
│   │   └── llm.py             # Qwen / OpenAI
│   ├── models/                # SQLAlchemy 2.0 ORM (A2.2)
│   └── schemas/               # Pydantic schemas
└── tests/                     # pytest 测试 (各 cycle 增量)
```

## 5 维评估 API (A3.2-A3.4 待实现)

```http
POST /api/v1/evaluations
Content-Type: multipart/form-data

{
  "midi_file": <binary>,
  "piece_name": "Bach Prelude in C",
  "user_age": 25
}

→ 200 OK
{
  "id": "uuid",
  "pitch_score": 0.92,
  "expressiveness_score": 0.78,
  "hand_pose_score": 0.85,
  "rhythm_score": 0.88,
  "sight_reading_score": 0.70,
  "overall_score": 0.83,
  "llm_feedback": "你的 Allegro 部分节奏非常稳定...",
  "created_at": "2026-07-21T10:00:00Z"
}
```

## 当前进度

| 任务 ID | 描述 | 状态 | 日期 |
|---------|------|------|------|
| A2.1 | FastAPI 项目结构 | ✅ DONE | 2026-07-21 |
| A2.2 | SQLAlchemy 2.0 模型 | 🟡 PENDING | - |
| A2.3 | JWT Auth (signup/login/refresh) | 🟡 PENDING | - |
| A2.4 | OAuth2 (Apple/Google) | 🟡 PENDING | - |
| A2.5 | Alembic 数据库迁移 | 🟡 PENDING | - |
| A2.6 | Middleware (CORS/rate_limit/logging) | 🟡 PENDING | - |

完整任务跟踪: [dev_plan_v4_tasks.md](../docs/dev_plan_v4_tasks.md)

## 测试

```bash
# 运行所有测试
pytest tests/ -v

# 带覆盖率
pytest tests/ -v --cov=app --cov-report=html
```

## 部署

完整部署流程见 [dev_plan_v4.md § 6 部署架构](../docs/dev_plan_v4.md)

简版:
```bash
# 服务器 (Ubuntu 22.04 + Docker)
cd /opt/copiano
git pull
docker compose up -d --build

# Nginx 反向代理
# Let's Encrypt SSL
# GitHub Actions CI/CD
```

## 关联文档

- [v4 完整开发方案](../docs/dev_plan_v4.md) — 架构、域名、商业化
- [v4 任务跟踪](../docs/dev_plan_v4_tasks.md) — ~60 任务
- [RCT 协议](../docs/real_user_rct_protocol.md) — 真实用户验证
- [v3 论文](../notes/arxiv_abstract_v3.md) — 算法基础

## 协议

- HTTP: REST + WebSocket
- Auth: JWT (HS256) + OAuth2 (Apple/Google/微信)
- 端口: 8000 (dev) / 443 (prod via Nginx)
