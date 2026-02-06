"""存储服务"""

import os
from pathlib import Path
from typing import List, Optional
from abc import ABC, abstractmethod

from src.core.exceptions import DifyStorageError
from src.core.logger import get_logger

logger = get_logger(__name__)


class StorageService(ABC):
    """存储服务抽象基类"""
    
    @abstractmethod
    def save_report(self, content: bytes, filename: str, report_type: str) -> str:
        """保存报告文件"""
        pass
    
    @abstractmethod
    def save_data(self, data: dict, filename: str) -> str:
        """保存数据文件"""
        pass
    
    @abstractmethod
    def list_reports(self, report_type: str, days: int = 30) -> List[str]:
        """列出报告文件"""
        pass
    
    @abstractmethod
    def cleanup_old_files(self, days: int) -> int:
        """清理旧文件"""
        pass


class LocalStorageService(StorageService):
    """本地文件存储服务"""
    
    def __init__(self, base_dir: str = "./outputs"):
        """
        初始化本地存储服务
        
        Args:
            base_dir: 基础目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def save_report(self, content: bytes, filename: str, report_type: str) -> str:
        """保存报告文件"""
        report_dir = self.base_dir / "reports" / report_type
        report_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = report_dir / filename
        file_path.write_bytes(content)
        
        logger.info(f"报告已保存: {file_path}")
        return str(file_path)
    
    def save_data(self, data: dict, filename: str) -> str:
        """保存数据文件"""
        import json
        
        data_dir = self.base_dir / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = data_dir / filename
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        logger.info(f"数据已保存: {file_path}")
        return str(file_path)
    
    def list_reports(self, report_type: str, days: int = 30) -> List[str]:
        """列出报告文件"""
        report_dir = self.base_dir / "reports" / report_type
        if not report_dir.exists():
            return []
        
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        
        reports = []
        for file_path in report_dir.iterdir():
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime >= cutoff_date:
                    reports.append(str(file_path))
        
        return sorted(reports)
    
    def cleanup_old_files(self, days: int) -> int:
        """清理旧文件"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        for dir_path in [self.base_dir / "reports", self.base_dir / "data"]:
            if not dir_path.exists():
                continue
            
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_date:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug(f"已删除旧文件: {file_path}")
        
        logger.info(f"已清理 {cleaned_count} 个旧文件")
        return cleaned_count


def create_storage_service(storage_type: str = "local", **kwargs) -> StorageService:
    """
    创建存储服务实例
    
    Args:
        storage_type: 存储类型 (local/oss/s3)
        **kwargs: 存储服务配置参数
    
    Returns:
        存储服务实例
    """
    if storage_type == "local":
        base_dir = kwargs.get("base_dir", "./outputs")
        return LocalStorageService(base_dir=base_dir)
    elif storage_type == "oss":
        # TODO: 实现 OSS 存储服务
        raise NotImplementedError("OSS 存储服务尚未实现")
    elif storage_type == "s3":
        # TODO: 实现 S3 存储服务
        raise NotImplementedError("S3 存储服务尚未实现")
    else:
        raise ValueError(f"不支持的存储类型: {storage_type}")
