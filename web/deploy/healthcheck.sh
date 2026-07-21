#!/bin/bash
# CoPiano Web 健康检查 + 监控
# cron: */5 * * * * /opt/copiano/web/deploy/healthcheck.sh
# 用 UptimeRobot / 飞书机器人 / 邮件告警

set -euo pipefail

DOMAIN="${DOMAIN:-https://copiano.com}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
LOG=/var/log/copiano-web-health.log

check() {
    local url=$1
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" || echo "000")
    echo "[$(date -Iseconds)] $url → $code"
    if [[ "$code" != "200" ]]; then
        echo "ALERT: $url returned $code" >> "$LOG"
        if [[ -n "$SLACK_WEBHOOK" ]]; then
            curl -X POST -H 'Content-Type: application/json' \
                -d "{\"text\":\"🚨 CoPiano health check failed: $url → $code\"}" \
                "$SLACK_WEBHOOK" >/dev/null || true
        fi
        return 1
    fi
}

# 检查 3 个关键端点
check "$DOMAIN/api/health"
check "$DOMAIN/sitemap.xml"
check "$DOMAIN/"

# 检查 Docker 容器
if ! docker ps --format '{{.Names}}' | grep -q copiano-web; then
    echo "ALERT: copiano-web container not running" >> "$LOG"
    docker logs --tail 20 copiano-web >> "$LOG" 2>&1 || true
fi
