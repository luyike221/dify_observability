"""每周报告 Deployment（使用 Prefect Block 配置）"""

from datetime import datetime, timedelta

from src.flows.workflow_log_flow import fetch_workflow_logs_flow


if __name__ == "__main__":
    # 计算时间范围（上周）
    last_week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
    today = datetime.now().strftime("%Y-%m-%dT00:00:00Z")
    
    # 使用 serve() 方法启动服务（Prefect 3.x）
    # serve() 方法会持续运行并自动处理调度
    # 注意：work_pool_name 需要在 Worker 启动时指定，或通过 UI 配置
    
    # 使用 Block 配置（推荐方式）
    # 在 Prefect UI 的 Blocks 页面创建名为 "weekly-workflow-report" 的 Block
    # 所有应用相关配置（base_url, api_token, app_id, output_dir 等）都在 Block 中管理
    fetch_workflow_logs_flow.serve(
        name="weekly-workflow-report",
        cron="0 3 * * 1",  # 每周一 03:00 执行
        parameters={
            # 使用 Block 配置（在 Prefect UI 中创建名为 "weekly-workflow-report" 的 Block）
            "config_name": "weekly-workflow-report",
            
            # 时间范围（可以在这里传入，也可以考虑在 Block 中添加）
            "created_at_after": last_week_start,
            "created_at_before": today,
        },
        tags=["weekly", "report", "workflow"],
    )
    
    # 如果需要覆盖 Block 中的某些配置，可以在 parameters 中传入：
    # parameters={
    #     "config_name": "weekly-workflow-report",
    #     "output_dir": "./outputs/reports/weekly-custom",  # 覆盖 Block 中的 output_dir
    #     "created_at_after": last_week_start,
    #     "created_at_before": today,
    # }
