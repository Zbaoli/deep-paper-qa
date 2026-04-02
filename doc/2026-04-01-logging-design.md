# 日志功能设计

## 概述

为 deep_paper_qa 添加两层日志持久化：
1. **loguru 文件日志** — 所有模块的调试日志按天写入文件
2. **结构化 JSONL 事件日志** — 每次对话的完整事件链，用于评测分析

## 需求

- 用途：评测分析（分析 Agent 准确率、tool 选择正确性、响应质量）
- JSONL 粒度：每个事件一条（用户消息、tool 调用开始/结束、Agent 回答各一条）
- 保留策略：不自动清理，手动管理
- 方案：loguru 文件输出（调试日志）+ 独立 ConversationLogger（评测 JSONL）

## 组件 1：loguru 文件日志配置

新建 `src/deep_paper_qa/logging_setup.py`。

### 配置

- 移除 loguru 默认 handler
- **stderr sink**：INFO 级别，简短格式（开发时控制台）
- **文件 sink**：DEBUG 级别，按天午夜轮转，不自动清理
  - 路径：`logs/app_{time:YYYY-MM-DD}.log`
  - 格式：`{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} | {message}`

### 调用时机

`app.py` 模块级别调用 `setup_logging()`，在 Chainlit 启动前完成配置。

### 日志补充

现有 loguru 调用（execute_sql、vector_search、search_abstracts）保持不变，文件 sink 自动捕获。

在 `app.py` 的 `astream_events` 循环中补充详细日志：

| 事件 | 记录内容 |
|------|---------|
| 用户消息 | thread_id, 完整 content |
| Tool 调用开始 | thread_id, tool_name, 完整 input 参数 |
| Tool 调用结束 | thread_id, tool_name, duration_ms, output 长度, output 前 1000 字 |
| Agent 回答 | thread_id, 完整 content |
| 会话统计 | thread_id, total_ms, tool_calls 次数, tools_used 列表 |

## 组件 2：ConversationLogger（结构化 JSONL）

新建 `src/deep_paper_qa/conversation_logger.py`，约 40 行。

### JSONL 事件类型

```jsonl
{"ts":"2026-04-01T10:00:01Z","thread_id":"abc-123","event":"user_message","content":"ACL 2025 发了多少篇论文"}
{"ts":"2026-04-01T10:00:02Z","thread_id":"abc-123","event":"tool_start","tool":"execute_sql","input":{"sql":"SELECT COUNT(*) FROM papers WHERE year=2025 AND conference='ACL'"}}
{"ts":"2026-04-01T10:00:03Z","thread_id":"abc-123","event":"tool_end","tool":"execute_sql","duration_ms":150,"output":"42"}
{"ts":"2026-04-01T10:00:04Z","thread_id":"abc-123","event":"agent_reply","content":"ACL 2025 共收录了 42 篇论文。","total_ms":3200,"tool_calls":1,"tools_used":["execute_sql"]}
```

### 类接口

```python
class ConversationLogger:
    def __init__(self, log_dir: str = "logs") -> None: ...
    def log_user_message(self, thread_id: str, content: str) -> None: ...
    def log_tool_start(self, thread_id: str, tool: str, input_data: dict) -> None: ...
    def log_tool_end(self, thread_id: str, tool: str, duration_ms: int, output: str) -> None: ...
    def log_agent_reply(self, thread_id: str, content: str, total_ms: int, tool_calls: int, tools_used: list[str]) -> None: ...
```

### 实现要点

- 每次调用 `json.dumps(event, ensure_ascii=False)` + 写入 + flush
- 文件路径：`logs/events.jsonl`（单文件追加）
- 线程安全：Chainlit 是单进程异步，无需加锁
- 异常处理：写入失败只 logger.warning，不影响主流程

## 集成（app.py 改动）

在 `on_message` 方法中：
1. 记录 `user_message` 事件
2. 在 `on_tool_start` 事件中记录 `tool_start`，保存开始时间
3. 在 `on_tool_end` 事件中计算 duration，记录 `tool_end`
4. 在事件循环结束后，汇总记录 `agent_reply`

## 改动文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/deep_paper_qa/logging_setup.py` | 新建 | loguru 配置 |
| `src/deep_paper_qa/conversation_logger.py` | 新建 | JSONL 事件写入器 |
| `src/deep_paper_qa/app.py` | 修改 | 集成两个日志组件 + 补充详细日志 |
| `.gitignore` | 修改 | 添加 `logs/` |
| `tests/test_conversation_logger.py` | 新建 | 单元测试 |

不改动：execute_sql.py、vector_search.py、search_abstracts.py、agent.py、config.py、models.py、prompts.py。

## 测试

- `test_conversation_logger.py`：验证 JSONL 写入格式、各事件类型字段完整性、文件创建
