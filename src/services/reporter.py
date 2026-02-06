"""报告生成服务"""

import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from src.core.logger import get_logger
from src.utils.formatters import format_timestamp

logger = get_logger(__name__)


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_csv_reports(self, result: Dict[str, Any]) -> List[str]:
        """
        生成 CSV 报告文件
        
        Args:
            result: 日志数据结果
        
        Returns:
            生成的报告文件路径列表
        """
        logs = result.get("data", [])
        if not logs:
            logger.warning("没有日志数据，无法生成 CSV 报告")
            return []
        
        # 提取数据
        qa_pairs = []
        user_stats = defaultdict(lambda: {
            "message_count": 0,
            "first_date": None,
            "last_date": None,
            "dates": set()
        })
        daily_stats = defaultdict(int)
        total_tokens = 0
        total_cost = 0.0
        session_ids = set()
        session_qa_map = defaultdict(list)
        
        # 处理每条日志
        for idx, log in enumerate(logs, 1):
            workflow_run = log.get("workflow_run", {})
            run_detail = log.get("workflow_run_detail", {})
            node_executions = log.get("node_executions", [])
            
            # 获取基本信息
            created_at = log.get("created_at")
            if created_at:
                date_str = format_timestamp(created_at).split()[0]
                daily_stats[date_str] += 1
            
            # 获取用户ID
            user_id = None
            created_by_account = log.get("created_by_account", {})
            created_by_end_user = log.get("created_by_end_user", {})
            if created_by_end_user:
                user_id = created_by_end_user.get("session_id")
            elif created_by_account:
                user_id = created_by_account.get("email")
            
            if not user_id and run_detail:
                inputs = run_detail.get("inputs", {})
                if isinstance(inputs, str):
                    try:
                        inputs = json.loads(inputs)
                    except (json.JSONDecodeError, TypeError):
                        inputs = {}
                elif not isinstance(inputs, dict):
                    inputs = {}
                user_id = inputs.get("sys.user_id") or inputs.get("sys", {}).get("user_id")
            
            # 获取会话ID
            session_id = workflow_run.get("id") or log.get("id")
            if session_id:
                session_ids.add(session_id)
            
            # 获取用户提问和AI回答
            user_query = ""
            ai_answer = ""
            attachments = []
            # 不使用去重，直接按顺序存储所有查到的内容（包括重复）
            # 每个片段都单独记录，保持原始顺序
            segments_list = []  # 存储所有片段，格式: (知识库名称, 文档名称, 片段内容, 相似度)
            
            if run_detail:
                # 处理 inputs
                inputs = run_detail.get("inputs", {})
                if isinstance(inputs, str):
                    try:
                        inputs = json.loads(inputs)
                    except (json.JSONDecodeError, TypeError):
                        inputs = {}
                elif not isinstance(inputs, dict):
                    inputs = {}
                
                # 处理 outputs
                outputs = run_detail.get("outputs", {})
                if isinstance(outputs, str):
                    try:
                        outputs = json.loads(outputs)
                    except (json.JSONDecodeError, TypeError):
                        outputs = {}
                elif not isinstance(outputs, dict):
                    outputs = {}
                
                user_query = inputs.get("query") or inputs.get("sys.query", "") or ""
                ai_answer = outputs.get("text", "") or ""
                
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
                                
                                # 不去重，直接记录所有查到的内容（包括重复）
                                if dataset_name and document_name and content:
                                    clean_dataset = dataset_name.replace("...", "").strip()
                                    clean_document = document_name.replace("...", "").strip()
                                    
                                    # 相似度和文本内容换行显示
                                    segment_text = f"相似度:{score:.4f}\n{content[:200]}"
                                    
                                    # 直接追加，不去重
                                    segments_list.append((clean_dataset, clean_document, segment_text))
            
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
                            if isinstance(price, str):
                                try:
                                    price = float(price)
                                except (ValueError, TypeError):
                                    price = 0
                            elif not isinstance(price, (int, float)):
                                price = 0
                            total_cost += price
            
            # 构建问答对：按知识库和文档组合展开为多行
            # 不去重，直接按查到的内容显示（包括重复）
            if not segments_list:
                # 没有知识库的情况，生成一行空数据
                qa_data = {
                    "序号": idx,
                    "用户id": user_id or "",
                    "会话id": session_id or "",
                    "问题排序": 1,
                    "用户提问": user_query,
                    "附件名称": "; ".join(attachments) if attachments else "",
                    "AI回答": ai_answer[:5000] if len(ai_answer) > 5000 else ai_answer,
                    "知识库名称": "",
                    "引用的文档名称": "",
                    "创建时间": format_timestamp(created_at) if created_at else "",
                    "created_at": created_at,
                }
                if session_id:
                    session_qa_map[session_id].append(qa_data)
                else:
                    qa_pairs.append(qa_data)
            else:
                # 按知识库和文档组合分组（但不去重，每个组合可能有多个片段）
                # 使用字典按 (知识库, 文档) 分组，但保留所有片段（包括重复）
                kb_doc_segments = {}  # {(知识库, 文档): [片段列表]}
                
                for kb_name, doc_name, segment_text in segments_list:
                    kb_doc_key = (kb_name, doc_name)
                    if kb_doc_key not in kb_doc_segments:
                        kb_doc_segments[kb_doc_key] = []
                    kb_doc_segments[kb_doc_key].append(segment_text)
                
                # 为每个知识库-文档组合创建一行
                for (kb_name, doc_name), doc_segments in kb_doc_segments.items():
                    # 动态生成文本片段列（每个片段一列）
                    qa_data = {
                        "序号": idx,
                        "用户id": user_id or "",
                        "会话id": session_id or "",
                        "问题排序": 1,
                        "用户提问": user_query,
                        "附件名称": "; ".join(attachments) if attachments else "",
                        "AI回答": ai_answer[:5000] if len(ai_answer) > 5000 else ai_answer,
                        "知识库名称": kb_name,
                        "引用的文档名称": doc_name,
                        "创建时间": format_timestamp(created_at) if created_at else "",
                        "created_at": created_at,
                    }
                    
                    # 动态添加文本片段列（每个片段一列，不去重）
                    for i, segment in enumerate(doc_segments, 1):
                        qa_data[f"文本片段内容{i}"] = segment
                    
                    if session_id:
                        session_qa_map[session_id].append(qa_data)
                    else:
                        qa_pairs.append(qa_data)
        
        # 按会话ID分组，计算问题排序
        for session_id, session_qas in session_qa_map.items():
            session_qas.sort(key=lambda x: x.get("created_at") or 0)
            for order, qa in enumerate(session_qas, 1):
                qa["问题排序"] = order
                qa.pop("created_at", None)
                qa_pairs.append(qa)
        
        qa_pairs.sort(key=lambda x: x["序号"])
        
        report_files = []
        
        # 1. 生成总览 CSV
        overview_file = self.output_dir / "问答类应用数-总览.csv"
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
                
                total_time = sum(log.get("workflow_run", {}).get("elapsed_time", 0) for log in logs if log.get("workflow_run", {}).get("elapsed_time"))
                token_speed = total_tokens / total_time if total_time > 0 else 0
                
                writer.writerow([
                    start_date, end_date, total_messages, total_users, total_sessions,
                    f"{avg_interactions:.2f}", f"{token_speed:.2f} tokens/秒", "", f"{total_cost:.6f}",
                ])
            else:
                writer.writerow([""] * 9)
        
        report_files.append(str(overview_file))
        
        # 2. 生成每日消息数 CSV
        daily_file = self.output_dir / "问答类应用数-每日消息数.csv"
        with open(daily_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["日期", "消息数量"])
            for date_str in sorted(daily_stats.keys()):
                writer.writerow([date_str, daily_stats[date_str]])
        
        report_files.append(str(daily_file))
        
        # 3. 生成用户列表 CSV
        user_list_file = self.output_dir / "问答类应用数-用户列表.csv"
        with open(user_list_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["用户ID", "消息数", "使用天数", "首次使用日期", "最后使用日期"])
            for user_id, stats in sorted(user_stats.items(), key=lambda x: x[1]["message_count"], reverse=True):
                use_days = len(stats["dates"])
                first_date = stats["first_date"].strftime("%Y-%m-%d") if stats["first_date"] else ""
                last_date = stats["last_date"].strftime("%Y-%m-%d") if stats["last_date"] else ""
                writer.writerow([user_id, stats["message_count"], use_days, first_date, last_date])
        
        report_files.append(str(user_list_file))
        
        # 4. 生成用户问答对 CSV
        # 先统计所有问答对中，每个知识库-文档组合最多有多少个文本片段
        max_segments = 0
        for qa in qa_pairs:
            # 统计该行有多少个文本片段列
            segment_count = 0
            for key in qa.keys():
                if key.startswith("文本片段内容"):
                    try:
                        num = int(key.replace("文本片段内容", ""))
                        segment_count = max(segment_count, num)
                    except ValueError:
                        pass
            max_segments = max(max_segments, segment_count)
        
        # 至少要有3列（文本片段内容1、2、N），如果超过3个，则动态增加列
        max_segments = max(max_segments, 3)
        
        # 构建列名
        base_columns = [
            "序号", "用户id", "会话id", "问题排序（同一个会话ID，提问先后顺序）",
            "用户提问", "附件名称：名称.后缀", "AI回答", "知识库名称", "引用的文档名称",
        ]
        # 动态生成文本片段列名
        segment_columns = [f"文本片段内容{i}（相似度+文本内容）" for i in range(1, max_segments + 1)]
        all_columns = base_columns + segment_columns + ["创建时间"]
        
        qa_file = self.output_dir / "问答类应用数-用户问答对.csv"
        with open(qa_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([""] * len(all_columns))
            writer.writerow(all_columns)
            writer.writerow([""] * len(all_columns))
            
            for qa in qa_pairs:
                row = [
                    qa.get("序号", ""),
                    qa.get("用户id", ""),
                    qa.get("会话id", ""),
                    qa.get("问题排序", ""),
                    qa.get("用户提问", ""),
                    qa.get("附件名称", ""),
                    qa.get("AI回答", ""),
                    qa.get("知识库名称", ""),
                    qa.get("引用的文档名称", ""),
                ]
                # 动态填充文本片段列
                for i in range(1, max_segments + 1):
                    row.append(qa.get(f"文本片段内容{i}", ""))
                row.append(qa.get("创建时间", ""))
                writer.writerow(row)
            
            writer.writerow([""] * len(all_columns))
            writer.writerow(["注：此处区分是否可上传附件、是否引用RAG知识库，若无内容，为空即可。"] + [""] * (len(all_columns) - 1))
            writer.writerow([""] * len(all_columns))
        
        report_files.append(str(qa_file))
        
        logger.info(f"CSV 报告已生成: {len(report_files)} 个文件")
        return report_files
    
    def generate_markdown_report(self, result: Dict[str, Any], include_details: bool = False) -> str:
        """
        生成 Markdown 格式的报告
        
        Args:
            result: 日志数据结果
            include_details: 是否包含详细信息
        
        Returns:
            Markdown 报告内容
        """
        from src.utils.formatters import format_json_for_markdown
        
        md_lines = []
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
        
        # 详细日志（如果包含）
        if include_details:
            md_lines.append("## 📋 日志详情")
            md_lines.append("")
            
            for i, log in enumerate(logs, 1):
                log_id = log.get("id", "N/A")
                workflow_run = log.get("workflow_run", {})
                
                md_lines.append(f"### {i}. 日志 ID: `{log_id}`")
                md_lines.append("")
                md_lines.append("#### 基本信息")
                md_lines.append("")
                md_lines.append("| 字段 | 值 |")
                md_lines.append("|------|-----|")
                md_lines.append(f"| 日志ID | `{log_id}` |")
                md_lines.append(f"| 状态 | {workflow_run.get('status', 'N/A')} |")
                md_lines.append(f"| 创建时间 | {format_timestamp(log.get('created_at'))} |")
                md_lines.append(f"| 耗时 | {workflow_run.get('elapsed_time', 0):.2f} 秒 |")
                md_lines.append("")
                
                # 工作流运行详情
                run_detail = log.get("workflow_run_detail")
                if run_detail:
                    md_lines.append("#### 工作流运行详情")
                    md_lines.append("")
                    if run_detail.get("inputs"):
                        md_lines.append("##### 输入参数")
                        md_lines.append("")
                        md_lines.append("```json")
                        md_lines.append(format_json_for_markdown(run_detail.get("inputs")))
                        md_lines.append("```")
                        md_lines.append("")
                    
                    if run_detail.get("outputs"):
                        md_lines.append("##### 输出结果")
                        md_lines.append("")
                        md_lines.append("```json")
                        md_lines.append(format_json_for_markdown(run_detail.get("outputs")))
                        md_lines.append("```")
                        md_lines.append("")
                
                if i < len(logs):
                    md_lines.append("---")
                    md_lines.append("")
        
        return "\n".join(md_lines)
