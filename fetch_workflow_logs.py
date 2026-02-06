#!/usr/bin/env python3
"""
Dify 工作流日志获取脚本

用于从外部系统获取 Dify 工作流应用的执行日志数据，适用于运维监控场景。

使用方法:
    python fetch_workflow_logs.py --api-token <token> --base-url <url> [选项]

示例:
    # 基本用法
    python fetch_workflow_logs.py --api-token app-R7kB8EZhzg4R8o2Li6FA4Dgb --base-url http://localhost

    # 获取失败的日志
    python fetch_workflow_logs.py --api-token app-R7kB8EZhzg4R8o2Li6FA4Dgb --base-url http://localhost --status failed

    # 搜索关键词并指定时间范围
    python fetch_workflow_logs.py --api-token app-R7kB8EZhzg4R8o2Li6FA4Dgb --base-url http://localhost \\
        --keyword "error" --after "2024-01-01T00:00:00Z" --before "2024-01-31T23:59:59Z"

    # 导出为 JSON 文件
    python fetch_workflow_logs.py --api-token app-R7kB8EZhzg4R8o2Li6FA4Dgb --base-url http://localhost --output logs.json

    # 导出为 Markdown 文件（包含整体摘要和每条日志的详细信息）
    python fetch_workflow_logs.py --api-token app-R7kB8EZhzg4R8o2Li6FA4Dgb --base-url http://localhost \
        --with-details --output-md logs_report.md

    # 获取详细信息（工作流运行详情）
    python fetch_workflow_logs.py --api-token app-R7kB8EZhzg4R8o2Li6FA4Dgb --base-url http://localhost --with-details

    # 获取完整信息（包括节点执行详情，使用账号密码自动获取 Console Token）
    python fetch_workflow_logs.py --api-token app-R7kB8EZhzg4R8o2Li6FA4Dgb --base-url http://localhost \
        --with-details --with-node-executions \
        --console-email 248618931@qq.com --console-password zj0309.. \
        --app-id 5ac73990-ee17-4aba-993c-a473e2fa2a90

    # 或者使用已有的 Console Token
    python fetch_workflow_logs.py --api-token app-R7kB8EZhzg4R8o2Li6FA4Dgb --base-url http://localhost \
        --with-details --with-node-executions \
        --console-token <your_token> \
        --app-id 5ac73990-ee17-4aba-993c-a473e2fa2a90

    # 生成 CSV 报告（问答类应用数相关统计）
    python 01-dify运维监控/fetch_workflow_logs.py --api-token app-R7kB8EZhzg4R8o2Li6FA4Dgb --base-url http://localhost \
        --with-details --with-node-executions \
        --console-email 248618931@qq.com --console-password zj0309.. \
        --app-id 5ac73990-ee17-4aba-993c-a473e2fa2a90 \
        --output-csv-dir .
关于 Console Token:
    Console Token 是用户登录 Dify 控制台后获得的 JWT token，用于访问 Console API。
    
    获取方式（推荐使用方式 1，自动获取）：
    1. 自动获取（推荐）：
       使用 --console-email 和 --console-password 参数，脚本会自动登录并获取 token
       如果 token 失效，脚本会自动重新登录获取新的 token
       
       示例：
       --console-email your-email@example.com --console-password your-password
    
    2. 手动提供 Token：
       使用 --console-token 参数直接提供已获取的 token
       
       获取方法：
       - 通过登录接口：
         curl -X POST "http://localhost/console/api/login" \\
           -H "Content-Type: application/json" \\
           -d '{"email": "your-email@example.com", "password": "your-password"}'
       
       - 从浏览器开发者工具：
         登录 Dify 控制台 -> F12 -> Network -> 查看 Console API 请求的 Authorization header
    
    注意：
    - 如果只需要工作流运行详情，不需要 Console Token（使用 --with-details 即可）
    - 只有需要节点执行详情时才需要 Console Token（使用 --with-node-executions）
    - 使用账号密码方式时，token 失效会自动重新获取，无需手动操作
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("错误: 需要安装 requests 库")
    print("请运行: pip install requests")
    sys.exit(1)


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
            base_url: Dify API 基础 URL (例如: https://api.dify.ai)
            api_token: 应用 API Token (格式: app-xxx)
            console_token: Console API Token (可选，用于获取节点执行详情)
            console_email: Console 登录邮箱 (可选，用于自动获取 token)
            console_password: Console 登录密码 (可选，用于自动获取 token)
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
        
        # Console API session (用于获取节点执行详情)
        self.console_session = None
        if console_token:
            self._init_console_session(console_token)
        elif console_email and console_password:
            # 自动获取 console token
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
        """
        自动登录 Console API 获取 token

        Returns:
            是否成功获取 token
        """
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
                    print(f"✅ 已自动获取 Console Token (用户: {self.console_email})")
                    return True
                else:
                    print(f"❌ 登录成功但未获取到 access_token")
                    return False
            else:
                error_msg = result.get("data", "未知错误")
                print(f"❌ 登录失败: {error_msg}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ 自动登录失败: {str(e)}")
            return False

    def _ensure_console_token(self) -> bool:
        """
        确保 Console Token 有效，如果失效则自动重新获取

        Returns:
            Console session 是否可用
        """
        if not self.console_session:
            # 如果没有 session，尝试自动登录
            if self.console_email and self.console_password:
                return self._auto_login_console()
            return False
        
        # 如果已有 session，直接返回 True
        # token 失效会在实际请求时检测并重新获取
        return True

    def _handle_console_auth_error(self):
        """处理 Console API 认证错误，尝试重新登录"""
        if self.console_email and self.console_password:
            print("⚠️  Console Token 可能已失效，尝试重新登录...")
            if self._auto_login_console():
                return True
        return False

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
        """
        获取工作流日志

        Args:
            keyword: 搜索关键词
            status: 执行状态 (succeeded/failed/stopped/partial-succeeded)
            created_at_before: 创建时间上限 (ISO 8601 格式)
            created_at_after: 创建时间下限 (ISO 8601 格式)
            created_by_end_user_session_id: 终端用户会话ID
            created_by_account: 账户邮箱
            page: 页码
            limit: 每页数量

        Returns:
            包含日志数据的字典
        """
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
            if hasattr(e.response, "text"):
                error_msg = f"请求失败: {e.response.status_code} - {e.response.text}"
            else:
                error_msg = f"请求失败: {str(e)}"
            raise Exception(error_msg) from e

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
        """
        获取所有日志（自动翻页）

        Args:
            keyword: 搜索关键词
            status: 执行状态
            created_at_before: 创建时间上限
            created_at_after: 创建时间下限
            created_by_end_user_session_id: 终端用户会话ID
            created_by_account: 账户邮箱
            limit: 每页数量
            max_pages: 最大页数限制（None 表示无限制）

        Returns:
            所有日志记录的列表
        """
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

            if not result.get("has_more", False):
                break

            page += 1

        return all_logs

    def fetch_workflow_run_detail(self, workflow_run_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流运行详情

        Args:
            workflow_run_id: 工作流运行ID

        Returns:
            工作流运行详情字典，如果不存在则返回 None
        """
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
                error_msg = f"请求失败: {e.response.status_code} - {e.response.text}"
            else:
                error_msg = f"请求失败: {str(e)}"
            raise Exception(error_msg) from e

    def fetch_node_executions(self, app_id: str, workflow_run_id: str) -> List[Dict[str, Any]]:
        """
        获取工作流运行的节点执行详情

        Args:
            app_id: 应用ID
            workflow_run_id: 工作流运行ID

        Returns:
            节点执行列表，如果无法获取则返回空列表
        """
        if not self._ensure_console_token():
            return []

        url = f"{self.base_url}/console/api/apps/{app_id}/workflow-runs/{workflow_run_id}/node-executions"
        
        try:
            response = self.console_session.get(url, timeout=30)
            if response.status_code == 404:
                return []
            elif response.status_code == 401:
                # Token 失效，尝试重新登录
                if self._handle_console_auth_error():
                    # 重新请求
                    response = self.console_session.get(url, timeout=30)
                    if response.status_code == 401:
                        return []
                    response.raise_for_status()
                else:
                    return []
            response.raise_for_status()
            result = response.json()
            return result.get("data", [])
        except requests.exceptions.RequestException:
            # 如果获取失败，返回空列表（不抛出异常）
            return []

    def enrich_log_with_details(self, log: Dict[str, Any], default_app_id: Optional[str] = None, include_node_executions: bool = False) -> Dict[str, Any]:
        """
        为日志添加详细信息

        Args:
            log: 日志记录
            default_app_id: 默认应用ID（如果日志中没有app_id则使用此值）
            include_node_executions: 是否包含节点执行详情

        Returns:
            增强后的日志记录
        """
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
            # 如果获取失败，记录但不中断流程
            log["workflow_run_detail_error"] = str(e)

        # 获取节点执行详情（如果需要且支持）
        if include_node_executions:
            # 尝试从多个地方获取 app_id
            app_id = (
                log.get("app_id") or  # 从日志中获取
                default_app_id or      # 使用默认值
                (run_detail.get("app_id") if run_detail else None)  # 从工作流运行详情中获取
            )
            
            if app_id:
                try:
                    node_executions = self.fetch_node_executions(app_id, workflow_run_id)
                    log["node_executions"] = node_executions
                except Exception as e:
                    # 如果获取失败，记录但不中断流程
                    log["node_executions_error"] = str(e)
            else:
                log["node_executions_error"] = "无法确定 app_id"

        return log


def format_timestamp(timestamp: Optional[float]) -> str:
    """格式化时间戳"""
    if timestamp is None:
        return "N/A"
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(timestamp)


def format_json_for_markdown(data: Any) -> str:
    """
    格式化 JSON 数据为 Markdown 友好的格式，处理 Unicode 编码
    
    Args:
        data: 要格式化的数据（可能是 dict、list 或 JSON 字符串）
    
    Returns:
        格式化后的 JSON 字符串
    """
    def decode_json_strings(obj: Any) -> Any:
        """递归解码嵌套的 JSON 字符串"""
        if isinstance(obj, str):
            # 尝试解析为 JSON
            try:
                parsed = json.loads(obj)
                # 如果解析成功，递归处理解析后的对象
                return decode_json_strings(parsed)
            except (json.JSONDecodeError, TypeError):
                # 如果不是有效的 JSON，直接返回字符串
                return obj
        elif isinstance(obj, dict):
            # 递归处理字典的每个值
            return {k: decode_json_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            # 递归处理列表的每个元素
            return [decode_json_strings(item) for item in obj]
        else:
            # 其他类型直接返回
            return obj
    
    # 先解码所有嵌套的 JSON 字符串
    decoded_data = decode_json_strings(data)
    
    # 格式化输出，ensure_ascii=False 确保 Unicode 字符直接显示为汉字
    return json.dumps(decoded_data, ensure_ascii=False, indent=2)


def print_logs_table(logs: List[Dict[str, Any]], show_details: bool = False):
    """以表格形式打印日志"""
    if not logs:
        print("没有找到日志记录")
        return

    print(f"\n{'='*120}")
    print(f"{'ID':<38} {'状态':<12} {'创建时间':<20} {'耗时(秒)':<10} {'来源':<15} {'创建者':<20}")
    print(f"{'-'*120}")

    for log in logs:
        log_id = log.get("id", "N/A")[:36]
        workflow_run = log.get("workflow_run", {})
        status = workflow_run.get("status", "N/A")
        created_at = format_timestamp(log.get("created_at"))
        elapsed_time = workflow_run.get("elapsed_time", 0)
        created_from = log.get("created_from", "N/A")
        
        # 获取创建者信息
        created_by_account = log.get("created_by_account", {})
        created_by_end_user = log.get("created_by_end_user", {})
        if created_by_account:
            creator = created_by_account.get("email", "N/A")
        elif created_by_end_user:
            creator = created_by_end_user.get("session_id", "N/A")
        else:
            creator = "N/A"

        print(f"{log_id:<38} {status:<12} {created_at:<20} {elapsed_time:<10.2f} {created_from:<15} {creator:<20}")
        
        # 如果有详细信息，显示详细信息
        if show_details:
            print(f"\n  📋 日志详情 (ID: {log_id}):")
            
            # 工作流运行详情
            run_detail = log.get("workflow_run_detail")
            if run_detail:
                print(f"    ✅ 工作流运行详情已获取")
                print(f"       - 状态: {run_detail.get('status', 'N/A')}")
                print(f"       - 耗时: {run_detail.get('elapsed_time', 0):.2f} 秒")
                print(f"       - Token 消耗: {run_detail.get('total_tokens', 0)}")
                print(f"       - 总步数: {run_detail.get('total_steps', 0)}")
                if run_detail.get("error"):
                    print(f"       - 错误: {run_detail.get('error', '')[:100]}")
                if run_detail.get("inputs"):
                    inputs_str = json.dumps(run_detail.get("inputs"), ensure_ascii=False)
                    if len(inputs_str) > 100:
                        inputs_str = inputs_str[:100] + "..."
                    print(f"       - 输入: {inputs_str}")
                if run_detail.get("outputs"):
                    outputs_str = json.dumps(run_detail.get("outputs"), ensure_ascii=False)
                    if len(outputs_str) > 100:
                        outputs_str = outputs_str[:100] + "..."
                    print(f"       - 输出: {outputs_str}")
            elif log.get("workflow_run_detail_error"):
                print(f"    ❌ 获取工作流运行详情失败: {log.get('workflow_run_detail_error')}")
            else:
                print(f"    ⚠️  未获取工作流运行详情")
            
            # 节点执行详情
            node_executions = log.get("node_executions")
            if node_executions:
                print(f"    ✅ 节点执行详情已获取 ({len(node_executions)} 个节点)")
                for i, node in enumerate(node_executions[:5], 1):  # 只显示前5个节点
                    node_type = node.get("node_type", "N/A")
                    node_title = node.get("title", "N/A")
                    node_status = node.get("status", "N/A")
                    node_time = node.get("elapsed_time", 0)
                    print(f"       {i}. [{node_type}] {node_title} - {node_status} ({node_time:.2f}s)")
                if len(node_executions) > 5:
                    print(f"       ... 还有 {len(node_executions) - 5} 个节点")
            elif log.get("node_executions_error"):
                print(f"    ❌ 获取节点执行详情失败: {log.get('node_executions_error')}")
            elif show_details and log.get("workflow_run"):
                print(f"    ⚠️  未获取节点执行详情（可能需要 --with-node-executions 和 --console-token）")
            
            print()  # 空行分隔

    print(f"{'='*120}\n")


def print_summary(result: Dict[str, Any]):
    """打印摘要信息"""
    total = result.get("total", 0)
    page = result.get("page", 1)
    limit = result.get("limit", 20)
    has_more = result.get("has_more", False)
    data_count = len(result.get("data", []))

    print(f"\n📊 日志摘要:")
    print(f"   总记录数: {total}")
    print(f"   当前页: {page}")
    print(f"   每页数量: {limit}")
    print(f"   当前页记录数: {data_count}")
    print(f"   是否有更多: {'是' if has_more else '否'}")


def generate_markdown(result: Dict[str, Any], include_details: bool = False) -> str:
    """生成 Markdown 格式的报告"""
    from datetime import datetime
    
    md_lines = []
    
    # 标题
    md_lines.append("# Dify 工作流执行日志报告")
    md_lines.append("")
    md_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_lines.append("")
    
    # 整体摘要
    md_lines.append("## 📊 整体摘要")
    md_lines.append("")
    total = result.get("total", 0)
    page = result.get("page", 1)
    limit = result.get("limit", 20)
    has_more = result.get("has_more", False)
    data_count = len(result.get("data", []))
    
    md_lines.append("| 项目 | 值 |")
    md_lines.append("|------|-----|")
    md_lines.append(f"| 总记录数 | {total} |")
    md_lines.append(f"| 当前页 | {page} |")
    md_lines.append(f"| 每页数量 | {limit} |")
    md_lines.append(f"| 当前页记录数 | {data_count} |")
    md_lines.append(f"| 是否有更多 | {'是' if has_more else '否'} |")
    md_lines.append("")
    
    # 统计信息
    logs = result.get("data", [])
    if logs:
        status_count = {}
        for log in logs:
            workflow_run = log.get("workflow_run", {})
            status = workflow_run.get("status", "unknown")
            status_count[status] = status_count.get(status, 0) + 1
        
        md_lines.append("### 状态统计")
        md_lines.append("")
        md_lines.append("| 状态 | 数量 |")
        md_lines.append("|------|------|")
        for status, count in sorted(status_count.items()):
            md_lines.append(f"| {status} | {count} |")
        md_lines.append("")
    
    # 按 ID 详细展示每条日志
    md_lines.append("## 📋 日志详情")
    md_lines.append("")
    
    for i, log in enumerate(logs, 1):
        log_id = log.get("id", "N/A")
        workflow_run = log.get("workflow_run", {})
        
        md_lines.append(f"### {i}. 日志 ID: `{log_id}`")
        md_lines.append("")
        
        # 基本信息
        md_lines.append("#### 基本信息")
        md_lines.append("")
        md_lines.append("| 字段 | 值 |")
        md_lines.append("|------|-----|")
        md_lines.append(f"| 日志ID | `{log_id}` |")
        md_lines.append(f"| 状态 | {workflow_run.get('status', 'N/A')} |")
        md_lines.append(f"| 创建时间 | {format_timestamp(log.get('created_at'))} |")
        md_lines.append(f"| 耗时 | {workflow_run.get('elapsed_time', 0):.2f} 秒 |")
        md_lines.append(f"| 来源 | {log.get('created_from', 'N/A')} |")
        
        # 创建者信息
        created_by_account = log.get("created_by_account", {})
        created_by_end_user = log.get("created_by_end_user", {})
        if created_by_account:
            creator = created_by_account.get("email", "N/A")
            creator_type = "账户"
        elif created_by_end_user:
            creator = created_by_end_user.get("session_id", "N/A")
            creator_type = "终端用户"
        else:
            creator = "N/A"
            creator_type = "N/A"
        
        md_lines.append(f"| 创建者类型 | {creator_type} |")
        md_lines.append(f"| 创建者 | {creator} |")
        md_lines.append("")
        
        # 工作流运行详情
        run_detail = log.get("workflow_run_detail")
        if run_detail:
            md_lines.append("#### 工作流运行详情")
            md_lines.append("")
            md_lines.append("| 字段 | 值 |")
            md_lines.append("|------|-----|")
            md_lines.append(f"| 运行ID | `{run_detail.get('id', 'N/A')}` |")
            md_lines.append(f"| 状态 | {run_detail.get('status', 'N/A')} |")
            md_lines.append(f"| 耗时 | {run_detail.get('elapsed_time', 0):.2f} 秒 |")
            md_lines.append(f"| Token 消耗 | {run_detail.get('total_tokens', 0)} |")
            md_lines.append(f"| 总步数 | {run_detail.get('total_steps', 0)} |")
            md_lines.append(f"| 异常数量 | {run_detail.get('exceptions_count', 0)} |")
            
            if run_detail.get("error"):
                md_lines.append(f"| 错误信息 | {run_detail.get('error', '')} |")
            
            if run_detail.get("created_at"):
                md_lines.append(f"| 创建时间 | {format_timestamp(run_detail.get('created_at'))} |")
            if run_detail.get("finished_at"):
                md_lines.append(f"| 完成时间 | {format_timestamp(run_detail.get('finished_at'))} |")
            
            md_lines.append("")
            
            # 输入
            if run_detail.get("inputs"):
                md_lines.append("##### 输入参数")
                md_lines.append("")
                md_lines.append("```json")
                md_lines.append(format_json_for_markdown(run_detail.get("inputs")))
                md_lines.append("```")
                md_lines.append("")
            
            # 输出
            if run_detail.get("outputs"):
                md_lines.append("##### 输出结果")
                md_lines.append("")
                md_lines.append("```json")
                md_lines.append(format_json_for_markdown(run_detail.get("outputs")))
                md_lines.append("```")
                md_lines.append("")
        elif log.get("workflow_run_detail_error"):
            md_lines.append("#### 工作流运行详情")
            md_lines.append("")
            md_lines.append(f"❌ 获取失败: {log.get('workflow_run_detail_error')}")
            md_lines.append("")
        
        # 节点执行详情
        node_executions = log.get("node_executions")
        if node_executions:
            md_lines.append("#### 节点执行详情")
            md_lines.append("")
            md_lines.append(f"共 {len(node_executions)} 个节点")
            md_lines.append("")
            
            for j, node in enumerate(node_executions, 1):
                md_lines.append(f"##### 节点 {j}: {node.get('title', 'N/A')}")
                md_lines.append("")
                md_lines.append("| 字段 | 值 |")
                md_lines.append("|------|-----|")
                md_lines.append(f"| 节点ID | `{node.get('node_id', 'N/A')}` |")
                md_lines.append(f"| 节点类型 | {node.get('node_type', 'N/A')} |")
                md_lines.append(f"| 标题 | {node.get('title', 'N/A')} |")
                md_lines.append(f"| 状态 | {node.get('status', 'N/A')} |")
                md_lines.append(f"| 耗时 | {node.get('elapsed_time', 0):.2f} 秒 |")
                md_lines.append(f"| 序号 | {node.get('index', 'N/A')} |")
                
                if node.get("predecessor_node_id"):
                    md_lines.append(f"| 前置节点 | `{node.get('predecessor_node_id')}` |")
                
                if node.get("error"):
                    md_lines.append(f"| 错误信息 | {node.get('error', '')} |")
                
                if node.get("created_at"):
                    md_lines.append(f"| 创建时间 | {format_timestamp(node.get('created_at'))} |")
                if node.get("finished_at"):
                    md_lines.append(f"| 完成时间 | {format_timestamp(node.get('finished_at'))} |")
                
                md_lines.append("")
                
                # 节点输入
                if node.get("inputs"):
                    md_lines.append("**输入:**")
                    md_lines.append("")
                    md_lines.append("```json")
                    md_lines.append(format_json_for_markdown(node.get("inputs")))
                    md_lines.append("```")
                    md_lines.append("")
                
                # 节点处理数据
                if node.get("process_data"):
                    md_lines.append("**处理数据:**")
                    md_lines.append("")
                    md_lines.append("```json")
                    md_lines.append(format_json_for_markdown(node.get("process_data")))
                    md_lines.append("```")
                    md_lines.append("")
                
                # 节点输出
                if node.get("outputs"):
                    md_lines.append("**输出:**")
                    md_lines.append("")
                    md_lines.append("```json")
                    md_lines.append(format_json_for_markdown(node.get("outputs")))
                    md_lines.append("```")
                    md_lines.append("")
        elif log.get("node_executions_error"):
            md_lines.append("#### 节点执行详情")
            md_lines.append("")
            md_lines.append(f"❌ 获取失败: {log.get('node_executions_error')}")
            md_lines.append("")
        
        # 分隔线
        if i < len(logs):
            md_lines.append("---")
            md_lines.append("")
    
    return "\n".join(md_lines)


def generate_csv_reports(result: Dict[str, Any], output_dir: str):
    """
    生成 CSV 报告文件
    
    Args:
        result: 日志数据结果
        output_dir: 输出目录
    """
    import os
    
    logs = result.get("data", [])
    if not logs:
        print("⚠️  没有日志数据，无法生成 CSV 报告")
        return
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 提取数据
    qa_pairs = []  # 用户问答对
    user_stats = defaultdict(lambda: {
        "message_count": 0,
        "first_date": None,
        "last_date": None,
        "dates": set()
    })
    daily_stats = defaultdict(int)  # 每日消息数
    total_tokens = 0
    total_cost = 0.0
    session_ids = set()
    session_qa_map = defaultdict(list)  # 按会话ID分组的问题
    
    # 处理每条日志
    for idx, log in enumerate(logs, 1):
        workflow_run = log.get("workflow_run", {})
        run_detail = log.get("workflow_run_detail", {})
        node_executions = log.get("node_executions", [])
        
        # 获取基本信息
        created_at = log.get("created_at")
        if created_at:
            date_str = format_timestamp(created_at).split()[0]  # 只取日期部分
            daily_stats[date_str] += 1
        
        # 获取用户ID
        user_id = None
        created_by_account = log.get("created_by_account", {})
        created_by_end_user = log.get("created_by_end_user", {})
        if created_by_end_user:
            user_id = created_by_end_user.get("session_id")
        elif created_by_account:
            user_id = created_by_account.get("email")
        
        if not user_id:
            # 尝试从输入中获取
            if run_detail:
                inputs = run_detail.get("inputs", {})
                if isinstance(inputs, str):
                    try:
                        inputs = json.loads(inputs)
                    except (json.JSONDecodeError, TypeError):
                        inputs = {}
                elif not isinstance(inputs, dict):
                    inputs = {}
            else:
                inputs = {}
            user_id = inputs.get("sys.user_id") or inputs.get("sys", {}).get("user_id")
        
        # 获取会话ID（使用 workflow_run_id 作为会话标识）
        session_id = workflow_run.get("id") or log.get("id")
        if session_id:
            session_ids.add(session_id)
        
        # 获取用户提问和AI回答
        user_query = ""
        ai_answer = ""
        attachments = []
        knowledge_base_name = ""
        document_names = []
        text_segments = []
        
        if run_detail:
            # 处理 inputs（可能是字符串或字典）
            inputs = run_detail.get("inputs", {})
            if isinstance(inputs, str):
                try:
                    inputs = json.loads(inputs)
                except (json.JSONDecodeError, TypeError):
                    inputs = {}
            elif not isinstance(inputs, dict):
                inputs = {}
            
            # 处理 outputs（可能是字符串或字典）
            outputs = run_detail.get("outputs", {})
            if isinstance(outputs, str):
                try:
                    outputs = json.loads(outputs)
                except (json.JSONDecodeError, TypeError):
                    outputs = {}
            elif not isinstance(outputs, dict):
                outputs = {}
            
            # 用户提问
            user_query = inputs.get("query") or inputs.get("sys.query", "") or ""
            
            # AI回答
            ai_answer = outputs.get("text", "") or ""
            
            # 附件
            files = inputs.get("sys.files", []) or inputs.get("sys", {}).get("files", [])
            if files:
                attachments = [f.get("name", "") or f.get("filename", "") for f in files if isinstance(f, dict)]
        
        # 从节点执行详情中获取知识库信息
        for node in node_executions:
            if node.get("node_type") == "knowledge-retrieval":
                node_outputs = node.get("outputs", {})
                if isinstance(node_outputs, str):
                    try:
                        node_outputs = json.loads(node_outputs)
                    except:
                        continue
                
                result_list = node_outputs.get("result", [])
                if result_list:
                    for item in result_list:
                        metadata = item.get("metadata", {})
                        if metadata:
                            dataset_name = metadata.get("dataset_name", "")
                            document_name = metadata.get("document_name", "")
                            content = item.get("content", "")
                            score = metadata.get("score", 0)
                            
                            if dataset_name and dataset_name not in knowledge_base_name:
                                if knowledge_base_name:
                                    knowledge_base_name += "; " + dataset_name
                                else:
                                    knowledge_base_name = dataset_name
                            
                            if document_name and document_name not in document_names:
                                document_names.append(document_name)
                            
                            if content:
                                segment_text = f"相似度:{score:.4f} {content[:200]}"
                                text_segments.append(segment_text)
        
        # 统计用户信息
        if user_id:
            user_stats[user_id]["message_count"] += 1
            if created_at:
                date_obj = datetime.fromtimestamp(created_at)
                if not user_stats[user_id]["first_date"] or date_obj < user_stats[user_id]["first_date"]:
                    user_stats[user_id]["first_date"] = date_obj
                if not user_stats[user_id]["last_date"] or date_obj > user_stats[user_id]["last_date"]:
                    user_stats[user_id]["last_date"] = date_obj
                user_stats[user_id]["dates"].add(date_obj.date())
        
        # 统计Token和费用
        if run_detail:
            total_tokens += run_detail.get("total_tokens", 0) or 0
            # 从节点执行详情中获取费用
            for node in node_executions:
                if node.get("node_type") == "llm":
                    process_data = node.get("process_data", {})
                    if isinstance(process_data, str):
                        try:
                            process_data = json.loads(process_data)
                        except:
                            continue
                    if not isinstance(process_data, dict):
                        continue
                    usage = process_data.get("usage", {})
                    if usage and isinstance(usage, dict):
                        price = usage.get("total_price", 0)
                        # 确保 price 是数字类型
                        if isinstance(price, str):
                            try:
                                price = float(price)
                            except (ValueError, TypeError):
                                price = 0
                        elif not isinstance(price, (int, float)):
                            price = 0
                        total_cost += price
        
        # 构建问答对（先收集，后续按会话排序）
        qa_data = {
            "序号": idx,
            "用户id": user_id or "",
            "会话id": session_id or "",
            "问题排序": 1,  # 后续会重新计算
            "用户提问": user_query,
            "附件名称": "; ".join(attachments) if attachments else "",
            "AI回答": ai_answer[:5000] if len(ai_answer) > 5000 else ai_answer,  # 限制长度
            "知识库名称": knowledge_base_name,
            "引用的文档名称": "; ".join(document_names[:5]),  # 最多5个文档
            "文本片段内容1": text_segments[0] if text_segments else "",
            "文本片段内容2": text_segments[1] if len(text_segments) > 1 else "",
            "文本片段内容N": "; ".join(text_segments[2:10]) if len(text_segments) > 2 else "",  # 最多10个片段
            "创建时间": format_timestamp(created_at) if created_at else "",
            "created_at": created_at,  # 用于排序
        }
        
        if session_id:
            session_qa_map[session_id].append(qa_data)
        else:
            qa_pairs.append(qa_data)
    
    # 按会话ID分组，计算问题排序
    for session_id, session_qas in session_qa_map.items():
        # 按创建时间排序
        session_qas.sort(key=lambda x: x.get("created_at") or 0)
        # 分配问题排序
        for order, qa in enumerate(session_qas, 1):
            qa["问题排序"] = order
            # 移除临时字段
            qa.pop("created_at", None)
            qa_pairs.append(qa)
    
    # 按序号排序（保持原始顺序）
    qa_pairs.sort(key=lambda x: x["序号"])
    
    # 1. 生成总览 CSV
    overview_file = os.path.join(output_dir, "问答类应用数-总览.csv")
    with open(overview_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["开始日期", "结束日期", "全部消息数", "用户数", "全部会话数", "平均会话互动数", "Token输出速度", "用户满意度", "费用消耗"])
        
        if logs:
            dates = [datetime.fromtimestamp(log.get("created_at")) for log in logs if log.get("created_at")]
            if dates:
                start_date = min(dates).strftime("%Y-%m-%d")
                end_date = max(dates).strftime("%Y-%m-%d")
            else:
                start_date = ""
                end_date = ""
            
            total_messages = len(logs)
            total_users = len(user_stats)
            total_sessions = len(session_ids)
            avg_interactions = total_messages / total_sessions if total_sessions > 0 else 0
            
            # Token输出速度（简化计算：总tokens/总耗时）
            total_time = sum(workflow_run.get("elapsed_time", 0) for log in logs if log.get("workflow_run", {}).get("elapsed_time"))
            token_speed = total_tokens / total_time if total_time > 0 else 0
            
            writer.writerow([
                start_date,
                end_date,
                total_messages,
                total_users,
                total_sessions,
                f"{avg_interactions:.2f}",
                f"{token_speed:.2f} tokens/秒",
                "",  # 用户满意度（需要额外数据）
                f"{total_cost:.6f}",
            ])
        else:
            writer.writerow(["", "", "", "", "", "", "", "", ""])
    
    # 2. 生成每日消息数 CSV
    daily_file = os.path.join(output_dir, "问答类应用数-每日消息数.csv")
    with open(daily_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["日期", "消息数量"])
        for date_str in sorted(daily_stats.keys()):
            writer.writerow([date_str, daily_stats[date_str]])
    
    # 3. 生成用户列表 CSV
    user_list_file = os.path.join(output_dir, "问答类应用数-用户列表.csv")
    with open(user_list_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["用户ID", "消息数", "使用天数", "首次使用日期", "最后使用日期"])
        for user_id, stats in sorted(user_stats.items(), key=lambda x: x[1]["message_count"], reverse=True):
            use_days = len(stats["dates"])
            first_date = stats["first_date"].strftime("%Y-%m-%d") if stats["first_date"] else ""
            last_date = stats["last_date"].strftime("%Y-%m-%d") if stats["last_date"] else ""
            writer.writerow([user_id, stats["message_count"], use_days, first_date, last_date])
    
    # 4. 生成用户问答对 CSV
    qa_file = os.path.join(output_dir, "问答类应用数-用户问答对.csv")
    with open(qa_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        # 写入表头（第一行空行，第二行标题）
        writer.writerow([""] * 13)
        writer.writerow([
            "序号", "用户id", "会话id", "问题排序（同一个会话ID，提问先后顺序）",
            "用户提问", "附件名称：名称.后缀", "AI回答", "知识库名称", "引用的文档名称",
            "文本片段内容1（相似度+文本内容）", "文本片段内容2（相似度+文本内容）",
            "文本片段内容N（相似度+文本内容）", "创建时间"
        ])
        writer.writerow([""] * 13)
        
        # 写入数据
        for qa in qa_pairs:
            writer.writerow([
                qa["序号"],
                qa["用户id"],
                qa["会话id"],
                qa["问题排序"],
                qa["用户提问"],
                qa["附件名称"],
                qa["AI回答"],
                qa["知识库名称"],
                qa["引用的文档名称"],
                qa["文本片段内容1"],
                qa["文本片段内容2"],
                qa["文本片段内容N"],
                qa["创建时间"],
            ])
        
        # 写入说明
        writer.writerow([""] * 13)
        writer.writerow(["注：此处区分是否可上传附件、是否引用RAG知识库，若无内容，为空即可。"] + [""] * 12)
        writer.writerow([""] * 13)
    
    print(f"✅ CSV 报告已生成到目录: {output_dir}")
    print(f"   - 总览: {overview_file}")
    print(f"   - 每日消息数: {daily_file}")
    print(f"   - 用户列表: {user_list_file}")
    print(f"   - 用户问答对: {qa_file}")


def main():
    parser = argparse.ArgumentParser(
        description="获取 Dify 工作流应用执行日志",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # 必需参数
    parser.add_argument(
        "--api-token",
        required=True,
        help="应用 API Token (格式: app-xxx)",
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Dify API 基础 URL (例如: https://api.dify.ai)",
    )

    # 过滤参数
    parser.add_argument(
        "--keyword",
        help="搜索关键词（匹配输入、输出、会话ID或工作流运行ID）",
    )
    parser.add_argument(
        "--status",
        choices=["succeeded", "failed", "stopped", "partial-succeeded"],
        help="过滤执行状态",
    )
    parser.add_argument(
        "--before",
        dest="created_at_before",
        help="过滤在此时间之前创建的日志 (ISO 8601 格式, 例如: 2024-01-01T00:00:00Z)",
    )
    parser.add_argument(
        "--after",
        dest="created_at_after",
        help="过滤在此时间之后创建的日志 (ISO 8601 格式, 例如: 2024-01-01T00:00:00Z)",
    )
    parser.add_argument(
        "--end-user-session-id",
        dest="created_by_end_user_session_id",
        help="按终端用户会话ID过滤",
    )
    parser.add_argument(
        "--account",
        dest="created_by_account",
        help="按账户邮箱过滤",
    )

    # 分页参数
    parser.add_argument(
        "--page",
        type=int,
        default=1,
        help="页码 (默认: 1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="每页数量 (默认: 20, 最大: 100)",
    )

    # 输出选项
    parser.add_argument(
        "--output",
        "-o",
        help="输出到 JSON 文件",
    )
    parser.add_argument(
        "--output-md",
        help="输出到 Markdown 文件",
    )
    parser.add_argument(
        "--output-csv-dir",
        help="输出 CSV 报告到指定目录（生成问答类应用数相关的 CSV 文件）",
    )
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="输出格式 (默认: table)",
    )
    parser.add_argument(
        "--fetch-all",
        action="store_true",
        help="获取所有日志（自动翻页）",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="最大页数限制（仅在使用 --fetch-all 时有效）",
    )
    
    # 详细信息选项
    parser.add_argument(
        "--with-details",
        action="store_true",
        help="获取每条日志的详细信息（工作流运行详情）",
    )
    parser.add_argument(
        "--with-node-executions",
        action="store_true",
        help="获取节点执行详情（需要 --console-token）",
    )
    parser.add_argument(
        "--console-token",
        help="Console API Token（用户登录后获得的 JWT token，用于获取节点执行详情，可选）",
    )
    parser.add_argument(
        "--console-email",
        help="Console 登录邮箱（用于自动获取 Console Token，可选）",
    )
    parser.add_argument(
        "--console-password",
        help="Console 登录密码（用于自动获取 Console Token，可选）",
    )
    parser.add_argument(
        "--app-id",
        help="应用ID（如果日志中没有app_id字段，需要手动指定）",
    )

    args = parser.parse_args()

    # 验证参数
    if args.limit < 1 or args.limit > 100:
        print("错误: --limit 必须在 1-100 之间")
        sys.exit(1)

    if args.page < 1:
        print("错误: --page 必须大于 0")
        sys.exit(1)

    # 验证参数
    if args.with_node_executions:
        if not args.console_token and not (args.console_email and args.console_password):
            print("错误: 使用 --with-node-executions 时必须提供 --console-token 或 --console-email + --console-password")
            sys.exit(1)

    # 创建获取器
    try:
        fetcher = WorkflowLogFetcher(
            args.base_url,
            args.api_token,
            console_token=args.console_token,
            console_email=args.console_email,
            console_password=args.console_password,
        )
    except Exception as e:
        print(f"错误: 初始化失败 - {e}")
        sys.exit(1)

    # 获取日志
    try:
        if args.fetch_all:
            print("正在获取所有日志...")
            logs = fetcher.fetch_all_logs(
                keyword=args.keyword,
                status=args.status,
                created_at_before=args.created_at_before,
                created_at_after=args.created_at_after,
                created_by_end_user_session_id=args.created_by_end_user_session_id,
                created_by_account=args.created_by_account,
                limit=args.limit,
                max_pages=args.max_pages,
            )
            result = {
                "total": len(logs),
                "data": logs,
                "has_more": False,
            }
        else:
            result = fetcher.fetch_logs(
                keyword=args.keyword,
                status=args.status,
                created_at_before=args.created_at_before,
                created_at_after=args.created_at_after,
                created_by_end_user_session_id=args.created_by_end_user_session_id,
                created_by_account=args.created_by_account,
                page=args.page,
                limit=args.limit,
            )
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)

    # 获取详细信息（如果需要）
    if args.with_details or args.with_node_executions:
        print("正在获取详细信息...")
        logs = result.get("data", [])
        enriched_logs = []
        
        for i, log in enumerate(logs, 1):
            print(f"  处理日志 {i}/{len(logs)}...", end="\r")
            try:
                enriched_log = fetcher.enrich_log_with_details(
                    log.copy(),
                    default_app_id=args.app_id,
                    include_node_executions=args.with_node_executions
                )
                enriched_logs.append(enriched_log)
            except Exception as e:
                print(f"\n  警告: 获取日志 {log.get('id', 'unknown')} 的详细信息失败: {e}")
                # 即使失败也添加错误信息
                log["enrichment_error"] = str(e)
                enriched_logs.append(log)  # 使用原始日志
        
        print(f"\n✅ 已处理 {len(enriched_logs)} 条日志")
        result["data"] = enriched_logs

    # 输出结果
    if args.output_csv_dir:
        # 生成 CSV 报告（需要详细信息）
        if not (args.with_details or args.with_node_executions):
            print("⚠️  生成 CSV 报告需要详细信息，自动启用 --with-details")
            # 重新获取详细信息
            logs = result.get("data", [])
            enriched_logs = []
            for i, log in enumerate(logs, 1):
                print(f"  处理日志 {i}/{len(logs)}...", end="\r")
                try:
                    enriched_log = fetcher.enrich_log_with_details(
                        log.copy(),
                        default_app_id=args.app_id,
                        include_node_executions=args.with_node_executions
                    )
                    enriched_logs.append(enriched_log)
                except Exception as e:
                    log["enrichment_error"] = str(e)
                    enriched_logs.append(log)
            print(f"\n✅ 已处理 {len(enriched_logs)} 条日志")
            result["data"] = enriched_logs
        
        generate_csv_reports(result, args.output_csv_dir)
    elif args.output_md:
        # 保存为 Markdown 文件
        show_details = args.with_details or args.with_node_executions
        md_content = generate_markdown(result, include_details=show_details)
        with open(args.output_md, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"✅ Markdown 报告已保存到: {args.output_md}")
        print(f"   总记录数: {len(result.get('data', []))}")
        print(f"   包含详细信息: {'是' if show_details else '否'}")
    elif args.output:
        # 保存到 JSON 文件
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"✅ 日志已保存到: {args.output}")
        print(f"   总记录数: {len(result.get('data', []))}")
    else:
        # 打印到控制台
        if args.format == "json":
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print_summary(result)
            show_details = args.with_details or args.with_node_executions
            print_logs_table(result.get("data", []), show_details=show_details)
            
            # 如果有详细信息但没有显示，提示用户使用 JSON 格式
            if show_details:
                print("\n💡 提示: 要查看完整的详细信息（包括完整的输入/输出和所有节点），请使用:")
                print("   --format json 或 --output <filename>.json 或 --output-md <filename>.md")


if __name__ == "__main__":
    main()
