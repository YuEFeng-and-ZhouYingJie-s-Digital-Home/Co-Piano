# CoPiano 域名 + SSL 配置操作指南 (yefzyj.top)

> 目标:把 5 个 `yefzyj.top` 子域名解析到腾讯云 Lighthouse `124.156.184.160`,申请 Let's Encrypt SSL。
> DNS 服务: DNSPod (腾讯云 `burnell.dnspod.net` / `barton.dnspod.net`)
> 管理入口: https://console.dnspod.cn 或 https://console.cloud.tencent.com/cns

---

## 总览:6 个子域名

| 子域名 | 用途 | 解析目标 |
|---|---|---|
| `yefzyj.top` | 营销站 apex | `124.156.184.160` |
| `www.yefzyj.top` | 营销站 www | `124.156.184.160` |
| `app.yefzyj.top` | Web App | `124.156.184.160` |
| `api.yefzyj.top` | FastAPI 后端 | `124.156.184.160` |
| `docs.yefzyj.top` | API 文档 | `124.156.184.160` |
| `admin.yefzyj.top` | 管理员面板(后续) | `124.156.184.160` |

---

## 第一步:登录 DNSPod

**两个入口都可以(同一套数据)**:
- **DNSPod 直控**: https://console.dnspod.cn (推荐,DNS 操作更直接)
- **腾讯云控制台**: https://console.cloud.tencent.com/cns → 左侧「权威解析」

用你注册 `yefzyj.top` 的腾讯云账号登录。域名应该已经在列表里(因为 NS 服务器是 dnspod.net)。

---

## 第二步:修改/添加 6 条 A 记录

点 `yefzyj.top` 进入 **「记录管理」** 页面。

**⚠️ 注意:dig 看到当前 `yefzyj.top` 解析到 `198.18.0.16`,这是 RFC 6890 基准测试假地址,一定要先改掉。**

### 2.1 修改已有记录(如果有)
- 找到主机记录为 `@` 的 A 记录(指向 198.18.0.x 的)→ 点编辑 → 把值改为 `124.156.184.160` → 保存
- 找到主机记录为 `www` 的 → 同上

### 2.2 添加缺失的子域名
点 **「添加记录」** 按钮,重复以下 6 次(每条记录点一次保存):

| 主机记录 | 记录类型 | 记录值 | TTL |
|---|---|---|---|
| `@` | A | `124.156.184.160` | 600 |
| `www` | A | `124.156.184.160` | 600 |
| `app` | A | `124.156.184.160` | 600 |
| `api` | A | `124.156.184.160` | 600 |
| `docs` | A | `124.156.184.160` | 600 |
| `admin` | A | `124.156.184.160` | 600 |

**字段说明**:
- **主机记录**:`@` = `yefzyj.top` 本身,其他填子域名前缀
- **记录类型**:`A` (IPv4)
- **记录值**: `124.156.184.160`
- **TTL**:`600` 秒(10 分钟,改动生效快;生产可改 3600)
- **线路类型**:默认(如果有"搜索引擎"或"国外"选项,选"默认"即可)

最终应该看到 6 条 A 记录,值都是 `124.156.184.160`。

---

## 第三步:验证 DNS 解析生效(本地)

DNS 生效需要 0-10 分钟(DNSPod 通常 1-5 分钟):

**macOS / Linux**:
```bash
dig yefzyj.top +short
dig www.yefzyj.top +short
dig app.yefzyj.top +short
dig api.yefzyj.top +short
dig docs.yefzyj.top +short
dig admin.yefzyj.top +short
```

**应该全部返回**: `124.156.184.160`

**Windows**:
```cmd
nslookup yefzyj.top
```

**在线工具**: https://www.whatsmydns.net/ → 输入 `yefzyj.top` 选 A → 全球节点检查绿色越多越好

---

## 第四步:SSH 上服务器申请 SSL

DNS 验证后:
```bash
ssh -i ~/Downloads/123.pem ubuntu@124.156.184.160
```

### 4.1 安装 certbot
```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

### 4.2 申请证书(standalone 模式)
**先停 nginx**释放 80 端口:
```bash
sudo systemctl stop nginx
```

**申请 6 个域名的多域证书**:
```bash
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
```

看到 `Successfully received certificate` 就 OK。

### 4.3 验证证书
```bash
sudo ls -la /etc/letsencrypt/live/yefzyj.top/
# 应看到 cert.pem  chain.pem  fullchain.pem  privkey.pem  README

sudo certbot certificates
# 显示: Certificate Name: yefzyj.top, Domains: 6, Expiry Date
```

### 4.4 测试自动续期
```bash
sudo certbot renew --dry-run
```

---

## 第五步:配置 Nginx 使用证书

**复制我们准备好的配置**:
```bash
sudo cp /opt/copiano/web/deploy/nginx.yefzyj.top.conf /etc/nginx/sites-available/yefzyj.top
sudo ln -sf /etc/nginx/sites-available/yefzyj.top /etc/nginx/sites-enabled/

# 测试
sudo nginx -t
# 输出: nginx: configuration file ... test is successful

# 重载
sudo systemctl reload nginx
```

---

## 第六步:部署 + 验证

```bash
# 部署 web 前端
cd /opt/copiano/web
docker compose -f deploy/docker-compose.yml up -d --build

# 部署后端(如果还没跑)
cd /opt/copiano/postgres
docker compose up -d

# 验证 6 个子域名
for d in yefzyj.top www.yefzyj.top app.yefzyj.top api.yefzyj.top docs.yefzyj.top admin.yefzyj.top; do
  echo "=== $d ==="
  curl -s -o /dev/null -w "HTTP %{http_code} (TLS: %{ssl_verify_result})\n" https://$d/api/health
done
```

应该全部 `200` + `TLS 0`(证书有效)。

---

## 故障排查

| 症状 | 排查 |
|---|---|
| dig 返回 198.18.0.x | DNSPod A 记录没改,或缓存未刷新(等 5 分钟) |
| certbot 报 `NXDOMAIN` | DNS 没生效,等几分钟再试 |
| certbot 报 `Timeout` | 80 端口被挡,`sudo ufw allow 80/tcp` |
| certbot 报 `Unauthorized` | 域名在 DNSPod 但 NS 没指 dnspod.net,检查 `dig NS yefzyj.top` |
| HTTPS 浏览器报证书无效 | 证书链不全,在 nginx 加 `ssl_trusted_certificate` |
| curl 返回 502 | 后端 docker 没跑,`docker ps` 查 copiano-web / copiano-postgres |

---

## 我准备好就等的

DNS 解析全部指向 `124.156.184.160` 后,告诉我"6 个全 124 了",我立刻:
1. SSH 上服务器跑 certbot(nginx 还在停着)
2. 配 Nginx 用证书
3. 部署 web + 后端
4. 验证 6 个子域全部 200
