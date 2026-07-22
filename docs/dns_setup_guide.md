# CoPiano 域名 + SSL 配置操作指南

> 目标:把 5 个子域名解析到腾讯云 Lighthouse `124.156.184.160`,申请 Let's Encrypt SSL。
> 控制台: https://console.cloud.tencent.com/cns (云解析 DNS)
> 官方文档: https://cloud.tencent.com/document/product/302/3446

---

## 总览:6 个子域名一次性配齐

| 子域名 | 用途 | 解析目标 |
|---|---|---|
| `copiano.com` | 营销站 apex | `124.156.184.160` |
| `www.copiano.com` | 营销站 www | `124.156.184.160` |
| `app.copiano.com` | Web App | `124.156.184.160` |
| `api.copiano.com` | FastAPI 后端 | `124.156.184.160` |
| `docs.copiano.com` | API 文档 | `124.156.184.160` |
| `admin.copiano.com` | 管理员面板(后续) | `124.156.184.160` |

---

## 第一步:登录云解析 DNS 控制台

1. 浏览器打开 **https://console.cloud.tencent.com/cns**
2. 用你的腾讯云账号登录(可能需要扫码或手机验证)
3. 左侧菜单 → **权威解析**

---

## 第二步:确认 copiano.com 已加入云解析

**情况 A — 域名在腾讯云注册** (例如你从腾讯云买了 copiano.com)
- 域名会自动出现在列表里,**跳过此步**

**情况 B — 域名在别的注册商** (GoDaddy / Namecheap / 阿里云 等)
- 点击右上角 **「添加域名」**
- 输入: `copiano.com`
- 标签: 选填(例如 `prod`)
- 点击 **「下一步」**
- 页面会提示你"需要在注册商修改 DNS 服务器",**记录那 2 个 NS 记录**,去你的域名注册商后台把 DNS 服务器改为云解析的地址
- 注册商 DNS 生效需要 **0-48 小时**

**验证**:回到 `https://console.cloud.tencent.com/cns`,如果列表里看到 `copiano.com` 状态正常(没有"未使用云解析 DNS 地址"的红色提示),就 OK。

---

## 第三步:添加 6 条 A 记录(核心操作)

1. 在域名列表点击 **「copiano.com」** 进入"记录管理"页
2. 点击 **「添加记录」** 按钮(或 "新手快速解析" 引导)
3. **重复 6 次**,每次填:

| 序号 | 主机记录 | 记录类型 | 记录值 | TTL | 备注 |
|---|---|---|---|---|---|
| 1 | `@` | A | `124.156.184.160` | 600 | apex 根域 |
| 2 | `www` | A | `124.156.184.160` | 600 | www |
| 3 | `app` | A | `124.156.184.160` | 600 | Web App |
| 4 | `api` | A | `124.156.184.160` | 600 | FastAPI 后端 |
| 5 | `docs` | A | `124.156.184.160` | 600 | API 文档 |
| 6 | `admin` | A | `124.156.184.160` | 600 | 管理员面板 |

**字段说明**:
- **主机记录**:`@` 代表 `copiano.com` 本身,`www` 代表 `www.copiano.com`,其他子域名直接写名字
- **记录类型**:选 `A` (IPv4)
- **记录值**:你的服务器公网 IP `124.156.184.160`
- **TTL**:填 `600` (10 分钟,改动生效快;生产环境可以填 3600)
- **其他**:权重/线路默认即可

每次填完点 **「保存」**。

4. 添加完应该看到 6 条记录,都指向 `124.156.184.160`

---

## 第四步:验证 DNS 解析生效(本地)

DNS 全球生效需要 **0-10 分钟**(云解析通常很快)。

**方法 1:命令行**
```bash
# macOS / Linux
dig copiano.com +short
dig www.copiano.com +short
dig app.copiano.com +short
dig api.copiano.com +short

# 应该都返回: 124.156.184.160
```

**方法 2:在线工具**
- https://www.whatsmydns.net/ — 输入域名,选 A 记录
- 全球节点检查,绿色越多越好

**方法 3:Windows**
```cmd
nslookup copiano.com
```

---

## 第五步:申请 Let's Encrypt SSL 证书(服务器端)

**前置**:DNS 已生效(上一步 dig 能看到 `124.156.184.160`)。

**SSH 上服务器** (用你的密钥):
```bash
ssh -i ~/Downloads/123.pem ubuntu@124.156.184.160
```

### 5.1 安装 certbot
```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

### 5.2 申请证书(推荐方式:standalone)

**注意**:certbot standalone 需要占用 80 端口,先确保 80 端口没被占。
```bash
# 先停 nginx(如果之前跑过我们 install-server.sh)
sudo systemctl stop nginx 2>/dev/null || true
sudo systemctl stop copiano-web 2>/dev/null || true

# 一键申请 6 个域名的证书
sudo certbot certonly --standalone \
  -d copiano.com \
  -d www.copiano.com \
  -d app.copiano.com \
  -d api.copiano.com \
  -d docs.copiano.com \
  -d admin.copiano.com \
  --email hi@copiano.com \
  --agree-tos \
  --no-eff-email

# 输出类似:
# Successfully received certificate.
# Certificate is saved at: /etc/letsencrypt/live/copiano.com/fullchain.pem
# Key is saved at:         /etc/letsencrypt/live/copiano.com/privkey.pem
```

**如果 80 端口已被占**:
```bash
# 先看谁在占
sudo ss -tlnp | grep :80

# 找到进程,kill 或改端口
```

### 5.3 验证证书
```bash
sudo ls -la /etc/letsencrypt/live/copiano.com/
# 应该看到: cert.pem  chain.pem  fullchain.pem  privkey.pem  README

# 看有效期
sudo certbot certificates
```

### 5.4 测试自动续期
```bash
sudo certbot renew --dry-run
# 输出: Congratulations, all simulated renewals succeeded
```

certbot 会自动加 cron job(在 `/etc/cron.d/certbot`),证书 60 天前自动续。

---

## 第六步:配置 Nginx 使用证书

我之前已经写好了 Nginx 配置,现在要:
1. 启用站点
2. 验证配置
3. 重载 nginx

```bash
# 上传我们准备好的配置
sudo cp /opt/copiano/web/deploy/nginx.copiano.com.conf /etc/nginx/sites-available/copiano.com
sudo ln -sf /etc/nginx/sites-available/copiano.com /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t
# 应该输出: nginx: configuration file /etc/nginx/nginx.conf test is successful

# 重载
sudo systemctl reload nginx
```

---

## 第七步:部署 + 验证

```bash
# 启动后端 (如果还没)
cd /opt/copiano/postgres && docker compose up -d

# 部署 Web 端
cd /opt/copiano/web
docker compose -f deploy/docker-compose.yml up -d --build

# 验证 HTTPS
curl -I https://copiano.com/api/health
# 应该返回 200

# 测试所有子域
for d in copiano.com www.copiano.com app.copiano.com api.copiano.com docs.copiano.com; do
  echo "=== $d ==="
  curl -s -o /dev/null -w "HTTP %{http_code} (TLS: %{ssl_verify_result})\n" https://$d/api/health
done
```

---

## 故障排查

| 症状 | 排查 |
|---|---|
| dig 没返回 IP | DNS 没生效,等 10 分钟;或检查 NS 是否指向云解析 |
| certbot 报 `Timeout` | 80 端口被防火墙挡;`sudo ufw allow 80/tcp` |
| certbot 报 `Unauthorized` | DNS 没解析到本机 IP,先 dig 验证 |
| curl 返回 502 | 后端没跑,`docker ps` 看 copiano-postgres / web 状态 |
| HTTPS 报 NET::ERR_CERT_AUTHORITY_INVALID | 证书链不完整,在 nginx 里加 `ssl_trusted_certificate` |
| 证书 30 天后过期 | 检查 cron job:`cat /etc/cron.d/certbot` |

---

## 完成后的操作

- [ ] 我会跑 `cd web && ./deploy.sh` 部署前端
- [ ] 我会跑 `docker compose up -d` 部署后端
- [ ] 我会跑 `curl https://copiano.com/api/health` 验证 200
- [ ] 我会跑 `certbot renew --dry-run` 验证自动续期

DNS 配好后,告诉我 "DNS 配好了",我就接着干。
