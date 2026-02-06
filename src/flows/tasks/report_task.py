"""生成报告 Task"""

from typing import Any, Dict, List
from prefect import task
from pathlib import Path

from src.services.reporter import ReportGenerator
from src.core.logger import get_logger

logger = get_logger(__name__)


@task(name="generate-reports")
def generate_reports_task(
    logs_result: Dict[str, Any],
    output_dir: str,
    output_format: str = "csv",
) -> Dict[str, Any]:
    """
    生成报告任务
    
    Args:
        logs_result: 日志数据结果
        output_dir: 输出目录
        output_format: 输出格式 (csv/markdown/json)
    
    Returns:
        报告生成结果
    """
    logger.info(f"开始生成 {output_format} 报告")
    
    reporter = ReportGenerator(output_dir=output_dir)
    report_files = []
    
    if output_format == "csv":
        report_files = reporter.generate_csv_reports(logs_result)
    elif output_format == "markdown":
        md_content = reporter.generate_markdown_report(logs_result, include_details=True)
        md_file = Path(output_dir) / f"logs_report_{logs_result.get('total', 0)}.md"
        md_file.write_text(md_content, encoding="utf-8")
        report_files = [str(md_file)]
    elif output_format == "json":
        import json
        json_file = Path(output_dir) / f"logs_data_{logs_result.get('total', 0)}.json"
        json_file.write_text(
            json.dumps(logs_result, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        report_files = [str(json_file)]
    else:
        logger.warning(f"不支持的输出格式: {output_format}")
    
    logger.info(f"成功生成 {len(report_files)} 个报告文件")
    
    return {
        "report_files": report_files,
        "report_count": len(report_files),
        "logs_count": len(logs_result.get("data", [])),
    }
