"""日志配置模块"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger
from prefect import get_run_logger as get_prefect_logger


def setup_logger(
    log_level: str = "INFO",
    log_dir: Optional[Path] = None,
    enable_file_logging: bool = True,
) -> None:
    """
    配置日志系统
    
    Args:
        log_level: 日志级别
        log_dir: 日志目录
        enable_file_logging: 是否启用文件日志
    """
    # 移除默认处理器
    logger.remove()
    
    # 控制台输出（带颜色）
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )
    
    # 文件输出（结构化）
    if enable_file_logging and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 主日志文件
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level=log_level,
            rotation="00:00",  # 每天午夜轮转
            retention="30 days",  # 保留30天
            compression="zip",  # 压缩旧日志
            encoding="utf-8",
        )
        
        # 错误日志文件
        logger.add(
            log_dir / "error_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level="ERROR",
            rotation="00:00",
            retention="30 days",
            compression="zip",
            encoding="utf-8",
        )


def get_logger(name: Optional[str] = None):
    """
    获取日志器
    
    Args:
        name: 日志器名称（可选）
    
    Returns:
        日志器实例
    """
    # 如果在 Prefect 环境中，尝试使用 Prefect 日志器
    try:
        prefect_logger = get_prefect_logger()
        if prefect_logger:
            return prefect_logger
    except Exception:
        pass
    
    # 否则使用 loguru
    if name:
        return logger.bind(name=name)
    return logger
