# CoPiano 生产环境 — PostgreSQL + Redis

> 部署在腾讯云 Lighthouse (124.156.184.160, Ubuntu 22.04)
> A1.6 任务产出 (2026-07-21)

## 架构

```
┌─────────────────────────────────────────────┐
│  Tencent Cloud Lighthouse (1.9G RAM + 2G)  │
│  /opt/copiano/postgres/                     │
│                                             │
│  ┌──────────────────┐  ┌────────────────┐   │
│  │ copiano-postgres │  │ copiano-redis  │   │
│  │ 16-alpine        │  │ 7-alpine       │   │
│  │ port 5432        │  │ port 6379      │   │
│  │ 36 MiB / 512M    │  │ 13 MiB / 256M  │   │
│  └──────────────────┘  └────────────────┘   │
│         ↕ localhost only (127.0.0.1)        │
│  ┌──────────────────────────────────────┐   │
│  │  copiano-api (FastAPI)               │   │
│  │  port 8000 → Nginx → :443            │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## 部署步骤

```bash
# 1. SSH 登录
ssh -i ~/Downloads/123.pem ubuntu@124.156.184.160

# 2. 创建目录
mkdir -p /opt/copiano/postgres/{data,init}
mkdir -p /opt/copiano/redis/data

# 3. 写入 docker-compose.yml (见同目录)
# 4. 写入 .env (含密码,已 gitignore)

# 5. 拉镜像 + 启动
cd /opt/copiano/postgres
docker compose pull
docker compose up -d

# 6. 验证
docker compose ps           # 两个服务应 healthy
docker exec copiano-postgres psql -U copiano -d copiano -c 'SELECT 1;'
docker exec copiano-redis redis-cli -a $REDIS_PASSWORD PING
```

## 资源限制

| 服务 | CPU 上限 | 内存上限 | 当前使用 |
|------|---------|---------|---------|
| postgres | 1 vCPU | 512 MB | ~37 MB |
| redis | 0.5 vCPU | 256 MB | ~13 MB |

合计 ~50 MB,适合 1.9G 内存服务器 + 2G swap。

## 关键设计

- **localhost only** — 5432/6379 只绑定 127.0.0.1,外部访问必须经过 FastAPI
- **AOF 持久化** — Redis 开启 appendonly,数据可恢复
- **LRU 淘汰** — maxmemory 200mb + allkeys-lru,防 OOM
- **持久卷** — PostgreSQL data 在 /opt/copiano/postgres/data (主机)
- **健康检查** — 10s 间隔,3 次失败重启
- **重启策略** — unless-stopped (服务器重启后自动起)
- **环境变量** — 密码在 .env 中 (不在 docker-compose.yml),遵循 12-factor app
- **TZ Asia/Shanghai** — DB 时间戳和业务时间一致

## 连接字符串

供 FastAPI `.env` 使用:

```bash
DATABASE_URL=postgresql+asyncpg://copiano:XXX@127.0.0.1:5432/copiano
DATABASE_URL_SYNC=postgresql://copiano:XXX@127.0.0.1:5432/copiano
REDIS_URL=redis://:XXX@127.0.0.1:6379/0
```

(XXX 替换为 .env 里的实际密码)

## 备份策略 (待 A8.x 完善)

当前: 仅本地持久卷
后续:
- 每日 `pg_dump` 备份到 /opt/copiano/backups/
- 定期上传到 S3 / COS
- Redis: AOF 文件周期归档

## 下一步

- A2.5 Alembic 迁移 (把 4 张表 schema 部署到 PostgreSQL)
- A3.x 5 维评估 API (用真实 DB 测试)
- A8.x 监控 + 备份 + 安全审计
