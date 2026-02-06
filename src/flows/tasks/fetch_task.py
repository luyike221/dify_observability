"""获取日志 Task"""

from typing import Any, Dict, List, Optional
from prefect import task

from src.services.fetcher import WorkflowLogFetcher
from src.core.logger import get_logger

logger = get_logger(__name__)


@task(name="fetch-workflow-logs", retries=2, retry_delay_seconds=5)
def fetch_logs_task(
    base_url: str,
    api_token: str,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    created_at_before: Optional[str] = None,
    created_at_after: Optional[str] = None,
    created_by_end_user_session_id: Optional[str] = None,
    created_by_account: Optional[str] = None,
    fetch_all: bool = False,
    limit: int = 20,
    max_pages: Optional[int] = None,
) -> Dict[str, Any]:
    """
    获取工作流日志任务
    
    Args:
        base_url: Dify API 基础 URL
        api_token: 应用 API Token
        keyword: 搜索关键词
        status: 执行状态
        created_at_before: 创建时间上限
        created_at_after: 创建时间下限
        created_by_end_user_session_id: 终端用户会话ID
        created_by_account: 账户邮箱
        fetch_all: 是否获取所有日志
        limit: 每页数量
        max_pages: 最大页数限制
    
    Returns:
        日志数据结果
    """
    logger.info("开始获取工作流日志")
    
    fetcher = WorkflowLogFetcher(base_url=base_url, api_token=api_token)
    
    if fetch_all:
        logs = fetcher.fetch_all_logs(
            keyword=keyword,
            status=status,
            created_at_before=created_at_before,
            created_at_after=created_at_after,
            created_by_end_user_session_id=created_by_end_user_session_id,
            created_by_account=created_by_account,
            limit=limit,
            max_pages=max_pages,
        )
        result = {
            "total": len(logs),
            "data": logs,
            "has_more": False,
        }
    else:
        result = fetcher.fetch_logs(
            keyword=keyword,
            status=status,
            created_at_before=created_at_before,
            created_at_after=created_at_after,
            created_by_end_user_session_id=created_by_end_user_session_id,
            created_by_account=created_by_account,
            page=1,
            limit=limit,
        )
    
    logger.info(f"成功获取 {len(result.get('data', []))} 条日志")
    return result
