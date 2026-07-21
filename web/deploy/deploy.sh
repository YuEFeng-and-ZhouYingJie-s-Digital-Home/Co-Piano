#!/bin/bash
# CoPiano 营销站 — 部署脚本
# 用法: ./deploy.sh [--no-build]
#
# 流程:
#   1. 本地 build Next.js standalone
#   2. scp 上传到服务器 /opt/copiano/web/
#   3. SSH 触发 docker compose up -d --build
#   4. 健康检查

set -euo pipefail

# --- 配置 ---
SERVER="ubuntu@124.156.184.160"
SERVER_PORT=22
SSH_KEY="${HOME}/Downloads/123.pem"
REMOTE_DIR="/opt/copiano/web"
LOCAL_BUILD_DIR="$(cd "$(dirname "$0")/.." && pwd)"

NO_BUILD=0
[[ "${1:-}" == "--no-build" ]] && NO_BUILD=1

log() { echo "[$(date +%H:%M:%S)] $*"; }
die() { log "ERROR: $*" >&2; exit 1; }

# --- 0. 前置检查 ---
[[ -f "$SSH_KEY" ]] || die "SSH key not found: $SSH_KEY (set SSH_KEY env var)"
chmod 600 "$SSH_KEY" 2>/dev/null || true

# --- 1. 本地 build ---
if [[ $NO_BUILD -eq 0 ]]; then
    log "Building Next.js standalone..."
    cd "$LOCAL_BUILD_DIR"
    npm ci --no-audit --no-fund || die "npm ci failed"
    npm run build || die "next build failed"
    log "Build OK"
fi

# --- 2. 上传 (rsync over ssh) ---
log "Syncing to ${SERVER}:${REMOTE_DIR} ..."
# rsync 排除 node_modules / .next/cache / .git
rsync -avz --delete \
    -e "ssh -i $SSH_KEY -p $SERVER_PORT -o StrictHostKeyChecking=no" \
    --exclude='node_modules' \
    --exclude='.next/cache' \
    --exclude='.git' \
    --exclude='.env.local' \
    --exclude='*.log' \
    "$LOCAL_BUILD_DIR/" \
    "${SERVER}:${REMOTE_DIR}/" \
    || die "rsync failed"

# --- 3. 远程重启 ---
log "Remote: docker compose build + up..."
ssh -i "$SSH_KEY" -p "$SERVER_PORT" -o StrictHostKeyChecking=no "$SERVER" <<'REMOTE'
cd /opt/copiano/web
docker compose -f deploy/docker-compose.yml build --no-cache
docker compose -f deploy/docker-compose.yml up -d
docker compose -f deploy/docker-compose.yml ps
REMOTE

# --- 4. 健康检查 ---
log "Health check..."
sleep 5
HEALTH=$(curl -s -o /dev/null -w '%{http_code}' https://copiano.com/api/health || echo "000")
if [[ "$HEALTH" == "200" ]]; then
    log "✅ Deploy success — https://copiano.com/api/health → 200"
else
    log "⚠️ Health check returned $HEALTH — check docker logs"
    ssh -i "$SSH_KEY" -p "$SERVER_PORT" -o StrictHostKeyChecking=no "$SERVER" \
        'docker logs --tail 50 copiano-web' || true
    exit 1
fi
