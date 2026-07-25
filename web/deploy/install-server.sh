#!/bin/bash
# CoPiano Web 服务端一次配置 (yefzyj.top)
# ssh ubuntu@124.156.184.160 'bash -s' < install-server.sh
set -euo pipefail

log() { echo "[$(date +%H:%M:%S)] $*"; }

if [[ $EUID -ne 0 ]]; then
    SUDO="sudo"
else
    SUDO=""
fi

log "1. 创建部署目录..."
$SUDO mkdir -p /opt/copiano/web
$SUDO chown ubuntu:ubuntu /opt/copiano/web

log "2. 安装 Nginx + Certbot..."
$SUDO apt update -y
$SUDO apt install -y nginx certbot python3-certbot-nginx

log "3. 配置 UFW 开放 80/443..."
$SUDO ufw allow 80/tcp || true
$SUDO ufw allow 443/tcp || true

log "4. 启用站点 (待用户上传 nginx.conf)..."
$SUDO tee /etc/nginx/sites-available/yefzyj.top > /dev/null <<'NGINX_PLACEHOLDER'
# 等待用户上传 deploy/nginx.yefzyj.top.conf 后启用
# sudo cp /opt/copiano/web/deploy/nginx.yefzyj.top.conf /etc/nginx/sites-available/yefzyj.top
# sudo ln -sf /etc/nginx/sites-available/yefzyj.top /etc/nginx/sites-enabled/
NGINX_PLACEHOLDER

log "5. 默认站点禁用..."
$SUDO rm -f /etc/nginx/sites-enabled/default || true

log "6. 验证 Nginx 配置..."
$SUDO nginx -t

log "7. 重载 Nginx..."
$SUDO systemctl reload nginx || $SUDO systemctl start nginx

log "8. 创建日志轮转..."
$SUDO tee /etc/logrotate.d/copiano-web > /dev/null <<'LOGROTATE'
/var/log/nginx/yefzyj.top.*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 $(cat /var/run/nginx.pid)
    endscript
}
LOGROTATE

log ""
log "=========================================="
log "✅ 服务端基础配置完成"
log ""
log "下一步:"
log "  1. 在 DNSPod (dnspod.cn) 配 A 记录: yefzyj.top → 124.156.184.160"
log "  2. DNS 生效后,运行: sudo certbot certonly --standalone -d yefzyj.top -d www.yefzyj.top -d app.yefzyj.top -d api.yefzyj.top -d docs.yefzyj.top -d admin.yefzyj.top --email hi@yefzyj.top --agree-tos --no-eff-email"
log "  3. 上传 nginx 配置: sudo cp /opt/copiano/web/deploy/nginx.yefzyj.top.conf /etc/nginx/sites-available/yefzyj.top && sudo ln -sf /etc/nginx/sites-available/yefzyj.top /etc/nginx/sites-enabled/ && sudo nginx -t && sudo systemctl reload nginx"
log "  4. 本地执行: cd web && ./deploy/deploy.sh"
log "=========================================="
