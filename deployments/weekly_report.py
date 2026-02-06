"""每周报告 Deployment"""

from datetime import datetime, timedelta

from src.flows.workflow_log_flow import fetch_workflow_logs_flow


if __name__ == "__main__":
    # 计算时间范围（上周）
    last_week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
    today = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
    
    # 使用 serve() 方法启动服务（Prefect 3.x）
    # serve() 方法会持续运行并自动处理调度
    # 注意：work_pool_name 需要在 Worker 启动时指定，或通过 UI 配置
    fetch_workflow_logs_flow.serve(
        name="weekly-workflow-report",
        cron="0 3 * * 1",  # 每周一 03:00 执行
        parameters={
            # 应用配置（每个应用不同，直接在这里配置）
            "api_token": "app-xxxxxxxxxxxxx",  # 替换为你的应用 API Token
            "app_id": "your-app-id",  # 替换为你的应用 ID（可选）
            
            # 时间范围
            "created_at_after": last_week_start,
            "created_at_before": today,
            
            # 输出配置
            "output_format": "csv",
            "output_dir": "./outputs/reports/weekly",
            
            # 功能开关
            "fetch_all": True,
            "with_details": True,
            "with_node_executions": True,
            "notify_on_complete": True,
        },
        tags=["weekly", "report", "workflow"],
    )
