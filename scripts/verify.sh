#!/bin/bash
# 快速验证脚本 - 检查项目启动状态和定时任务

set -e

echo "=========================================="
echo "  Dify 工作流监控系统 - 验证脚本"
echo "=========================================="
echo ""

# 检查 Prefect Server
echo "=== 1. 检查 Prefect Server ==="
if curl -s http://127.0.0.1:4200/api/health > /dev/null 2>&1; then
    echo "✅ Prefect Server 运行正常 (http://127.0.0.1:4200)"
else
    echo "❌ Prefect Server 未运行"
    echo "   请运行: uv run prefect server start"
fi
echo ""

# 检查 Work Pool
echo "=== 2. 检查 Work Pool ==="
if uv run prefect work-pool ls 2>/dev/null | grep -q "dify-workflow-pool"; then
    echo "✅ Work Pool 'dify-workflow-pool' 存在"
else
    echo "❌ Work Pool 'dify-workflow-pool' 不存在"
    echo "   请运行: uv run prefect work-pool create dify-workflow-pool --type process"
fi
echo ""

# 检查 Deployments
echo "=== 3. 检查 Deployments ==="
DEPLOYMENTS=$(uv run prefect deployment ls 2>/dev/null | grep -c "fetch-workflow-logs-flow" || echo "0")
if [ "$DEPLOYMENTS" -gt 0 ]; then
    echo "✅ 找到 $DEPLOYMENTS 个 Deployment"
    uv run prefect deployment ls 2>/dev/null | grep "fetch-workflow-logs-flow" || true
else
    echo "❌ 未找到 Deployment"
    echo "   请运行: uv run python deployments/daily_report.py"
    echo "   然后运行: uv run python deployments/weekly_report.py"
fi
echo ""

# 检查最近的 Flow Runs
echo "=== 4. 检查最近的 Flow Runs ==="
FLOW_RUNS=$(uv run prefect flow-run ls --limit 5 2>/dev/null | wc -l)
if [ "$FLOW_RUNS" -gt 1 ]; then
    echo "✅ 找到 Flow Runs 记录"
    uv run prefect flow-run ls --limit 3 2>/dev/null || true
else
    echo "⚠️  暂无 Flow Runs 记录"
    echo "   任务可能还未执行，或需要手动触发"
fi
echo ""

# 检查输出文件
echo "=== 5. 检查输出文件 ==="
if [ -d "outputs/reports/daily" ] && [ "$(ls -A outputs/reports/daily 2>/dev/null)" ]; then
    echo "✅ 每日报告输出目录有文件"
    ls -lh outputs/reports/daily/ | head -5
else
    echo "⚠️  每日报告输出目录为空或不存在"
fi
echo ""

if [ -d "outputs/reports/weekly" ] && [ "$(ls -A outputs/reports/weekly 2>/dev/null)" ]; then
    echo "✅ 每周报告输出目录有文件"
    ls -lh outputs/reports/weekly/ | head -5
else
    echo "⚠️  每周报告输出目录为空或不存在"
fi
echo ""

# 检查日志文件
echo "=== 6. 检查日志文件 ==="
TODAY=$(date +%Y-%m-%d)
if [ -f "outputs/logs/app_${TODAY}.log" ]; then
    echo "✅ 今天的日志文件存在"
    echo "   最后几行日志:"
    tail -3 outputs/logs/app_${TODAY}.log 2>/dev/null || echo "   (日志文件为空)"
else
    echo "⚠️  今天的日志文件不存在"
fi
echo ""

# 总结
echo "=========================================="
echo "  验证完成"
echo "=========================================="
echo ""
echo "📊 访问 Prefect UI: http://127.0.0.1:4200"
echo "📁 查看输出目录: outputs/reports/"
echo "📝 查看日志目录: outputs/logs/"
echo ""
