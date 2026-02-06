"""每日报告 Deployment（使用 Prefect Block 配置）"""

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
    
    # 使用 Block 配置（推荐方式）
    # 在 Prefect UI 的 Blocks 页面创建名为 "daily-workflow-report-debug" 的 Block
    # 所有应用相关配置（base_url, api_token, app_id, output_dir 等）都在 Block 中管理
    fetch_workflow_logs_flow.serve(
        name="daily-workflow-report-debug",
        schedule=schedule,  # 每30秒执行一次（调试模式）
        # cron="0 2 * * *",  # 生产环境：每天 02:00 执行
        parameters={
            # 使用 Block 配置（在 Prefect UI 中创建名为 "daily-workflow-report-debug" 的 Block）
            "config_name": "daily-workflow-report-debug",
            
            # 时间范围（暂时不传入，查询所有时间段）
            # 如果需要，可以在 Block 中添加时间范围配置，或在这里传入
            # "created_at_after": one_hour_ago,
            # "created_at_before": now,
        },
        tags=["daily", "report", "workflow", "debug"],
    )
    
    # 如果需要覆盖 Block 中的某些配置，可以在 parameters 中传入：
    # parameters={
    #     "config_name": "daily-workflow-report-debug",
    #     "output_dir": "./outputs/reports/daily-custom",  # 覆盖 Block 中的 output_dir
    # }
