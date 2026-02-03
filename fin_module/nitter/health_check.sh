#!/bin/bash
# Nitter 健康检查脚本
# 用法: 添加到 crontab -e
# */5 * * * * /path/to/health_check.sh >> /path/to/health_check.log 2>&1

NITTER_URL="http://localhost:8080"
NITTER_DIR="$(dirname "$0")"
LOG_FILE="$NITTER_DIR/health_check.log"

check_health() {
    # 测试首页
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$NITTER_URL/" --max-time 10)
    
    if [ "$HTTP_CODE" != "200" ]; then
        echo "[$(date)] ❌ 首页检查失败，HTTP状态码: $HTTP_CODE"
        return 1
    fi
    
    # 测试 RSS 功能
    RSS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$NITTER_URL/VitalikButerin/rss" --max-time 15)
    
    if [ "$RSS_CODE" != "200" ]; then
        echo "[$(date)] ⚠️ RSS 检查失败，HTTP状态码: $RSS_CODE (可能是 Token 问题)"
        return 2
    fi
    
    echo "[$(date)] ✅ 服务正常运行"
    return 0
}

restart_nitter() {
    echo "[$(date)] 🔄 正在重启 Nitter..."
    cd "$NITTER_DIR"
    docker compose restart nitter
    sleep 10
}

# 主逻辑
check_health
STATUS=$?

if [ $STATUS -eq 1 ]; then
    # 服务完全不可用，尝试重启
    restart_nitter
    check_health
    if [ $? -ne 0 ]; then
        echo "[$(date)] 🚨 重启后仍然失败，需要人工检查！"
    fi
elif [ $STATUS -eq 2 ]; then
    echo "[$(date)] 📝 RSS 失败通常表示 Token 已过期，请更新 sessions.jsonl"
fi
