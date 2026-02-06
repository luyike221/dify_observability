#!/bin/bash
# Prefect 初始化脚本（使用 uv）

set -e

echo "🚀 开始设置 Prefect 环境..."

# 检查 uv 是否已安装
if ! command -v uv &> /dev/null; then
    echo "❌ uv 未安装，请先安装 uv"
    echo "   安装方法: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# 设置 Prefect API URL
echo "⚙️  配置 Prefect API URL..."
uv run prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api 2>/dev/null || true

# 检查 Prefect Server（如果未运行）
echo "📡 检查 Prefect Server..."
if ! curl -s http://localhost:4200/api/health > /dev/null 2>&1; then
    echo "⚠️  Prefect Server 未运行，请先启动: uv run prefect server start"
    echo "   或者使用 Docker Compose 启动"
fi

# 创建 Work Pool
echo "🏊 创建 Work Pool..."
WORK_POOL_NAME="${PREFECT_WORK_POOL_NAME:-dify-workflow-pool}"

if uv run prefect work-pool ls 2>/dev/null | grep -q "$WORK_POOL_NAME"; then
    echo "✅ Work Pool '$WORK_POOL_NAME' 已存在"
else
    echo "📦 创建 Work Pool '$WORK_POOL_NAME'..."
    uv run prefect work-pool create "$WORK_POOL_NAME" --type process
    echo "✅ Work Pool 创建成功"
fi

# 提示启动 Worker
echo ""
echo "✅ Prefect 环境设置完成！"
echo ""
echo "📝 下一步："
echo "   1. 启动 Worker: uv run prefect worker start --pool $WORK_POOL_NAME"
echo "   2. 部署任务: uv run python deployments/daily_report.py"
echo "   3. 访问 UI: http://localhost:4200"
echo "   4. 验证任务: ./scripts/verify.sh"