"""重试装饰器"""

from functools import wraps
from typing import Callable, Type, Tuple, Any
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)
import requests

from src.core.exceptions import DifyAPIError, DifyAuthenticationError


def retry_on_api_error(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_exceptions: Tuple[Type[Exception], ...] = (requests.RequestException, DifyAPIError),
):
    """
    重试装饰器，用于 API 请求
    
    Args:
        max_attempts: 最大重试次数
        initial_wait: 初始等待时间（秒）
        max_wait: 最大等待时间（秒）
        retry_exceptions: 需要重试的异常类型
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=initial_wait, max=max_wait),
            retry=retry_if_exception_type(retry_exceptions),
            reraise=True,
        )
        def wrapper(*args, **kwargs) -> Any:
            return func(*args, **kwargs)
        return wrapper
    return decorator
