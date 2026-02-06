"""参数校验工具"""

from typing import Optional
from datetime import datetime


def validate_iso_datetime(dt_str: Optional[str]) -> bool:
    """
    验证 ISO 8601 格式的日期时间字符串
    
    Args:
        dt_str: 日期时间字符串
    
    Returns:
        是否为有效格式
    """
    if not dt_str:
        return True
    
    try:
        datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return True
    except (ValueError, AttributeError):
        return False


def validate_status(status: Optional[str]) -> bool:
    """
    验证工作流状态
    
    Args:
        status: 状态字符串
    
    Returns:
        是否为有效状态
    """
    if not status:
        return True
    
    valid_statuses = ["succeeded", "failed", "stopped", "partial-succeeded"]
    return status.lower() in valid_statuses


def validate_limit(limit: int) -> bool:
    """
    验证分页限制
    
    Args:
        limit: 每页数量
    
    Returns:
        是否在有效范围内
    """
    return 1 <= limit <= 100


def validate_page(page: int) -> bool:
    """
    验证页码
    
    Args:
        page: 页码
    
    Returns:
        是否大于0
    """
    return page > 0
