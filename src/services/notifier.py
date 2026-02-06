"""通知服务"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import requests

from src.core.exceptions import DifyNotificationError
from src.core.logger import get_logger

logger = get_logger(__name__)


class NotificationService(ABC):
    """通知服务抽象基类"""
    
    @abstractmethod
    def notify_success(self, task_name: str, result: Dict[str, Any]) -> bool:
        """通知任务成功"""
        pass
    
    @abstractmethod
    def notify_failure(self, task_name: str, error: Exception) -> bool:
        """通知任务失败"""
        pass
    
    @abstractmethod
    def notify_report_ready(self, report_path: str, report_type: str) -> bool:
        """通知报告已生成"""
        pass


class EmailNotificationService(NotificationService):
    """邮件通知服务"""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        smtp_to: str,
    ):
        """
        初始化邮件通知服务
        
        Args:
            smtp_host: SMTP 服务器地址
            smtp_port: SMTP 端口
            smtp_user: SMTP 用户名
            smtp_password: SMTP 密码
            smtp_to: 收件人邮箱
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.smtp_to = smtp_to
    
    def _send_email(self, subject: str, body: str) -> bool:
        """发送邮件"""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.smtp_user
            msg["To"] = self.smtp_to
            msg["Subject"] = subject
            
            msg.attach(MIMEText(body, "plain", "utf-8"))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"邮件已发送: {subject}")
            return True
        except Exception as e:
            logger.error(f"发送邮件失败: {str(e)}")
            return False
    
    def notify_success(self, task_name: str, result: Dict[str, Any]) -> bool:
        """通知任务成功"""
        subject = f"✅ {task_name} 执行成功"
        body = f"""
任务名称: {task_name}
执行状态: 成功

结果摘要:
{result.get('summary', '无')}
        """
        return self._send_email(subject, body)
    
    def notify_failure(self, task_name: str, error: Exception) -> bool:
        """通知任务失败"""
        subject = f"❌ {task_name} 执行失败"
        body = f"""
任务名称: {task_name}
执行状态: 失败

错误信息:
{str(error)}
        """
        return self._send_email(subject, body)
    
    def notify_report_ready(self, report_path: str, report_type: str) -> bool:
        """通知报告已生成"""
        subject = f"📊 {report_type} 报告已生成"
        body = f"""
报告类型: {report_type}
报告路径: {report_path}

报告已成功生成，请查看。
        """
        return self._send_email(subject, body)


class DingTalkNotificationService(NotificationService):
    """钉钉通知服务"""
    
    def __init__(self, webhook_url: str):
        """
        初始化钉钉通知服务
        
        Args:
            webhook_url: 钉钉机器人 Webhook URL
        """
        self.webhook_url = webhook_url
    
    def _send_message(self, title: str, content: str) -> bool:
        """发送钉钉消息"""
        try:
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": title,
                    "text": f"## {title}\n\n{content}",
                },
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"钉钉消息已发送: {title}")
            return True
        except Exception as e:
            logger.error(f"发送钉钉消息失败: {str(e)}")
            return False
    
    def notify_success(self, task_name: str, result: Dict[str, Any]) -> bool:
        """通知任务成功"""
        title = f"✅ {task_name} 执行成功"
        content = f"**任务名称**: {task_name}\n\n**执行状态**: 成功\n\n**结果摘要**: {result.get('summary', '无')}"
        return self._send_message(title, content)
    
    def notify_failure(self, task_name: str, error: Exception) -> bool:
        """通知任务失败"""
        title = f"❌ {task_name} 执行失败"
        content = f"**任务名称**: {task_name}\n\n**执行状态**: 失败\n\n**错误信息**: {str(error)}"
        return self._send_message(title, content)
    
    def notify_report_ready(self, report_path: str, report_type: str) -> bool:
        """通知报告已生成"""
        title = f"📊 {report_type} 报告已生成"
        content = f"**报告类型**: {report_type}\n\n**报告路径**: {report_path}\n\n报告已成功生成，请查看。"
        return self._send_message(title, content)


def create_notification_service(
    notification_type: str = "email",
    **kwargs
) -> Optional[NotificationService]:
    """
    创建通知服务实例
    
    Args:
        notification_type: 通知类型 (email/dingtalk/wechat)
        **kwargs: 通知服务配置参数
    
    Returns:
        通知服务实例，如果配置无效则返回 None
    """
    if notification_type == "email":
        required_keys = ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "smtp_to"]
        if all(key in kwargs for key in required_keys):
            return EmailNotificationService(
                smtp_host=kwargs["smtp_host"],
                smtp_port=kwargs["smtp_port"],
                smtp_user=kwargs["smtp_user"],
                smtp_password=kwargs["smtp_password"],
                smtp_to=kwargs["smtp_to"],
            )
        else:
            logger.warning("邮件通知配置不完整，跳过通知")
            return None
    elif notification_type == "dingtalk":
        if "webhook_url" in kwargs:
            return DingTalkNotificationService(webhook_url=kwargs["webhook_url"])
        else:
            logger.warning("钉钉通知配置不完整，跳过通知")
            return None
    elif notification_type == "wechat":
        # TODO: 实现企业微信通知服务
        logger.warning("企业微信通知服务尚未实现")
        return None
    else:
        logger.warning(f"不支持的通知类型: {notification_type}")
        return None
