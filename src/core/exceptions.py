"""自定义异常类"""


class DifyWorkflowLogError(Exception):
    """Dify 工作流日志相关错误的基类"""
    pass


class DifyAPIError(DifyWorkflowLogError):
    """Dify API 请求错误"""
    def __init__(self, message: str, status_code: int = None, response_text: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class DifyAuthenticationError(DifyAPIError):
    """Dify API 认证错误"""
    pass


class DifyConfigError(DifyWorkflowLogError):
    """配置错误"""
    pass


class DifyStorageError(DifyWorkflowLogError):
    """存储服务错误"""
    pass


class DifyNotificationError(DifyWorkflowLogError):
    """通知服务错误"""
    pass
