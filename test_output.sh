#!/bin/bash
# 测试命令 - 使用 JSON 格式输出查看详细信息
python fetch_workflow_logs.py \
  --api-token app-R7kB8EZhzg4R8o2Li6FA4Dgb \
  --base-url http://localhost \
  --with-details \
  --format json \
  --limit 1
