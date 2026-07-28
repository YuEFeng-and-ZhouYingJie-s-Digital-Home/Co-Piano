# CoPiano v4.0 部署前置 — 细致操作指南

> 目标:从 GitHub admin 全配齐到 https://yefzyj.top 全部 5 子域上线,共 7 步,约 60 分钟。
> 服务器: 腾讯云 Lighthouse `ubuntu@124.156.184.160` (Ubuntu 22.04.5)
> 域名: `yefzyj.top` (DNSPod 管理)
> 仓库: https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano

---

## Step 0: 撤销旧 token (5 分钟) ⚠️ **必做**

你之前 paste 的 `ghp_FOokfVgz…` 已经在 chat history / shell history 出现多次,必须立即撤销。

### 0.1 撤销
- 打开 https://github.com/settings/tokens
- 找到你近期生成的 GitHub PAT(以 `ghp_` 开头)
- 点击右侧 **Delete** 按钮
- 确认删除

### 0.2 生成新 token
- 仍然在 https://github.com/settings/tokens
- 点击 **Generate new token** → **Fine-grained token** (推荐,scope 更小)
  - Token name: `CoPiano-deploy-2026Q3`
  - Expiration: **30 days** (强制,过期需续)
  - Resource owner: `YuEFeng-and-ZhouYingJie-s-Digital-Home`
  - Repository access: **Only select repositories** → `Co-Piano`
  - Permissions:
    - Repository permissions:
      - **Contents**: Read and write (推 push 必需)
      - **Pull requests**: Read and write (开 PR / approve)
      - **Actions**: Read and write (workflow dispatch)
      - **Metadata**: Read-only (auto)
- 生成后**只显示一次**,立即复制

### 0.3 用 1Password CLI 存
```bash
# 假设你已经在 1Password Desktop 登录
op signin

# 存到 Private vault
op create item login \
  --title "CoPiano GitHub PAT" \
  --vault Private \
  --url "https://github.com" \
  --username "kzhou176-dot" \
  --value "$NEW_TOKEN"

# 后续使用(不在 shell 留痕)
GITHUB_TOKEN=$(op read "op://Private/CoPiano GitHub PAT/value")
```

**我后续用这个方式调 API,不再 paste 明文。**

---

## Step 1: 配 GitHub Secrets (10 分钟)

**位置**: https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/settings/secrets/actions

### 1.1 必需 secrets(已配 4 个,需补 5 个)

| Secret 名 | 值 | 用途 |
|---|---|---|
| `BACKEND_DATABASE_URL` | `postgresql+asyncpg://copiano:GHMFjIjUQCxDC4017QZpqorvYjjWDfHc@127.0.0.1:5432/copiano` | ✅ 已配 (CI) |
| `BACKEND_REDIS_URL` | `redis://:sNbnGWJwnx2hLtaeGd7CcEQ3nMnmbzHr@127.0.0.1:6379/0` | ✅ 已配 (CI) |
| `BACKEND_JWT_SECRET` | (CI 用的临时值) | ✅ 已配 (CI) |
| `NEXTAUTH_SECRET` | (CI 用的临时值) | ✅ 已配 (CI) |
| **`DEPLOY_SSH_KEY`** | **整段 PEM 私钥文本**(含 BEGIN/END 行) | ❌ **待配** |
| **`DEPLOY_HOST`** | `ubuntu@124.156.184.160` | ❌ **待配** |
| **`DEPLOY_PORT`** | `22` | ❌ **待配** |
| **`DEPLOY_USER`** | `ubuntu` | ❌ **待配** |
| **`NEXT_PUBLIC_API_BASE_URL`** | `https://api.yefzyj.top` | ❌ **待配** |
| **`NEXT_PUBLIC_MARKETING_URL`** | `https://yefzyj.top` | ❌ **待配** |
| **`NEXT_PUBLIC_WS_BASE_URL`** | `wss://api.yefzyj.top` | ❌ **待配** |
| **`NEXT_PUBLIC_APP_URL`** | `https://app.yefzyj.top` | ❌ **待配** |

### 1.2 SSH 私钥获取

```bash
# 本地查看
cat ~/Downloads/123.pem

# 全文复制(包括 BEGIN/END 行),粘到 DEPLOY_SSH_KEY 的值里
# 整段是一行,GitHub UI 会自动处理多行
```

### 1.3 我帮你用 op 批量设(替代手动)

**前提**:你已经按 Step 0.3 把 token 存到 1Password。

```bash
GITHUB_TOKEN=$(op read "op://Private/CoPiano GitHub PAT/value")
REPO="YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano"
SSH_KEY=$(cat ~/Downloads/123.pem)

# 用 /tmp/set_github_secrets.py(已有)
cat > /tmp/deploy_secrets.json <<EOF
{
  "DEPLOY_SSH_KEY": "$SSH_KEY",
  "DEPLOY_HOST": "ubuntu@124.156.184.160",
  "DEPLOY_PORT": "22",
  "DEPLOY_USER": "ubuntu",
  "NEXT_PUBLIC_API_BASE_URL": "https://api.yefzyj.top",
  "NEXT_PUBLIC_MARKETING_URL": "https://yefzyj.top",
  "NEXT_PUBLIC_WS_BASE_URL": "wss://api.yefzyj.top",
  "NEXT_PUBLIC_APP_URL": "https://app.yefzyj.top"
}
EOF

python3 /tmp/set_github_secrets.py "$GITHUB_TOKEN" /tmp/deploy_secrets.json
```

**告诉我 token 已生成 + 1Password 存好,我就跑这段。**

---

## Step 2: 配 DNSPod 6 条 A 记录 (5 分钟)

**位置**: https://console.dnspod.cn (或 https://console.cloud.tencent.com/cns)

### 2.1 登录

- 用你买 `yefzyj.top` 的腾讯云账号登 DNSPod
- 点 `yefzyj.top` → 「记录管理」

### 2.2 修改 / 添加 6 条 A 记录

| 操作 | 主机记录 | 当前值(可能是) | 改成 | TTL |
|---|---|---|---|---|
| 改 | `@` | `198.18.0.16` | `124.156.184.160` | 600 |
| 改 | `www` | `198.18.0.17` | `124.156.184.160` | 600 |
| 加 | `app` | (无) | `124.156.184.160` | 600 |
| 加 | `api` | (无) | `124.156.184.160` | 600 |
| 加 | `docs` | (无) | `124.156.184.160` | 600 |
| 加 | `admin` | (无) | `124.156.184.160` | 600 |

**记录类型全部 A**。修改完保存。

### 2.3 验证 DNS 生效(本机)

```bash
# macOS / Linux
dig yefzyj.top +short          # 应:124.156.184.160
dig www.yefzyj.top +short
dig app.yefzyj.top +short
dig api.yefzyj.top +short
dig docs.yefzyj.top +short
dig admin.yefzyj.top +short

# 6 个全部返回 124.156.184.160 → 配好
# 有任一返回 198.18.0.x → 等 1-5 分钟重试
```

### 2.4 NS 验证(防万一 NS 被改了)

```bash
dig NS yefzyj.top +short
# 应:burnell.dnspod.net.  barton.dnspod.net.
# 不是 → 你域名在别的注册商,需要去那边改 NS
```

**全部 6 条返回 124.156.184.160 后告诉我,接着跑 Step 3。**

---

## Step 3: 服务器基础配置 (5 分钟,自动化)

服务器 `ubuntu@124.156.184.160` 上跑 `install-server.sh`。

### 3.1 你手动跑 SSH 命令(我没法绕过你授权)

```bash
# 在你 macOS 终端
ssh -i ~/Downloads/123.pem ubuntu@124.156.184.160
```

### 3.2 服务器端跑

```bash
# 一次性安装:Nginx + certbot + ufw + 创建 /opt/copiano/ 目录
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo mkdir -p /opt/copiano/web /opt/copiano/backend
sudo chown -R ubuntu:ubuntu /opt/copiano

# 验证 nginx 配置语法
sudo nginx -t
```

### 3.3 我(或你)上传 deploy 套件 + 启用站点

```bash
# 在你 macOS 终端(另开一个 tab)
GIT_TOKEN=$(op read "op://Private/CoPiano GitHub PAT/value")
SERVER="ubuntu@124.156.184.160"

# 1. 上传 Nginx 配置
scp -i ~/Downloads/123.pem web/deploy/nginx.yefzyj.top.conf \
  ubuntu@$SERVER:/tmp/nginx.yefzyj.top.conf
ssh -i ~/Downloads/123.pem ubuntu@$SERVER \
  'sudo mv /tmp/nginx.yefzyj.top.conf /etc/nginx/sites-available/yefzyj.top && \
   sudo ln -sf /etc/nginx/sites-available/yefzyj.top /etc/nginx/sites-enabled/ && \
   sudo rm -f /etc/nginx/sites-enabled/default && \
   sudo nginx -t'

# ⚠️ nginx -t 会报证书文件不存在的错误 — 这是正常的,Step 4 签证书后再 reload
```

**如果你 nginx -t 报证书错误,正常,继续 Step 4。**

---

## Step 4: 申请 Let's Encrypt SSL 证书 (3 分钟,自动化)

### 4.1 停 nginx(释放 80 端口)

```bash
# macOS 终端
ssh -i ~/Downloads/123.pem ubuntu@124.156.184.160 \
  'sudo systemctl stop nginx'
```

### 4.2 申请 6 域名多域证书(我帮你跑)

```bash
# macOS 终端
ssh -i ~/Downloads/123.pem ubuntu@124.156.184.160 << 'REMOTE'
sudo certbot certonly --standalone \
  -d yefzyj.top \
  -d www.yefzyj.top \
  -d app.yefzyj.top \
  -d api.yefzyj.top \
  -d docs.yefzyj.top \
  -d admin.yefzyj.top \
  --email hi@yefzyj.top \
  --agree-tos \
  --no-eff-email

# 验证
sudo ls -la /etc/letsencrypt/live/yefzyj.top/
sudo certbot certificates
sudo certbot renew --dry-run
REMOTE
```

### 4.3 启动 nginx

```bash
ssh -i ~/Downloads/123.pem ubuntu@124.156.184.160 \
  'sudo systemctl start nginx && sudo nginx -t && sudo systemctl reload nginx'
```

### 4.4 验证 HTTPS

```bash
# 测一个域名
curl -I https://yefzyj.top/
# 期望:HTTP/2 200(或 502,因为 web 还没跑)

# 6 个全测
for d in yefzyj.top www.yefzyj.top app.yefzyj.top api.yefzyj.top docs.yefzyj.top admin.yefzyj.top; do
  echo "=== $d ==="
  curl -s -o /dev/null -w "  HTTP %{http_code}  TLS %{ssl_verify_result}\n" https://$d/ --max-time 5
done
```

**全部 200/502 + TLS 0 → SSL OK。**

---

## Step 5: 部署后端 (10 分钟)

后端部署到服务器 `/opt/copiano/backend/`。

### 5.1 上传代码 + 启动

我帮你写一个 deploy 脚本。或者你手动:

```bash
# macOS 终端 — 我跑
ssh -i ~/Downloads/123.pem ubuntu@124.156.184.160 << 'REMOTE'
# 创建 venv + 装依赖
cd /opt/copiano/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 跑 alembic 迁移
alembic upgrade head

# 用 nohup 启动(临时,后续用 systemd)
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > /tmp/copiano-backend.log 2>&1 &
echo "Backend started: PID $!"

# 健康检查
sleep 3
curl -s -o /dev/null -w "Backend: HTTP %{http_code}\n" http://127.0.0.1:8000/api/v1/users/me
REMOTE
```

### 5.2 配 systemd(推荐)

我帮你写 `/etc/systemd/system/copiano-backend.service`:

```ini
[Unit]
Description=CoPiano FastAPI Backend
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/copiano/backend
Environment="PATH=/opt/copiano/backend/venv/bin"
ExecStart=/opt/copiano/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=append:/var/log/copiano-backend.log
StandardError=append:/var/log/copiano-backend.log

[Install]
WantedBy=multi-user.target
```

启用:
```bash
sudo systemctl daemon-reload
sudo systemctl enable copiano-backend
sudo systemctl start copiano-backend
sudo systemctl status copiano-backend
```

**Step 5 完成后,`curl https://api.yefzyj.top/docs` 应该看到 Swagger UI。**

---

## Step 6: 部署 Web 端 (10 分钟)

### 6.1 用 GitHub Actions Deploy workflow(自动)

GitHub Secrets 都配齐后,触发 deploy:

**方式 A — 推 main 自动触发**

```bash
# 改任意 web/ 文件
echo "# last deployed: $(date)" >> web/deploy/.deploy_marker
git add web/deploy/.deploy_marker
git commit -m "chore: trigger deploy"
git push origin main
```

**方式 B — 手动 workflow_dispatch**

- 打开 https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/actions/workflows/deploy.yml
- 点击 **Run workflow** → 选 environment (production) → **Run**
- 等 5-10 分钟看 logs

### 6.2 Deploy workflow 跑完后,验证

```bash
# macOS 终端
for d in yefzyj.top www.yefzyj.top app.yefzyj.top; do
  echo "=== $d ==="
  curl -s -o /dev/null -w "  HTTP %{http_code}  TLS %{ssl_verify_result}\n" https://$d/api/health --max-time 5
done

# 看页面
open https://yefzyj.top
open https://app.yefzyj.top/login
```

**全部 200 + 页面正常 → 部署成功!**

---

## Step 7: 配监控 + 告警 (10 分钟)

### 7.1 健康检查 cron

```bash
# 在服务器
cat /opt/copiano/web/deploy/healthcheck.sh | sudo tee /usr/local/bin/copiano-healthcheck.sh
sudo chmod +x /usr/local/bin/copiano-healthcheck.sh

# 加 cron job:每 5 分钟
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/copiano-healthcheck.sh >> /var/log/copiano-health.log 2>&1") | crontab -

# 验证
sudo crontab -l | grep copiano
```

### 7.2 (可选) Slack/飞书告警

`/opt/copiano/web/deploy/healthcheck.sh` 已支持 `SLACK_WEBHOOK` 环境变量,设上即可:
```bash
sudo mkdir -p /etc/copiano
echo 'SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL' | sudo tee /etc/copiano/healthcheck.env
# 编辑 /usr/local/bin/copiano-healthcheck.sh,加 . /etc/copiano/healthcheck.env
```

### 7.3 GitHub Actions 跑通

打开 https://github.com/YuEFeng-and-ZhouYingJie-s-Digital-Home/Co-Piano/actions
- 应该有 CI / CodeQL / Deploy 三个 workflow
- 第一次 push 后会自动跑
- 检查 4 个 secret 是否都生效(BACKEND_DATABASE_URL / _REDIS_URL / _JWT_SECRET / NEXTAUTH_SECRET)

---

## 🎉 完成!CoPiano v4.0 上线

完成后:
- 🌐 https://yefzyj.top 营销主页
- 🌐 https://app.yefzyj.top Web App
- 🌐 https://api.yefzyj.top FastAPI
- 🌐 https://docs.yefzyj.top Swagger UI
- 🌐 https://admin.yefzyj.top 管理员面板
- 🔄 自动 deploy: 推 main → CI 跑通 → Deploy 自动
- 🔒 SSL 自动续期: certbot renew 60 天前自动

---

## 📋 时间线总览

| Step | 内容 | 估计时间 | 你的动作 |
|---|---|---|---|
| 0 | 撤销旧 token + 生成新 | 5 min | 手动 |
| 1 | 配 GitHub Secrets (5 个) | 10 min | 我跑(op 读) |
| 2 | DNSPod 6 条 A 记录 | 5 min | 手动 |
| 3 | 服务器基础配置 (apt + nginx) | 5 min | 我跑(SSH) |
| 4 | Let's Encrypt SSL 证书 | 3 min | 我跑(SSH) |
| 5 | 部署后端 (uvicorn) | 10 min | 我跑(SSH) |
| 6 | 部署 Web (Deploy workflow) | 10 min | 我跑(GitHub) |
| 7 | 监控 + 告警 | 10 min | 我跑(SSH) |
| **总计** | | **~58 min** | |

---

## 🆘 常见问题

### Q1: certbot 报 `DNS problem: NXDOMAIN`
**原因**: DNS 还没生效。`dig yefzyj.top +short`,等 5 分钟重试。

### Q2: nginx -t 报 `cannot load certificate`
**正常**: Step 4 之前没证书。**继续 Step 4**,别停。

### Q3: 后端 502 / 无法启动
```bash
# 看日志
ssh ubuntu@124.156.184.160 'tail -50 /var/log/copiano-backend.log'
# 或 journalctl
ssh ubuntu@124.156.184.160 'sudo journalctl -u copiano-backend -n 50'
```

### Q4: Deploy workflow 失败
看 GitHub Actions 页面 logs,常见原因:
- Secrets 没配齐 → Step 1 检查
- SSH key 格式错 → 重新 cat ~/Downloads/123.pem 完整复制
- 服务器端口被挡 → ufw 状态

### Q5: DNS 已配但 certbot 失败
**等 5-10 分钟**,DNS 全球生效需要时间。

---

## 🎁 顺便:1Password 存 SSH 私钥

```bash
# 把 SSH 私钥也存到 1Password(不要存任何 git 里)
op create item ssh_key \
  --title "CoPiano server SSH" \
  --vault Private \
  --private-key "$(cat ~/Downloads/123.pem)" \
  --hostname "124.156.184.160" \
  --username "ubuntu"
```

这样你所有 CoPiano 相关凭据都集中在 1Password Private vault。
