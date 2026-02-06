"""工作流日志报表配置 Block（存到 Prefect Server 的 Blocks 里，UI 可维护）"""

from typing import Optional
from prefect.blocks.core import Block
from pydantic import Field


class WorkflowReportConfig(Block):
    """
    工作流日志报表配置 Block
    
    用于在 Prefect UI 中管理不同应用的配置，避免在代码中硬编码参数。
    每个应用可以创建一个 Block 实例，通过 config_name 在 Flow 中引用。
    
    使用方式：
        1. 在 Prefect UI 的 Blocks 页面创建 Block 实例
        2. 在 Flow 中通过 WorkflowReportConfig.load("block-name") 加载配置
        3. 在 Deployment 中只需传入 config_name 参数
    """
    
    # Dify API 配置
    base_url: str = Field(
        ...,
        description="Dify API 基础 URL，例如: http://localhost 或 https://api.dify.ai"
    )
    api_token: str = Field(
        ...,
        description="Dify 应用 API Token（app-xxx 格式）"
    )
    app_id: Optional[str] = Field(
        None,
        description="应用 ID（可选），用于获取应用详情"
    )
    
    # Console 配置（可选，用于需要 Console API 的场景）
    console_token: Optional[str] = Field(
        None,
        description="Console API Token（可选）"
    )
    console_email: Optional[str] = Field(
        None,
        description="Console 登录邮箱（可选）"
    )
    console_password: Optional[str] = Field(
        None,
        description="Console 登录密码（可选）"
    )
    
    # 输出配置
    output_format: str = Field(
        "csv",
        description="输出格式: csv/markdown/json"
    )
    output_dir: str = Field(
        "./outputs/reports/daily",
        description="输出目录路径"
    )
    
    # 功能开关
    fetch_all: bool = Field(
        True,
        description="是否获取所有日志（忽略分页限制）"
    )
    with_details: bool = Field(
        True,
        description="是否获取详细信息（包括节点执行详情）"
    )
    with_node_executions: bool = Field(
        True,
        description="是否包含节点执行详情"
    )
    notify_on_complete: bool = Field(
        True,
        description="是否在完成时发送通知"
    )
    
    # 查询参数（可选）
    limit: int = Field(
        20,
        description="每页数量限制"
    )
    max_pages: Optional[int] = Field(
        None,
        description="最大页数限制（None 表示不限制）"
    )
    
    # Block 元数据
    _block_type_name = "Workflow Report Config"
    
    class Config:
        """Pydantic 配置"""
        json_schema_extra = {
            "example": {
                "base_url": "http://localhost",
                "api_token": "app-R7kB8EZhzg4R8o2Li6FA4Dgb",
                "app_id": "5ac73990-ee17-4aba-993c-a473e2fa2a90",
                "output_format": "csv",
                "output_dir": "./outputs/reports/daily",
                "fetch_all": True,
                "with_details": True,
                "with_node_executions": True,
                "notify_on_complete": True,
            }
        }
