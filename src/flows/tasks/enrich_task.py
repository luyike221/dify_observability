"""丰富日志详情 Task"""

from typing import Any, Dict, List, Optional
from prefect import task

from src.services.fetcher import WorkflowLogFetcher
from src.core.logger import get_logger

logger = get_logger(__name__)


@task(name="enrich-workflow-logs", retries=1)
def enrich_logs_task(
    logs_result: Dict[str, Any],
    base_url: str,
    api_token: str,
    app_id: Optional[str] = None,
    console_token: Optional[str] = None,
    console_email: Optional[str] = None,
    console_password: Optional[str] = None,
    with_node_executions: bool = False,
) -> Dict[str, Any]:
    """
    丰富日志详情任务
    
    Args:
        logs_result: 日志数据结果
        base_url: Dify API 基础 URL
        api_token: 应用 API Token
        app_id: 应用ID
        console_token: Console API Token
        console_email: Console 登录邮箱
        console_password: Console 登录密码
        with_node_executions: 是否包含节点执行详情
    
    Returns:
        增强后的日志数据结果
    """
    logger.info("开始丰富日志详情")
    
    fetcher = WorkflowLogFetcher(
        base_url=base_url,
        api_token=api_token,
        console_token=console_token,
        console_email=console_email,
        console_password=console_password,
    )
    
    logs = logs_result.get("data", [])
    enriched_logs = []
    
    for i, log in enumerate(logs, 1):
        logger.debug(f"处理日志 {i}/{len(logs)}")
        try:
            enriched_log = fetcher.enrich_log_with_details(
                log.copy(),
                default_app_id=app_id,
                include_node_executions=with_node_executions,
            )
            enriched_logs.append(enriched_log)
        except Exception as e:
            logger.warning(f"获取日志 {log.get('id', 'unknown')} 的详细信息失败: {e}")
            log["enrichment_error"] = str(e)
            enriched_logs.append(log)
    
    result = logs_result.copy()
    result["data"] = enriched_logs
    
    logger.info(f"成功丰富 {len(enriched_logs)} 条日志")
    return result
