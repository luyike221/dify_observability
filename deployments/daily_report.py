"""每日报告 Deployment（调试模式：每30秒执行一次）"""

from datetime import datetime, timedelta
from prefect import serve
from prefect.schedules import IntervalSchedule

from src.flows.workflow_log_flow import fetch_workflow_logs_flow


if __name__ == "__main__":
    # 调试模式：使用最近1小时的数据范围
    # 生产环境应使用 yesterday 和 today
    one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # 创建每30秒执行一次的调度
    schedule = IntervalSchedule(interval=timedelta(seconds=30))
    
    fetch_workflow_logs_flow.serve(
        name="daily-workflow-report-debug",
        schedule=schedule,  # 每30秒执行一次（调试模式）
        # cron="0 2 * * *",  # 生产环境：每天 02:00 执行
        parameters={
            "created_at_after": one_hour_ago,
            "created_at_before": now,
            "output_format": "csv",
            "output_dir": "./outputs/reports/daily",
            "fetch_all": True,
            "with_details": True,
            "with_node_executions": True,
            "notify_on_complete": True,
        },
        tags=["daily", "report", "workflow", "debug"],
        work_pool_name="dify-workflow-pool",
    )
