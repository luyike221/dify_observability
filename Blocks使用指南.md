# Prefect Blocks 使用指南

## 概述

本项目已迁移到使用 Prefect Blocks 来管理配置，这样可以：
- ✅ 在 Prefect UI 中直接管理配置，无需修改代码
- ✅ 为不同应用创建不同的 Block 实例
- ✅ 新增应用时只需在 UI 中创建新 Block，无需重新部署
- ✅ 配置变更即时生效

## 快速开始

### 1. 创建 Block（方式一：使用脚本）

使用提供的脚本快速创建默认 Block：

```bash
uv run python scripts/create_block.py --create-defaults
```

这会创建两个默认 Block：
- `daily-workflow-report-debug` - 每日报告配置（调试模式）
- `weekly-workflow-report` - 每周报告配置

### 2. 创建 Block（方式二：在 Prefect UI 中）

1. 打开 Prefect UI（通常是 http://localhost:4200）
2. 点击左侧菜单的 **Blocks**
3. 点击 **+ Create** 按钮
4. 在搜索框输入 `Workflow Report Config` 或 `workflow-report-config`
5. 填写配置字段：
   - **Block Name**: 例如 `daily-workflow-report-debug`
   - **base_url**: Dify API 基础 URL（例如：`http://localhost`）
   - **api_token**: 应用 API Token（例如：`app-R7kB8EZhzg4R8o2Li6FA4Dgb`）
   - **app_id**: 应用 ID（可选）
   - **output_format**: 输出格式（`csv` / `markdown` / `json`）
   - **output_dir**: 输出目录（例如：`./outputs/reports/daily`）
   - **fetch_all**: 是否获取所有日志（`true` / `false`）
   - **with_details**: 是否获取详细信息（`true` / `false`）
   - **with_node_executions**: 是否包含节点执行详情（`true` / `false`）
   - **notify_on_complete**: 是否在完成时发送通知（`true` / `false`）
6. 点击 **Create** 保存

### 3. 在 Deployment 中使用 Block

在 `deployments/daily_report.py` 中，只需传入 `config_name`：

```python
fetch_workflow_logs_flow.serve(
    name="daily-workflow-report-debug",
    schedule=Interval(timedelta(seconds=30)),
    parameters={
        "config_name": "daily-workflow-report-debug",  # 引用 Block 名称
    },
    tags=["daily", "report", "workflow", "debug"],
)
```

## 配置字段说明

### 必需字段

- **base_url**: Dify API 基础 URL
- **api_token**: Dify 应用 API Token（`app-xxx` 格式）

### 可选字段

- **app_id**: 应用 ID（用于获取应用详情）
- **console_token**: Console API Token（可选）
- **console_email**: Console 登录邮箱（可选）
- **console_password**: Console 登录密码（可选）
- **output_format**: 输出格式，默认 `csv`
- **output_dir**: 输出目录，默认 `./outputs/reports/daily`
- **fetch_all**: 是否获取所有日志，默认 `true`
- **with_details**: 是否获取详细信息，默认 `true`
- **with_node_executions**: 是否包含节点执行详情，默认 `true`
- **notify_on_complete**: 是否在完成时发送通知，默认 `true`
- **limit**: 每页数量限制，默认 `20`
- **max_pages**: 最大页数限制（`null` 表示不限制）

## 使用场景

### 场景 1：多应用配置

如果你有多个 Dify 应用需要监控：

1. 为每个应用创建一个 Block：
   - `app-prod-config` - 生产环境应用
   - `app-staging-config` - 测试环境应用
   - `app-dev-config` - 开发环境应用

2. 创建对应的 Deployment，每个引用不同的 Block：
   ```python
   # deployment_app_prod.py
   fetch_workflow_logs_flow.serve(
       name="app-prod-report",
       parameters={"config_name": "app-prod-config"},
   )
   
   # deployment_app_staging.py
   fetch_workflow_logs_flow.serve(
       name="app-staging-report",
       parameters={"config_name": "app-staging-config"},
   )
   ```

### 场景 2：覆盖 Block 配置

如果需要临时覆盖 Block 中的某些配置，可以在 Deployment 的 `parameters` 中传入：

```python
fetch_workflow_logs_flow.serve(
    name="daily-workflow-report-debug",
    parameters={
        "config_name": "daily-workflow-report-debug",
        "output_dir": "./outputs/reports/daily-custom",  # 覆盖 Block 中的 output_dir
        "created_at_after": "2024-01-01T00:00:00Z",  # 添加时间范围
    },
)
```

### 场景 3：环境隔离

为不同环境创建不同的 Block：
- `daily-report-dev` - 开发环境
- `daily-report-staging` - 测试环境
- `daily-report-prod` - 生产环境

每个 Block 配置不同的 `base_url`、`api_token` 和 `output_dir`。

## 管理 Block

### 查看所有 Block

在 Prefect UI 的 Blocks 页面可以查看所有已创建的 Block。

### 编辑 Block

1. 在 Blocks 页面找到要编辑的 Block
2. 点击 Block 名称进入详情页
3. 点击 **Edit** 按钮
4. 修改配置后点击 **Save**

### 删除 Block

1. 在 Blocks 页面找到要删除的 Block
2. 点击 Block 名称进入详情页
3. 点击 **Delete** 按钮

⚠️ **注意**：删除 Block 后，引用该 Block 的 Deployment 将无法运行。

## 命令行工具

### 创建默认 Block

```bash
uv run python scripts/create_block.py --create-defaults
```

### 创建自定义 Block

```bash
uv run python scripts/create_block.py \
    --name my-config \
    --base-url http://localhost \
    --api-token app-xxxxxxxxxxxxx \
    --app-id your-app-id \
    --output-dir ./outputs/reports/custom \
    --output-format csv
```

## 向后兼容

Flow 仍然支持直接传入参数的方式（不使用 Block），这样可以保持向后兼容：

```python
fetch_workflow_logs_flow.serve(
    name="legacy-deployment",
    parameters={
        "base_url": "http://localhost",
        "api_token": "app-xxx",
        # ... 其他参数
    },
)
```

但推荐使用 Block 方式，因为：
- 配置集中管理
- 易于维护
- 支持多应用场景

## 最佳实践

1. **命名规范**：使用有意义的 Block 名称，例如 `{app-name}-{env}-config`
2. **敏感信息**：API tokens 等敏感信息存储在 Block 中，Prefect 会自动加密
3. **版本管理**：虽然 Block 没有版本控制，但可以通过命名区分，例如 `app-prod-config-v2`
4. **权限控制**：限制 Prefect UI 的访问权限，只允许授权人员修改 Block
5. **文档化**：在 Block 的 `description` 字段中记录配置用途和注意事项

## 故障排查

### 问题：无法加载 Block

**错误信息**：`无法加载 Block 配置 'xxx': Block not found`

**解决方案**：
1. 检查 Block 名称是否正确
2. 在 Prefect UI 的 Blocks 页面确认 Block 是否存在
3. 检查 Prefect Server 连接是否正常

### 问题：Block 配置不生效

**可能原因**：
1. Deployment 中的参数覆盖了 Block 配置
2. Block 配置未保存
3. Flow 使用了环境变量覆盖

**解决方案**：
1. 检查 Deployment 的 `parameters` 是否传入了覆盖值
2. 在 Prefect UI 中确认 Block 配置已保存
3. 检查环境变量设置

## 参考

- [Prefect Blocks 文档](https://docs.prefect.io/latest/concepts/blocks/)
- [Prefect 3.x 配置管理最佳实践](https://docs.prefect.io/latest/guides/configuration/)
