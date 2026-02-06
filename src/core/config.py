"""配置管理模块"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class StorageConfig(BaseModel):
    """存储配置"""
    type: str = Field(default="local", description="存储类型: local/oss/s3")
    config: Dict[str, Any] = Field(default_factory=dict, description="存储后端配置")


class NotificationConfig(BaseModel):
    """通知配置"""
    enabled: bool = Field(default=False, description="是否启用通知")
    type: str = Field(default="email", description="通知类型: email/dingtalk/wechat")
    config: Dict[str, Any] = Field(default_factory=dict, description="通知渠道配置")


class DifyConfig(BaseModel):
    """Dify 配置"""
    
    # API 配置
    base_url: str = Field(..., description="Dify API 基础 URL")
    api_token: str = Field(..., description="应用 API Token")
    app_id: Optional[str] = Field(default=None, description="应用 ID")
    
    # Console API 配置（可选）
    console_email: Optional[str] = Field(default=None, description="Console 登录邮箱")
    console_password: Optional[str] = Field(default=None, description="Console 登录密码")
    console_token: Optional[str] = Field(default=None, description="Console API Token")
    
    # 输出配置
    output_base_dir: str = Field(default="./outputs", description="输出基础目录")
    storage: StorageConfig = Field(default_factory=StorageConfig, description="存储配置")
    
    # 通知配置
    notification: NotificationConfig = Field(default_factory=NotificationConfig, description="通知配置")
    
    # 日志配置
    log_level: str = Field(default="INFO", description="日志级别")
    log_dir: str = Field(default="./outputs/logs", description="日志目录")
    log_retention_days: int = Field(default=30, description="日志保留天数")
    
    # Prefect 配置
    prefect_api_url: Optional[str] = Field(default=None, description="Prefect API URL")
    prefect_work_pool_name: Optional[str] = Field(default=None, description="Prefect Work Pool 名称")
    
    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """验证 base_url"""
        return v.rstrip("/")
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level 必须是 {valid_levels} 之一")
        return v.upper()
    
    @classmethod
    def from_env(cls) -> "DifyConfig":
        """从环境变量创建配置"""
        return cls(
            base_url=os.getenv("DIFY_BASE_URL", "http://localhost"),
            api_token=os.getenv("DIFY_API_TOKEN", ""),
            app_id=os.getenv("DIFY_APP_ID"),
            console_email=os.getenv("DIFY_CONSOLE_EMAIL"),
            console_password=os.getenv("DIFY_CONSOLE_PASSWORD"),
            console_token=os.getenv("DIFY_CONSOLE_TOKEN"),
            output_base_dir=os.getenv("OUTPUT_BASE_DIR", "./outputs"),
            storage=StorageConfig(
                type=os.getenv("STORAGE_TYPE", "local"),
                config={
                    "endpoint": os.getenv("OSS_ENDPOINT"),
                    "access_key_id": os.getenv("OSS_ACCESS_KEY_ID"),
                    "access_key_secret": os.getenv("OSS_ACCESS_KEY_SECRET"),
                    "bucket_name": os.getenv("OSS_BUCKET_NAME"),
                } if os.getenv("STORAGE_TYPE") == "oss" else {}
            ),
            notification=NotificationConfig(
                enabled=os.getenv("NOTIFICATION_ENABLED", "false").lower() == "true",
                type=os.getenv("NOTIFICATION_TYPE", "email"),
                config={
                    "smtp_host": os.getenv("SMTP_HOST"),
                    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
                    "smtp_user": os.getenv("SMTP_USER"),
                    "smtp_password": os.getenv("SMTP_PASSWORD"),
                    "smtp_to": os.getenv("SMTP_TO"),
                    "dingtalk_webhook": os.getenv("DINGTALK_WEBHOOK"),
                }
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_dir=os.getenv("LOG_DIR", "./outputs/logs"),
            log_retention_days=int(os.getenv("LOG_RETENTION_DAYS", "30")),
            prefect_api_url=os.getenv("PREFECT_API_URL"),
            prefect_work_pool_name=os.getenv("PREFECT_WORK_POOL_NAME"),
        )
    
    def get_output_dir(self, subdir: str = "") -> Path:
        """获取输出目录路径"""
        base = Path(self.output_base_dir)
        if subdir:
            return base / subdir
        return base
    
    def get_log_dir(self) -> Path:
        """获取日志目录路径"""
        return Path(self.log_dir)
    
    def ensure_dirs(self):
        """确保必要的目录存在"""
        self.get_output_dir().mkdir(parents=True, exist_ok=True)
        self.get_output_dir("logs").mkdir(parents=True, exist_ok=True)
        self.get_output_dir("reports").mkdir(parents=True, exist_ok=True)
        self.get_output_dir("data").mkdir(parents=True, exist_ok=True)
        self.get_log_dir().mkdir(parents=True, exist_ok=True)
