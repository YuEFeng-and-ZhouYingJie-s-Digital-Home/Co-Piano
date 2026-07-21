# Alembic — 数据库迁移

> CoPiano 后端的 schema 演进工具
> 配置时间: 2026-07-21 (A2.5)

## 快速使用

```bash
cd backend/
source venv/bin/activate

# 1. 应用所有 migration 到 head
DATABASE_URL_SYNC="postgresql://copiano:XXX@127.0.0.1:5432/copiano" \
  alembic upgrade head

# 2. 查看当前 revision
alembic current

# 3. 查看历史
alembic history --verbose

# 4. 改完 ORM 模型后,自动生成新 migration
alembic revision --autogenerate -m "add field xxx"

# 5. 回滚 1 步
alembic downgrade -1

# 6. 回滚到最初
alembic downgrade base
```

## 配置文件

- `alembic.ini` — alembic 全局配置
  - `script_location = alembic`
  - `sqlalchemy.url = sqlite:///./copiano.db` (默认值,实际从 env 覆盖)
- `alembic/env.py` — 关键配置
  - 自动 `import app.models` 让所有模型注册
  - `target_metadata = Base.metadata`
  - 从 `settings.database_url_sync` 读 URL
  - `compare_type=True` + `compare_server_default=True` 自动检测 schema 变化

## 当前 Migrations

| Revision | Description | Date |
|----------|-------------|------|
| `d263a44e8ad2` | initial schema (4 tables + indexes) | 2026-07-21 |

## Schema 概览

- `users` (UUID PK) + 5 enum (subscription_tier, oauth_provider)
- `evaluations` (UUID PK) + 4 enum (difficulty) + 5 维分数字段
- `curriculum_progress` (BIGINT PK) + 8 enum (block_type) + SM-2 字段
- `sight_reading_sessions` (UUID PK) + 3 enum (difficulty/mode/input)
- 所有外键 ON DELETE CASCADE
- 所有时间戳 `timestamp with time zone`

## 跨环境执行

### 本地开发 (SQLite)
```bash
DATABASE_URL_SYNC="sqlite:///./dev.db" alembic upgrade head
```

### 测试 (临时 SQLite)
```bash
DATABASE_URL_SYNC="sqlite:///:memory:" alembic upgrade head
```

### 生产 (远程 PG)
```bash
# SSH 隧道方式
ssh -L 15432:127.0.0.1:5432 ubuntu@server
DATABASE_URL_SYNC="postgresql://copiano:XXX@127.0.0.1:15432/copiano" \
  alembic upgrade head
```

或直接在服务器上跑:
```bash
ssh ubuntu@server
cd /opt/copiano/api
DATABASE_URL_SYNC="postgresql://copiano:XXX@127.0.0.1:5432/copiano" \
  alembic upgrade head
```

## 注意事项

- **生产前必测** — migration 在 dev/staging 跑通再上 prod
- **保留 downgrade** — 每个 migration 必须能回滚(autogenerate 不保证,人工 review)
- **数据迁移** — schema 变更(ALTER TABLE)和数据迁移(INSERT/UPDATE)分多个文件
- **不删旧 migration** — 即使有 bug,新建修复 migration,不要修改历史
- **CI 跑迁移** — pytest 应该跑一遍 upgrade head + downgrade base 验证

## 排错

```bash
# 看详细 SQL
alembic upgrade head --sql

# 强制重置(危险,会清数据)
alembic stamp head  # 把当前 DB 标记为 head,不实际跑 migration
```
