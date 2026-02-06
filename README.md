# Dify 工作流日志监控系统

基于 Prefect 的 Dify 工作流日志获取和报告生成系统。

## 功能特性

- ✅ 自动获取 Dify 工作流执行日志
- ✅ 支持详细信息获取（工作流运行详情、节点执行详情）
- ✅ 自动生成 CSV/Markdown/JSON 报告
- ✅ 基于 Prefect 的任务调度和监控
- ✅ 支持多种通知渠道（邮件、钉钉）
- ✅ 结构化日志和错误追踪
- ✅ 配置管理和环境变量支持

## 快速开始

### 前置要求

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) - 快速 Python 包管理器

安装 uv：
```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv
```

### 1. 安装依赖

使用 uv 安装项目依赖：

```bash
# 安装项目及其依赖
uv sync

# 或仅安装依赖（不创建虚拟环境）
uv pip install -e .
```

> **注意**: 如果仍需要使用 `requirements.txt`，可以使用 `uv pip install -r requirements.txt`

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 3. 启动 Prefect Server

```bash
# 方式 1: 直接启动（开发环境）
prefect server start

# 方式 2: Docker Compose（生产环境）
# 参考 Prefect 官方文档
```

### 4. 设置 Prefect 环境

```bash
chmod +x scripts/setup_prefect.sh
./scripts/setup_prefect.sh
```

### 5. 启动 Worker

```bash
prefect worker start --pool dify-workflow-pool
```

### 6. 部署任务

```bash
# 使用 uv 运行（推荐）
uv run python deployments/daily_report.py
uv run python deployments/weekly_report.py

# 或激活虚拟环境后运行
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows
python deployments/daily_report.py
python deployments/weekly_report.py
```

## 使用方式

### 方式 1: Prefect Flow（推荐）

通过 Prefect UI 或 API 触发任务：

```python
from src.flows.workflow_log_flow import fetch_workflow_logs_flow

# 手动触发
result = fetch_workflow_logs_flow(
    created_at_after="2024-01-01T00:00:00Z",
    created_at_before="2024-01-31T23:59:59Z",
    output_format="csv",
    with_details=True,
    with_node_executions=True,
)
```

### 方式 2: 命令行（向后兼容）

保留原有的命令行脚本作为备用：

```bash
# 使用 uv 运行（推荐）
uv run python fetch_workflow_logs.py \
  --api-token app-xxx \
  --base-url http://localhost \
  --with-details \
  --with-node-executions \
  --console-email your@email.com \
  --console-password your-password \
  --app-id your-app-id \
  --output-csv-dir ./outputs

# 或激活虚拟环境后运行
python fetch_workflow_logs.py \
  --api-token app-xxx \
  --base-url http://localhost \
  --with-details \
  --with-node-executions \
  --console-email your@email.com \
  --console-password your-password \
  --app-id your-app-id \
  --output-csv-dir ./outputs
```

## 配置说明

### 环境变量

主要配置项：

- `DIFY_BASE_URL`: Dify API 基础 URL
- `DIFY_API_TOKEN`: 应用 API Token
- `DIFY_APP_ID`: 应用 ID
- `DIFY_CONSOLE_EMAIL`: Console 登录邮箱（可选）
- `DIFY_CONSOLE_PASSWORD`: Console 登录密码（可选）
- `NOTIFICATION_ENABLED`: 是否启用通知
- `NOTIFICATION_TYPE`: 通知类型（email/dingtalk）

详细配置见 `.env.example`。

### Prefect 配置

- `PREFECT_API_URL`: Prefect API URL（默认: http://localhost:4200/api）
- `PREFECT_WORK_POOL_NAME`: Work Pool 名称（默认: dify-workflow-pool）

## 目录结构

```
01-dify运维监控/
├── src/                    # 源代码
│   ├── core/              # 核心模块（配置、日志、异常）
│   ├── services/          # 业务服务（获取、报告、存储、通知）
│   ├── utils/             # 工具函数（重试、校验、格式化）
│   └── flows/             # Prefect Flow 和 Task
├── deployments/            # Deployment 配置
├── scripts/                # 部署脚本
├── outputs/                # 输出目录
│   ├── logs/              # 日志文件
│   ├── reports/            # 生成的报告
│   └── data/               # 原始数据备份
├── pyproject.toml          # 项目配置和依赖（uv）
├── requirements.txt        # Python 依赖（向后兼容）
├── .env.example            # 环境变量模板
└── README.md               # 本文档
```

## 报告格式

系统会生成以下 CSV 报告：

1. **问答类应用数-总览.csv**: 整体统计信息
2. **问答类应用数-每日消息数.csv**: 每日消息统计
3. **问答类应用数-用户列表.csv**: 用户使用统计
4. **问答类应用数-用户问答对.csv**: 详细的问答对数据

## 监控和日志

### Prefect UI

访问 http://localhost:4200 查看：
- 任务执行状态
- 执行历史记录
- 参数配置
- 日志查看

### 日志文件

日志文件保存在 `outputs/logs/` 目录：
- `app_YYYY-MM-DD.log`: 主日志文件
- `error_YYYY-MM-DD.log`: 错误日志文件

## 故障排查

### 1. Prefect Server 无法连接

```bash
# 检查 Server 是否运行
curl http://localhost:4200/api/health

# 重启 Server
prefect server start
```

### 2. Worker 无法启动

```bash
# 检查 Work Pool 是否存在
prefect work-pool ls

# 创建 Work Pool
prefect work-pool create dify-workflow-pool --type process
```

### 3. 任务执行失败

- 检查环境变量配置是否正确
- 检查 Dify API 是否可访问
- 查看 Prefect UI 中的错误日志
- 查看 `outputs/logs/error_*.log` 文件

### 4. uv 相关问题

```bash
# 检查 uv 是否安装
uv --version

# 重新同步依赖
uv sync --reinstall

# 清理缓存
uv cache clean
```

## 开发指南

### 依赖管理（uv）

使用 uv 管理项目依赖：

```bash
# 添加新依赖
uv add package-name

# 添加开发依赖
uv add --dev package-name

# 添加可选依赖组
uv add --optional storage oss2

# 移除依赖
uv remove package-name

# 更新所有依赖
uv sync --upgrade

# 查看依赖树
uv tree
```

依赖会自动更新到 `pyproject.toml` 文件中。

### 添加新的报告格式

1. 在 `src/services/reporter.py` 中添加新的生成方法
2. 在 `src/flows/tasks/report_task.py` 中添加对应的处理逻辑
3. 更新 `fetch_workflow_logs_flow` 的参数说明

### 添加新的通知渠道

1. 在 `src/services/notifier.py` 中实现新的通知服务类
2. 在 `create_notification_service` 函数中添加创建逻辑
3. 更新 `.env.example` 添加相应配置项

## 许可证

本项目遵循项目主仓库的许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！
# dify_observability
