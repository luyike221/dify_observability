"""格式化工具函数"""

import json
from typing import Any, Optional
from datetime import datetime


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
            try:
                parsed = json.loads(obj)
                return decode_json_strings(parsed)
            except (json.JSONDecodeError, TypeError):
                return obj
        elif isinstance(obj, dict):
            return {k: decode_json_strings(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [decode_json_strings(item) for item in obj]
        else:
            return obj
    
    decoded_data = decode_json_strings(data)
    return json.dumps(decoded_data, ensure_ascii=False, indent=2)
