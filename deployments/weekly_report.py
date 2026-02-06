"""每周报告 Deployment"""

from datetime import datetime, timedelta
from prefect import serve

from src.flows.workflow_log_flow import fetch_workflow_logs_flow


if __name__ == "__main__":
    # 计算时间范围（上周）
    last_week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
    today = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
    
    fetch_workflow_logs_flow.serve(
        name="weekly-workflow-report",
        cron="0 3 * * 1",  # 每周一 03:00 执行
        parameters={
            "created_at_after": last_week_start,
            "created_at_before": today,
            "output_format": "csv",
            "output_dir": "./outputs/reports/weekly",
            "fetch_all": True,
            "with_details": True,
            "with_node_executions": True,
            "notify_on_complete": True,
        },
        tags=["weekly", "report", "workflow"],
        work_pool_name="dify-workflow-pool",
    )
