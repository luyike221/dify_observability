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
    # Block 配置（优先使用）
    config_name: Optional[str] = None,
    # 过滤参数
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    created_at_before: Optional[str] = None,
    created_at_after: Optional[str] = None,
    created_by_end_user_session_id: Optional[str] = None,
    created_by_account: Optional[str] = None,
    # 输出配置（如果使用 Block，这些参数会被 Block 中的值覆盖）
    output_format: Optional[str] = None,  # csv/markdown/json
    output_dir: Optional[str] = None,
    # 功能开关（如果使用 Block，这些参数会被 Block 中的值覆盖）
    fetch_all: Optional[bool] = None,
    with_details: Optional[bool] = None,
    with_node_executions: Optional[bool] = None,
    limit: Optional[int] = None,
    max_pages: Optional[int] = None,
    # 通知配置（如果使用 Block，这些参数会被 Block 中的值覆盖）
    notify_on_complete: Optional[bool] = None,
    # 配置（从环境变量或参数传入，如果使用 Block，这些参数会被 Block 中的值覆盖）
    base_url: Optional[str] = None,
    api_token: Optional[str] = None,
    app_id: Optional[str] = None,
    console_token: Optional[str] = None,
    console_email: Optional[str] = None,
    console_password: Optional[str] = None,
) -> Dict[str, Any]:
    """
    获取 Dify 工作流日志的主 Flow
    
    支持两种配置方式：
    1. 使用 Prefect Block（推荐）：传入 config_name，从 Prefect UI 中管理的 Block 读取配置
    2. 直接传参数（向后兼容）：直接传入所有参数
    
    Args:
        config_name: Prefect Block 名称（如果提供，将从 Block 读取配置）
        keyword: 搜索关键词
        status: 执行状态
        created_at_before: 创建时间上限
        created_at_after: 创建时间下限
        created_by_end_user_session_id: 终端用户会话ID
        created_by_account: 账户邮箱
        output_format: 输出格式（如果使用 Block，会被 Block 中的值覆盖）
        output_dir: 输出目录（如果使用 Block，会被 Block 中的值覆盖）
        fetch_all: 是否获取所有日志（如果使用 Block，会被 Block 中的值覆盖）
        with_details: 是否获取详细信息（如果使用 Block，会被 Block 中的值覆盖）
        with_node_executions: 是否包含节点执行详情（如果使用 Block，会被 Block 中的值覆盖）
        limit: 每页数量（如果使用 Block，会被 Block 中的值覆盖）
        max_pages: 最大页数限制（如果使用 Block，会被 Block 中的值覆盖）
        notify_on_complete: 是否在完成时发送通知（如果使用 Block，会被 Block 中的值覆盖）
        base_url: Dify API 基础 URL（如果使用 Block，会被 Block 中的值覆盖）
        api_token: 应用 API Token（如果使用 Block，会被 Block 中的值覆盖）
        app_id: 应用ID（如果使用 Block，会被 Block 中的值覆盖）
        console_token: Console API Token（如果使用 Block，会被 Block 中的值覆盖）
        console_email: Console 登录邮箱（如果使用 Block，会被 Block 中的值覆盖）
        console_password: Console 登录密码（如果使用 Block，会被 Block 中的值覆盖）
    
    Returns:
        执行结果字典
    """
    logger = get_run_logger()
    logger.info("开始执行工作流日志获取任务")
    
    # 如果提供了 config_name，从 Block 加载配置
    if config_name:
        try:
            from src.blocks.workflow_report_config import WorkflowReportConfig
            logger.info(f"从 Block 加载配置: {config_name}")
            block_config = WorkflowReportConfig.load(config_name)
            
            # 从 Block 读取配置（参数传入的值会覆盖 Block 中的值）
            base_url = base_url or block_config.base_url
            api_token = api_token or block_config.api_token
            app_id = app_id or block_config.app_id
            console_token = console_token or block_config.console_token
            console_email = console_email or block_config.console_email
            console_password = console_password or block_config.console_password
            output_format = output_format or block_config.output_format
            output_dir = output_dir or block_config.output_dir
            fetch_all = fetch_all if fetch_all is not None else block_config.fetch_all
            with_details = with_details if with_details is not None else block_config.with_details
            with_node_executions = with_node_executions if with_node_executions is not None else block_config.with_node_executions
            notify_on_complete = notify_on_complete if notify_on_complete is not None else block_config.notify_on_complete
            limit = limit or block_config.limit
            max_pages = max_pages or block_config.max_pages
            
            logger.info(f"已从 Block '{config_name}' 加载配置")
        except Exception as e:
            logger.error(f"从 Block 加载配置失败: {e}")
            raise ValueError(f"无法加载 Block 配置 '{config_name}': {e}")
    else:
        # 向后兼容：从环境变量或参数加载配置
        logger.info("使用参数或环境变量配置（未使用 Block）")
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
            logger.warning(f"加载环境变量配置失败，使用参数值: {e}")
        
        # 设置默认值（如果未提供）
        output_format = output_format or "csv"
        output_dir = output_dir or "./outputs/reports"
        fetch_all = fetch_all if fetch_all is not None else True
        with_details = with_details if with_details is not None else True
        with_node_executions = with_node_executions if with_node_executions is not None else False
        notify_on_complete = notify_on_complete if notify_on_complete is not None else False
        limit = limit or 20
    
    # 验证必需参数
    if not base_url or not api_token:
        raise ValueError("必须提供 base_url 和 api_token（通过 Block、参数或环境变量）")
    
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
