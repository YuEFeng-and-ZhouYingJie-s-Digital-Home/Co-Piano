# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| v4.x    | ✅ Active          |
| v3.x    | ⚠️ Critical fixes only |
| < v3.0  | ❌ End of life     |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Email: **<hi@yefzyj.top>** with subject `[SECURITY] CoPiano <brief description>`.

We aim to:
- Acknowledge within **48 hours**
- Provide a fix or mitigation plan within **7 days** for high-severity issues
- Credit you in the security advisory (unless you prefer to remain anonymous)

## Scope

- Backend: FastAPI 鉴权 (bcrypt + JWT), SQL 注入 (SQLAlchemy ORM 防护), 文件上传 (MIME 校验)
- Web: NextAuth.js v5 session, CSP headers, HSTS, X-Frame-Options
- Storage: MinIO bucket ACL 隔离, presigned URL 过期 (1 小时)
- LLM: prompt injection 防护 (system prompt 隔离, 用户输入不直接进 system)

## Best Practices for Self-Hosting

- Change `JWT_SECRET` (32+ char random)
- Enable HTTPS (Let's Encrypt via certbot)
- Set `ENVIRONMENT=production` (关闭 debug 日志)
- Restrict CORS (`allow_origins` 不要用 `*`)
- 定期 `docker compose pull` 更新镜像
- 备份 PostgreSQL (`pg_dump` 每日 cron)
