"""每日报告 Deployment（调试模式：每30秒执行一次）"""

from datetime import datetime, timedelta
from prefect.schedules import Interval

from src.flows.workflow_log_flow import fetch_workflow_logs_flow


if __name__ == "__main__":
    # 调试模式：暂时不限制时间范围，查询所有时间段的日志
    # 生产环境应使用 yesterday 和 today
    # one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    # now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # 创建每30秒执行一次的调度（Prefect 3.x 使用 Interval 而不是 IntervalSchedule）
    schedule = Interval(timedelta(seconds=30))
    
    # 使用 serve() 方法启动服务（Prefect 3.x）
    # serve() 方法会持续运行并自动处理调度
    # 注意：work_pool_name 需要在 Worker 启动时指定，或通过 UI 配置
    fetch_workflow_logs_flow.serve(
        name="daily-workflow-report-debug",
        schedule=schedule,  # 每30秒执行一次（调试模式）
        # cron="0 2 * * *",  # 生产环境：每天 02:00 执行
        parameters={
            # 应用配置（每个应用不同，直接在这里配置）
            "base_url": "http://localhost",  # Dify API 基础 URL（如果未配置，会从 .env 读取）
            "api_token": "app-R7kB8EZhzg4R8o2Li6FA4Dgb",  # 替换为你的应用 API Token
            "app_id": "5ac73990-ee17-4aba-993c-a473e2fa2a90",  # 替换为你的应用 ID（可选）
            
            # 时间范围（暂时不传入，查询所有时间段）
            # "created_at_after": one_hour_ago,
            # "created_at_before": now,
            
            # 输出配置
            "output_format": "csv",
            "output_dir": "./outputs/reports/daily",
            
            # 功能开关
            "fetch_all": True,
            "with_details": True,
            "with_node_executions": True,
            "notify_on_complete": True,
        },
        tags=["daily", "report", "workflow", "debug"],
    )
