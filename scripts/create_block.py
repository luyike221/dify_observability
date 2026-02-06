"""创建和管理 Prefect Block 配置的辅助脚本"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.blocks.workflow_report_config import WorkflowReportConfig


def create_block(
    block_name: str,
    base_url: str,
    api_token: str,
    app_id: str = None,
    output_dir: str = "./outputs/reports/daily",
    output_format: str = "csv",
    **kwargs
):
    """
    创建或更新一个 WorkflowReportConfig Block
    
    Args:
        block_name: Block 名称（在 Prefect UI 中显示的名称）
        base_url: Dify API 基础 URL
        api_token: Dify 应用 API Token
        app_id: 应用 ID（可选）
        output_dir: 输出目录
        output_format: 输出格式
        **kwargs: 其他可选参数（fetch_all, with_details, with_node_executions 等）
    
    Example:
        create_block(
            block_name="daily-workflow-report-debug",
            base_url="http://localhost",
            api_token="app-R7kB8EZhzg4R8o2Li6FA4Dgb",
            app_id="5ac73990-ee17-4aba-993c-a473e2fa2a90",
            output_dir="./outputs/reports/daily",
        )
    """
    config = WorkflowReportConfig(
        base_url=base_url,
        api_token=api_token,
        app_id=app_id,
        output_dir=output_dir,
        output_format=output_format,
        **kwargs
    )
    
    # 保存 Block（如果已存在则更新）
    config.save(name=block_name, overwrite=True)
    print(f"✅ Block '{block_name}' 已创建/更新成功！")
    print(f"   在 Prefect UI 的 Blocks 页面可以查看和编辑此配置")


def create_default_blocks():
    """创建默认的 Block 配置（用于快速开始）"""
    
    print("=" * 60)
    print("创建默认 Block 配置")
    print("=" * 60)
    
    # 每日报告 Block（调试模式）
    print("\n1. 创建 daily-workflow-report-debug Block...")
    create_block(
        block_name="daily-workflow-report-debug",
        base_url="http://localhost",
        api_token="app-R7kB8EZhzg4R8o2Li6FA4Dgb",  # 请替换为你的实际 token
        app_id="5ac73990-ee17-4aba-993c-a473e2fa2a90",  # 请替换为你的实际 app_id
        output_dir="./outputs/reports/daily",
        output_format="csv",
        fetch_all=True,
        with_details=True,
        with_node_executions=True,
        notify_on_complete=True,
    )
    
    # 每周报告 Block
    print("\n2. 创建 weekly-workflow-report Block...")
    create_block(
        block_name="weekly-workflow-report",
        base_url="http://localhost",
        api_token="app-xxxxxxxxxxxxx",  # 请替换为你的实际 token
        app_id="your-app-id",  # 请替换为你的实际 app_id
        output_dir="./outputs/reports/weekly",
        output_format="csv",
        fetch_all=True,
        with_details=True,
        with_node_executions=True,
        notify_on_complete=True,
    )
    
    print("\n" + "=" * 60)
    print("✅ 默认 Block 配置创建完成！")
    print("=" * 60)
    print("\n⚠️  注意：请记得在 Prefect UI 中更新以下配置：")
    print("   - api_token: 替换为你的实际应用 API Token")
    print("   - app_id: 替换为你的实际应用 ID")
    print("   - base_url: 如果需要，更新为你的 Dify API 地址")
    print("\n📖 使用方法：")
    print("   1. 在 Prefect UI 的 Blocks 页面查看和编辑配置")
    print("   2. 在 deployment 文件中使用 config_name 参数引用 Block")
    print("   3. 新增应用时，只需在 UI 中创建新的 Block 实例")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="创建或更新 Prefect Block 配置")
    parser.add_argument(
        "--create-defaults",
        action="store_true",
        help="创建默认的 Block 配置（daily-workflow-report-debug 和 weekly-workflow-report）"
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Block 名称"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        help="Dify API 基础 URL"
    )
    parser.add_argument(
        "--api-token",
        type=str,
        help="Dify 应用 API Token"
    )
    parser.add_argument(
        "--app-id",
        type=str,
        default=None,
        help="应用 ID（可选）"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./outputs/reports/daily",
        help="输出目录（默认: ./outputs/reports/daily）"
    )
    parser.add_argument(
        "--output-format",
        type=str,
        default="csv",
        choices=["csv", "markdown", "json"],
        help="输出格式（默认: csv）"
    )
    
    args = parser.parse_args()
    
    if args.create_defaults:
        create_default_blocks()
    elif args.name and args.base_url and args.api_token:
        create_block(
            block_name=args.name,
            base_url=args.base_url,
            api_token=args.api_token,
            app_id=args.app_id,
            output_dir=args.output_dir,
            output_format=args.output_format,
        )
    else:
        parser.print_help()
        print("\n示例：")
        print("  创建默认 Block:")
        print("    uv run python scripts/create_block.py --create-defaults")
        print("\n  创建自定义 Block:")
        print("    uv run python scripts/create_block.py --name my-config --base-url http://localhost --api-token app-xxx")
