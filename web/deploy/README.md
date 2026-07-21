# CoPiano 营销站 — 部署指南

> 目标:把 `web/` 部署到 `https://copiano.com`

## 架构

```
Internet (用户)
  ↓ HTTPS:443
Nginx (反向代理 + SSL termination)
  ↓ HTTP:3000
Docker: copiano-web (Next.js 14 standalone)
  ↓ API call
Backend (api.copiano.com, FastAPI)
```

## 前置条件 (需用户操作)

| 任务 | 状态 | 备注 |
|---|---|---|
| A1.3 DNS 5 子域名 A 记录 | [BLOCKED] | 用户在腾讯云 DNS 配 `copiano.com` → `124.156.184.160` |
| A1.5 Let's Encrypt 证书 | [BLOCKED, 依赖 DNS] | `certbot --nginx -d copiano.com -d www.copiano.com` |
| 部署目录创建 | ✅ | 服务器已有 `/opt/copiano/` |
| Docker 已就绪 | ✅ | Docker 29.6.2 + Compose v5.3.1 |

## 部署步骤

### 1. 服务器端一次配置 (用户首次)

```bash
ssh -i ~/Downloads/123.pem ubuntu@124.156.184.160

# 创建部署目录
sudo mkdir -p /opt/copiano/web
sudo chown ubuntu:ubuntu /opt/copiano/web

# 安装 Nginx
sudo apt install -y nginx certbot python3-certbot-nginx

# 启用站点
sudo cp nginx.copiano.com.conf /etc/nginx/sites-available/copiano.com
sudo ln -s /etc/nginx/sites-available/copiano.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 申请 SSL 证书 (需要 DNS 已生效)
sudo certbot --nginx -d copiano.com -d www.copiano.com
```

### 2. 部署 Web 应用 (本地)

```bash
cd web/

# 第一次: 上传源码到服务器
./deploy/deploy.sh

# 后续: 仅传变更
./deploy/deploy.sh --no-build  # 假设已 build
```

### 3. 验证

```bash
# 健康检查
curl -i https://copiano.com/api/health

# 页面测试
curl -i https://copiano.com/ | head -5
curl -i https://copiano.com/pricing | head -5
curl -i https://copiano.com/about | head -5

# SEO 文件
curl -i https://copiano.com/sitemap.xml | head -10
curl -i https://copiano.com/robots.txt
curl -I https://copiano.com/opengraph-image  # 应返回 image/png
```

## Nginx 配置要点

- **HTTP→HTTPS 301**:除 ACME 验证路径外全部重定向
- **TLS 1.2/1.3**:Mozilla Intermediate 配置
- **HSTS**:max-age=63072000 (2 年)
- **OCSP Stapling**:减少 TLS 握手延迟
- **Gzip**:level 6,text/json/svg/xml
- **Next.js static 缓存**:`/_next/static/*` 1 年 immutable
- **超时 120s**:覆盖 LLM 流式响应
- **客户端 body 上限 10M**:MIDI 由后端接收,前端不会传大文件

## Docker 镜像

- 基础镜像:`node:20-alpine`
- 三段式:deps (npm ci) → builder (next build) → runner (standalone)
- non-root user (`nextjs:1001`)
- 仅暴露 `127.0.0.1:3000`,外网不可直连
- 健康检查:wget `/api/health` 每 30s
- 日志轮转:10M × 3 文件

## 故障排查

```bash
# 容器日志
docker logs --tail 100 copiano-web

# 进入容器
docker exec -it copiano-web sh

# 资源
docker stats copiano-web

# Nginx
sudo nginx -T | grep copiano
sudo tail -50 /var/log/nginx/copiano.com.error.log

# 证书续期
sudo certbot renew --dry-run
```

## CI/CD (后续 A8.2)

GitHub Actions 自动 build + 部署,密钥存 GitHub Secrets。
