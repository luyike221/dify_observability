#!/usr/bin/env python3
"""
    用途：测试脚本 - 手动运行 Flow 进行测试（不触发定时任务）
    命令：uv run python test_flow.py
"""

from datetime import datetime
from src.flows.workflow_log_flow import fetch_workflow_logs_flow


if __name__ == "__main__":
    print("=" * 60)
    print("开始测试 Flow（不触发定时任务）")
    print("=" * 60)
    
    # 配置参数（从 deployments/daily_report.py 复制）
    base_url = "http://localhost"
    api_token = "app-R7kB8EZhzg4R8o2Li6FA4Dgb"
    app_id = "5ac73990-ee17-4aba-993c-a473e2fa2a90"
    
    # 时间范围（暂时不限制，查询所有时间段）
    # created_at_after = None
    # created_at_before = None
    
    # 直接调用 Flow 函数
    result = fetch_workflow_logs_flow(
        # 应用配置
        base_url=base_url,
        api_token=api_token,
        app_id=app_id,
        
        # 时间范围（不传入，查询所有时间段）
        # created_at_after=created_at_after,
        # created_at_before=created_at_before,
        
        # 输出配置
        output_format="csv",
        output_dir="./outputs/reports/test",
        
        # 功能开关
        fetch_all=True,
        with_details=True,
        with_node_executions=True,
        notify_on_complete=False,  # 测试时不发送通知
        
        # 限制数量（测试时可以减少）
        limit=20,
        max_pages=5,  # 最多5页，避免测试时间过长
    )
    
    print("=" * 60)
    print("测试完成！")
    print("=" * 60)
    if isinstance(result, dict):
        print(f"获取日志数: {len(result.get('data', []))}")
        print(f"报告文件: {result.get('report_files', [])}")
        print(f"输出目录: ./outputs/reports/test")
    else:
        print(f"结果类型: {type(result)}")
        print(f"结果内容: {result}")
