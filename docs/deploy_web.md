# CoPiano v4 营销站部署 — 总览

> 目标域名:`https://copiano.com`(apex) + 5 子域名
> 部署时间:**待用户 DNS 解析生效后**

## 5 子域名架构

| 子域名 | 用途 | 状态 |
|---|---|---|
| `copiano.com` | 营销主页 (Hero + RCT + Pricing) | ✅ Cycle 41-47 完成 |
| `app.copiano.com` | Web App (登录/课程/录音) | [PENDING] W6 |
| `api.copiano.com` | FastAPI 后端 (25 端点 + 1 WS) | ✅ Cycle 23-40 |
| `admin.copiano.com` | 管理员面板 (Teacher) | [PENDING] 后续 |
| `docs.copiano.com` | API 文档 (Swagger UI) | [PENDING] 后续 |

## 当前状态 (W5 营销站收官)

- ✅ A5.1 Next.js 14 init
- ✅ A5.2 Tailwind + shadcn/ui
- ✅ A5.3 营销主页 (Hero + 5 维 + RCT Recharts)
- ✅ A5.4 /pricing 订阅页 (5 档)
- ✅ A5.5 /about 团队+论文+时间线
- ✅ A5.6 SEO 全套 (sitemap/robots/OG/JSON-LD/PWA)
- ✅ A5.7 部署套件 (Nginx + Docker + 脚本 + 文档)

**W5 7/7 完成 🎉** — 等待用户 DNS 生效 + certbot 证书后即可一键部署。

## 用户操作清单 (部署前)

| # | 操作 | 命令 | 阻塞项 |
|---|---|---|---|
| 1 | 腾讯云 DNS 配 A 记录 | `copiano.com → 124.156.184.160` | A1.3 |
| 2 | 服务端基础配置 | `bash install-server.sh` (一键) | - |
| 3 | 申请 SSL 证书 | `certbot --nginx -d copiano.com -d www.copiano.com` | 依赖 #1 |
| 4 | 上传 web 源码 + 部署 | `./deploy.sh` (一键) | 依赖 #2 #3 |

## 部署后验证

```bash
curl -i https://copiano.com/api/health          # 200
curl -I https://copiano.com/                     # 200
curl -I https://copiano.com/pricing              # 200
curl -I https://copiano.com/about                # 200
curl -I https://copiano.com/sitemap.xml          # 200 application/xml
curl -I https://copiano.com/robots.txt           # 200 text/plain
curl -I https://copiano.com/opengraph-image      # 200 image/png
curl -I https://copiano.com/icon                 # 200 image/png
```

## 资源消耗预估

- Docker 容器:copiano-web ~150M RAM (Next.js standalone + node:20-alpine)
- 磁盘:~250M 镜像 + 源码
- 流量:营销站主要是静态,LLM 流式走 `api.copiano.com`

## 下一步 (W6 Web App)

W6 开始建 `app.copiano.com` 的 Web App 主体:NextAuth + /login + /signup + /app/* 受保护路由。
- A6.1 NextAuth.js 配置
- A6.2 /login + /signup
- A6.3 /app 路由组
- A6.4-6.9 课程/录音/反馈/进度/视奏/设置

预计 7-8 个 cycle 完成 W6。
