#!/bin/bash
set -e

echo "🚀 FinRadar 市场追踪服务启动"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📅 时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "🕐 时区: ${TZ:-Asia/Shanghai}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 保存环境变量供 cron 使用
env >> /etc/environment

case "${RUN_MODE:-cron}" in
"once")
    echo "🔄 单次执行模式"
    exec /usr/local/bin/python -m fin_module
    ;;
"cron")
    # 默认定时: 每天早上 8:30 执行
    CRON_SCHEDULE="${CRON_SCHEDULE:-30 8 * * *}"
    
    # 生成 crontab
    echo "${CRON_SCHEDULE} cd /app && /usr/local/bin/python -m fin_module >> /var/log/market.log 2>&1" > /tmp/crontab
    
    echo "📅 定时任务配置:"
    echo "   调度: ${CRON_SCHEDULE}"
    cat /tmp/crontab

    if ! /usr/local/bin/supercronic -test /tmp/crontab; then
        echo "❌ crontab 格式验证失败"
        exit 1
    fi

    # 立即执行一次（如果配置了）
    if [ "${IMMEDIATE_RUN:-true}" = "true" ]; then
        echo ""
        echo "▶️ 立即执行一次..."
        /usr/local/bin/python -m fin_module || true
    fi

    echo ""
    echo "⏰ 启动定时任务: ${CRON_SCHEDULE}"
    echo "🎯 supercronic 将作为 PID 1 运行"
    echo ""
    
    exec /usr/local/bin/supercronic -passthrough-logs /tmp/crontab
    ;;
*)
    # 执行传入的命令
    exec "$@"
    ;;
esac
