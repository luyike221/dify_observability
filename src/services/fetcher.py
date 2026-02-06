"""工作流日志获取服务"""

from typing import Any, Dict, List, Optional
import requests

from src.core.exceptions import DifyAPIError, DifyAuthenticationError
from src.core.logger import get_logger
from src.utils.retry import retry_on_api_error

logger = get_logger(__name__)


class WorkflowLogFetcher:
    """工作流日志获取器"""

    def __init__(
        self,
        base_url: str,
        api_token: str,
        console_token: Optional[str] = None,
        console_email: Optional[str] = None,
        console_password: Optional[str] = None,
    ):
        """
        初始化日志获取器

        Args:
            base_url: Dify API 基础 URL
            api_token: 应用 API Token
            console_token: Console API Token (可选)
            console_email: Console 登录邮箱 (可选)
            console_password: Console 登录密码 (可选)
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.console_token = console_token
        self.console_email = console_email
        self.console_password = console_password
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        })
        
        # Console API session
        self.console_session = None
        if console_token:
            self._init_console_session(console_token)
        elif console_email and console_password:
            self._auto_login_console()

    def _init_console_session(self, token: str):
        """初始化 Console API session"""
        self.console_token = token
        self.console_session = requests.Session()
        self.console_session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    def _auto_login_console(self) -> bool:
        """自动登录 Console API 获取 token"""
        if not self.console_email or not self.console_password:
            return False

        try:
            url = f"{self.base_url}/console/api/login"
            response = requests.post(
                url,
                json={
                    "email": self.console_email,
                    "password": self.console_password,
                },
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("result") == "success":
                data = result.get("data", {})
                access_token = data.get("access_token")
                if access_token:
                    self._init_console_session(access_token)
                    logger.info(f"已自动获取 Console Token (用户: {self.console_email})")
                    return True
                else:
                    logger.error("登录成功但未获取到 access_token")
                    return False
            else:
                error_msg = result.get("data", "未知错误")
                logger.error(f"登录失败: {error_msg}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"自动登录失败: {str(e)}")
            return False

    def _ensure_console_token(self) -> bool:
        """确保 Console Token 有效"""
        if not self.console_session:
            if self.console_email and self.console_password:
                return self._auto_login_console()
            return False
        return True

    def _handle_console_auth_error(self) -> bool:
        """处理 Console API 认证错误"""
        if self.console_email and self.console_password:
            logger.warning("Console Token 可能已失效，尝试重新登录...")
            if self._auto_login_console():
                return True
        return False

    @retry_on_api_error(max_attempts=3)
    def fetch_logs(
        self,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        created_at_before: Optional[str] = None,
        created_at_after: Optional[str] = None,
        created_by_end_user_session_id: Optional[str] = None,
        created_by_account: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """获取工作流日志"""
        url = f"{self.base_url}/v1/workflows/logs"
        params = {
            "page": page,
            "limit": limit,
        }

        if keyword:
            params["keyword"] = keyword
        if status:
            params["status"] = status
        if created_at_before:
            params["created_at__before"] = created_at_before
        if created_at_after:
            params["created_at__after"] = created_at_after
        if created_by_end_user_session_id:
            params["created_by_end_user_session_id"] = created_by_end_user_session_id
        if created_by_account:
            params["created_by_account"] = created_by_account

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            status_code = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            response_text = getattr(e.response, "text", None) if hasattr(e, "response") else None
            raise DifyAPIError(
                f"请求失败: {str(e)}",
                status_code=status_code,
                response_text=response_text,
            ) from e

    def fetch_all_logs(
        self,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
        created_at_before: Optional[str] = None,
        created_at_after: Optional[str] = None,
        created_by_end_user_session_id: Optional[str] = None,
        created_by_account: Optional[str] = None,
        limit: int = 20,
        max_pages: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """获取所有日志（自动翻页）"""
        all_logs = []
        page = 1

        while True:
            if max_pages and page > max_pages:
                break

            result = self.fetch_logs(
                keyword=keyword,
                status=status,
                created_at_before=created_at_before,
                created_at_after=created_at_after,
                created_by_end_user_session_id=created_by_end_user_session_id,
                created_by_account=created_by_account,
                page=page,
                limit=limit,
            )

            logs = result.get("data", [])
            if not logs:
                break

            all_logs.extend(logs)
            logger.debug(f"已获取第 {page} 页，共 {len(all_logs)} 条日志")

            if not result.get("has_more", False):
                break

            page += 1

        logger.info(f"共获取 {len(all_logs)} 条日志")
        return all_logs

    @retry_on_api_error(max_attempts=3)
    def fetch_workflow_run_detail(self, workflow_run_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流运行详情"""
        url = f"{self.base_url}/v1/workflows/run/{workflow_run_id}"
        
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                if e.response.status_code == 404:
                    return None
                raise DifyAPIError(
                    f"请求失败: {e.response.status_code} - {e.response.text}",
                    status_code=e.response.status_code,
                    response_text=e.response.text,
                ) from e
            raise DifyAPIError(f"请求失败: {str(e)}") from e

    def fetch_node_executions(self, app_id: str, workflow_run_id: str) -> List[Dict[str, Any]]:
        """获取工作流运行的节点执行详情"""
        if not self._ensure_console_token():
            logger.warning("无法获取 Console Token，跳过节点执行详情")
            return []

        url = f"{self.base_url}/console/api/apps/{app_id}/workflow-runs/{workflow_run_id}/node-executions"
        
        try:
            response = self.console_session.get(url, timeout=30)
            if response.status_code == 404:
                return []
            elif response.status_code == 401:
                if self._handle_console_auth_error():
                    response = self.console_session.get(url, timeout=30)
                    if response.status_code == 401:
                        return []
                    response.raise_for_status()
                else:
                    return []
            response.raise_for_status()
            result = response.json()
            return result.get("data", [])
        except requests.exceptions.RequestException as e:
            logger.warning(f"获取节点执行详情失败: {str(e)}")
            return []

    def enrich_log_with_details(
        self,
        log: Dict[str, Any],
        default_app_id: Optional[str] = None,
        include_node_executions: bool = False,
    ) -> Dict[str, Any]:
        """为日志添加详细信息"""
        workflow_run = log.get("workflow_run", {})
        workflow_run_id = workflow_run.get("id")
        
        if not workflow_run_id:
            return log

        # 获取工作流运行详情
        try:
            run_detail = self.fetch_workflow_run_detail(workflow_run_id)
            if run_detail:
                log["workflow_run_detail"] = run_detail
        except Exception as e:
            logger.warning(f"获取工作流运行详情失败: {str(e)}")
            log["workflow_run_detail_error"] = str(e)

        # 获取节点执行详情
        if include_node_executions:
            app_id = (
                log.get("app_id") or
                default_app_id or
                (run_detail.get("app_id") if run_detail else None)
            )
            
            if app_id:
                try:
                    node_executions = self.fetch_node_executions(app_id, workflow_run_id)
                    log["node_executions"] = node_executions
                except Exception as e:
                    logger.warning(f"获取节点执行详情失败: {str(e)}")
                    log["node_executions_error"] = str(e)
            else:
                log["node_executions_error"] = "无法确定 app_id"

        return log
