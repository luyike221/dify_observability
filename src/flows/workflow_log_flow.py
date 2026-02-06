"""工作流日志获取 Flow"""

from typing import Any, Dict, Optional
from prefect import flow, get_run_logger

from src.core.config import DifyConfig
from src.core.logger import setup_logger, get_logger
from src.flows.tasks.fetch_task import fetch_logs_task
from src.flows.tasks.enrich_task import enrich_logs_task
from src.flows.tasks.report_task import generate_reports_task
from src.services.notifier import create_notification_service

# 初始化日志
setup_logger()


@flow(name="fetch-workflow-logs", log_prints=True)
def fetch_workflow_logs_flow(
    # 过滤参数
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    created_at_before: Optional[str] = None,
    created_at_after: Optional[str] = None,
    created_by_end_user_session_id: Optional[str] = None,
    created_by_account: Optional[str] = None,
    # 输出配置
    output_format: str = "csv",  # csv/markdown/json
    output_dir: str = "./outputs/reports",
    # 功能开关
    fetch_all: bool = True,
    with_details: bool = True,
    with_node_executions: bool = False,
    limit: int = 20,
    max_pages: Optional[int] = None,
    # 通知配置
    notify_on_complete: bool = False,
    # 配置（从环境变量或参数传入）
    base_url: Optional[str] = None,
    api_token: Optional[str] = None,
    app_id: Optional[str] = None,
    console_token: Optional[str] = None,
    console_email: Optional[str] = None,
    console_password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    获取 Dify 工作流日志的主 Flow
    
    Args:
        keyword: 搜索关键词
        status: 执行状态
        created_at_before: 创建时间上限
        created_at_after: 创建时间下限
        created_by_end_user_session_id: 终端用户会话ID
        created_by_account: 账户邮箱
        output_format: 输出格式
        output_dir: 输出目录
        fetch_all: 是否获取所有日志
        with_details: 是否获取详细信息
        with_node_executions: 是否包含节点执行详情
        limit: 每页数量
        max_pages: 最大页数限制
        notify_on_complete: 是否在完成时发送通知
        base_url: Dify API 基础 URL（可选，优先使用环境变量）
        api_token: 应用 API Token（可选，优先使用环境变量）
        app_id: 应用ID（可选，优先使用环境变量）
        console_token: Console API Token（可选）
        console_email: Console 登录邮箱（可选）
        console_password: Console 登录密码（可选）
    
    Returns:
        执行结果字典
    """
    logger = get_run_logger()
    logger.info("开始执行工作流日志获取任务")
    
    # 加载配置
    try:
        config = DifyConfig.from_env()
        # 如果参数提供了值，则覆盖配置
        base_url = base_url or config.base_url
        api_token = api_token or config.api_token
        app_id = app_id or config.app_id
        console_token = console_token or config.console_token
        console_email = console_email or config.console_email
        console_password = console_password or config.console_password
    except Exception as e:
        logger.warning(f"加载配置失败，使用参数值: {e}")
        if not base_url or not api_token:
            raise ValueError("必须提供 base_url 和 api_token（通过参数或环境变量）")
    
    # 打印关键配置（用于排查问题）
    logger.info("=" * 60)
    logger.info("关键配置信息:")
    logger.info(f"  base_url: {base_url}")
    logger.info(f"  api_token: {api_token[:10]}...{api_token[-4:] if len(api_token) > 14 else '***'}")
    logger.info(f"  app_id: {app_id or '(未配置)'}")
    logger.info(f"  时间范围: {created_at_after} ~ {created_at_before}")
    logger.info(f"  输出格式: {output_format}")
    logger.info(f"  输出目录: {output_dir}")
    logger.info(f"  获取所有: {fetch_all}")
    logger.info(f"  包含详情: {with_details}")
    logger.info(f"  包含节点执行: {with_node_executions}")
    logger.info("=" * 60)
    
    # Task 1: 获取日志
    logs_result = fetch_logs_task(
        base_url=base_url,
        api_token=api_token,
        keyword=keyword,
        status=status,
        created_at_before=created_at_before,
        created_at_after=created_at_after,
        created_by_end_user_session_id=created_by_end_user_session_id,
        created_by_account=created_by_account,
        fetch_all=fetch_all,
        limit=limit,
        max_pages=max_pages,
    )
    
    # Task 2: 丰富详情（如果需要）
    if with_details:
        enriched_result = enrich_logs_task(
            logs_result=logs_result,
            base_url=base_url,
            api_token=api_token,
            app_id=app_id,
            console_token=console_token,
            console_email=console_email,
            console_password=console_password,
            with_node_executions=with_node_executions,
        )
    else:
        enriched_result = logs_result
    
    # Task 3: 生成报告
    report_result = generate_reports_task(
        logs_result=enriched_result,
        output_dir=output_dir,
        output_format=output_format,
    )
    
    # Task 4: 发送通知（如果需要）
    if notify_on_complete:
        try:
            config = DifyConfig.from_env()
            if config.notification.enabled:
                notifier = create_notification_service(
                    notification_type=config.notification.type,
                    **config.notification.config
                )
                if notifier:
                    notifier.notify_report_ready(
                        report_path=", ".join(report_result.get("report_files", [])),
                        report_type=output_format,
                    )
        except Exception as e:
            logger.warning(f"发送通知失败: {e}")
    
    result = {
        "logs_count": len(enriched_result.get("data", [])),
        "report_files": report_result.get("report_files", []),
        "report_count": report_result.get("report_count", 0),
        "status": "success",
    }
    
    logger.info(f"任务执行完成: 获取 {result['logs_count']} 条日志，生成 {result['report_count']} 个报告")
    
    return result
