#!/bin/bash
# Prefect 初始化脚本

set -e

echo "🚀 开始设置 Prefect 环境..."

# 检查 Prefect 是否已安装
if ! command -v prefect &> /dev/null; then
    echo "❌ Prefect 未安装，请先运行: pip install -r requirements.txt"
    exit 1
fi

# 启动 Prefect Server（如果未运行）
echo "📡 检查 Prefect Server..."
if ! curl -s http://localhost:4200/api/health > /dev/null 2>&1; then
    echo "⚠️  Prefect Server 未运行，请先启动: prefect server start"
    echo "   或者使用 Docker Compose 启动"
fi

# 创建 Work Pool
echo "🏊 创建 Work Pool..."
WORK_POOL_NAME="${PREFECT_WORK_POOL_NAME:-dify-workflow-pool}"

if prefect work-pool ls | grep -q "$WORK_POOL_NAME"; then
    echo "✅ Work Pool '$WORK_POOL_NAME' 已存在"
else
    echo "📦 创建 Work Pool '$WORK_POOL_NAME'..."
    prefect work-pool create "$WORK_POOL_NAME" --type process
    echo "✅ Work Pool 创建成功"
fi

# 提示启动 Worker
echo ""
echo "✅ Prefect 环境设置完成！"
echo ""
echo "📝 下一步："
echo "   1. 启动 Worker: prefect worker start --pool $WORK_POOL_NAME"
echo "   2. 部署任务: python deployments/daily_report.py"
echo "   3. 访问 UI: http://localhost:4200"
