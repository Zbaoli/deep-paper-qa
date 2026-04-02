# 日志功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 deep_paper_qa 添加 loguru 文件日志 + 结构化 JSONL 对话事件记录，用于调试和评测分析。

**Architecture:** 两个独立组件：`logging_setup.py` 配置 loguru 的 stderr + 文件 sink；`conversation_logger.py` 用 `ConversationLogger` 类将对话事件写入 JSONL。两者在 `app.py` 中集成。

**Tech Stack:** loguru（已有依赖）、json（标准库）、pathlib（标准库）

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/deep_paper_qa/logging_setup.py` | 新建 | loguru sink 配置（stderr + 按天轮转文件） |
| `src/deep_paper_qa/conversation_logger.py` | 新建 | JSONL 事件写入器 |
| `src/deep_paper_qa/app.py` | 修改 | 集成日志组件，补充详细事件日志 |
| `.gitignore` | 修改 | 添加 `logs/` |
| `tests/test_conversation_logger.py` | 新建 | ConversationLogger 单元测试 |

---

### Task 1: .gitignore 添加 logs/

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 添加 logs/ 到 .gitignore**

在 `.gitignore` 末尾追加：

```
# Logs
logs/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: .gitignore 添加 logs/ 目录"
```

---

### Task 2: ConversationLogger 测试 + 实现

**Files:**
- Create: `tests/test_conversation_logger.py`
- Create: `src/deep_paper_qa/conversation_logger.py`

- [ ] **Step 1: 写 ConversationLogger 的测试**

```python
# tests/test_conversation_logger.py
"""ConversationLogger 单元测试"""

import json
from pathlib import Path

import pytest

from deep_paper_qa.conversation_logger import ConversationLogger


@pytest.fixture()
def logger_instance(tmp_path: Path) -> ConversationLogger:
    """使用临时目录的 ConversationLogger 实例"""
    return ConversationLogger(log_dir=str(tmp_path))


@pytest.fixture()
def events_file(tmp_path: Path) -> Path:
    """JSONL 文件路径"""
    return tmp_path / "events.jsonl"


def _read_events(path: Path) -> list[dict]:
    """读取 JSONL 文件的所有事件"""
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    return [json.loads(line) for line in lines if line.strip()]


class TestLogUserMessage:
    def test_writes_user_message_event(
        self, logger_instance: ConversationLogger, events_file: Path
    ) -> None:
        logger_instance.log_user_message("thread-1", "ACL 2025 多少篇论文")

        events = _read_events(events_file)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "user_message"
        assert e["thread_id"] == "thread-1"
        assert e["content"] == "ACL 2025 多少篇论文"
        assert "ts" in e


class TestLogToolStart:
    def test_writes_tool_start_event(
        self, logger_instance: ConversationLogger, events_file: Path
    ) -> None:
        logger_instance.log_tool_start(
            "thread-1", "execute_sql", {"sql": "SELECT COUNT(*) FROM papers"}
        )

        events = _read_events(events_file)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "tool_start"
        assert e["tool"] == "execute_sql"
        assert e["input"] == {"sql": "SELECT COUNT(*) FROM papers"}


class TestLogToolEnd:
    def test_writes_tool_end_event(
        self, logger_instance: ConversationLogger, events_file: Path
    ) -> None:
        logger_instance.log_tool_end("thread-1", "execute_sql", 150, "42")

        events = _read_events(events_file)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "tool_end"
        assert e["tool"] == "execute_sql"
        assert e["duration_ms"] == 150
        assert e["output"] == "42"


class TestLogAgentReply:
    def test_writes_agent_reply_event(
        self, logger_instance: ConversationLogger, events_file: Path
    ) -> None:
        logger_instance.log_agent_reply(
            "thread-1", "共 42 篇", 3200, 1, ["execute_sql"]
        )

        events = _read_events(events_file)
        assert len(events) == 1
        e = events[0]
        assert e["event"] == "agent_reply"
        assert e["content"] == "共 42 篇"
        assert e["total_ms"] == 3200
        assert e["tool_calls"] == 1
        assert e["tools_used"] == ["execute_sql"]


class TestMultipleEvents:
    def test_appends_to_same_file(
        self, logger_instance: ConversationLogger, events_file: Path
    ) -> None:
        logger_instance.log_user_message("t1", "问题1")
        logger_instance.log_tool_start("t1", "execute_sql", {"sql": "SELECT 1"})
        logger_instance.log_tool_end("t1", "execute_sql", 100, "1")
        logger_instance.log_agent_reply("t1", "回答", 500, 1, ["execute_sql"])

        events = _read_events(events_file)
        assert len(events) == 4
        assert [e["event"] for e in events] == [
            "user_message", "tool_start", "tool_end", "agent_reply"
        ]


class TestDirectoryCreation:
    def test_creates_log_dir_if_not_exists(self, tmp_path: Path) -> None:
        new_dir = tmp_path / "subdir" / "logs"
        cl = ConversationLogger(log_dir=str(new_dir))
        cl.log_user_message("t1", "test")

        assert (new_dir / "events.jsonl").exists()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_conversation_logger.py -v
```

预期：FAIL，`ModuleNotFoundError: No module named 'deep_paper_qa.conversation_logger'`

- [ ] **Step 3: 实现 ConversationLogger**

```python
# src/deep_paper_qa/conversation_logger.py
"""结构化对话事件记录器，写入 JSONL 文件用于评测分析"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger


class ConversationLogger:
    """将对话事件以 JSONL 格式写入文件。

    每个事件一行 JSON，用 thread_id 关联同一会话的事件。
    写入失败不影响主流程，仅 logger.warning 记录。
    """

    def __init__(self, log_dir: str = "logs") -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = self._log_dir / "events.jsonl"

    def _write_event(self, event: dict[str, Any]) -> None:
        """写入单条事件到 JSONL 文件"""
        event["ts"] = datetime.now(timezone.utc).isoformat()
        try:
            line = json.dumps(event, ensure_ascii=False, default=str)
            with open(self._file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
        except Exception as e:
            logger.warning("JSONL 写入失败: {}", e)

    def log_user_message(self, thread_id: str, content: str) -> None:
        """记录用户消息事件"""
        self._write_event({
            "thread_id": thread_id,
            "event": "user_message",
            "content": content,
        })

    def log_tool_start(self, thread_id: str, tool: str, input_data: dict) -> None:
        """记录工具调用开始事件"""
        self._write_event({
            "thread_id": thread_id,
            "event": "tool_start",
            "tool": tool,
            "input": input_data,
        })

    def log_tool_end(
        self, thread_id: str, tool: str, duration_ms: int, output: str
    ) -> None:
        """记录工具调用结束事件"""
        self._write_event({
            "thread_id": thread_id,
            "event": "tool_end",
            "tool": tool,
            "duration_ms": duration_ms,
            "output": output,
        })

    def log_agent_reply(
        self,
        thread_id: str,
        content: str,
        total_ms: int,
        tool_calls: int,
        tools_used: list[str],
    ) -> None:
        """记录 Agent 最终回答事件"""
        self._write_event({
            "thread_id": thread_id,
            "event": "agent_reply",
            "content": content,
            "total_ms": total_ms,
            "tool_calls": tool_calls,
            "tools_used": tools_used,
        })
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_conversation_logger.py -v
```

预期：6 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/deep_paper_qa/conversation_logger.py tests/test_conversation_logger.py
git commit -m "feat: 添加 ConversationLogger 结构化 JSONL 事件记录"
```

---

### Task 3: logging_setup 模块

**Files:**
- Create: `src/deep_paper_qa/logging_setup.py`

- [ ] **Step 1: 创建 logging_setup.py**

```python
# src/deep_paper_qa/logging_setup.py
"""loguru 日志配置：stderr + 按天轮转文件输出"""

import sys

from loguru import logger


def setup_logging() -> None:
    """配置 loguru sink：stderr 控制台 + 文件持久化。

    移除默认 handler，添加两个 sink：
    - stderr: INFO 级别，简短格式（开发时控制台查看）
    - 文件:  DEBUG 级别，按天午夜轮转，不自动清理
    """
    logger.remove()

    # stderr：简短格式
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level:<8}</level> | "
            "{message}"
        ),
    )

    # 文件：按天轮转，完整格式
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="00:00",
        retention=None,
        encoding="utf-8",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level:<8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
    )

    logger.info("日志系统初始化完成")
```

- [ ] **Step 2: Commit**

```bash
git add src/deep_paper_qa/logging_setup.py
git commit -m "feat: 添加 loguru 文件日志配置（按天轮转）"
```

---

### Task 4: 集成到 app.py

**Files:**
- Modify: `src/deep_paper_qa/app.py`

- [ ] **Step 1: 重写 app.py 集成两个日志组件**

将 `src/deep_paper_qa/app.py` 完整替换为：

```python
"""Chainlit 入口：Agent 流式输出 + 中间步骤展示 + 日志记录"""

import time
import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_agent
from deep_paper_qa.conversation_logger import ConversationLogger
from deep_paper_qa.logging_setup import setup_logging

# 初始化日志
setup_logging()

# 全局 Agent 实例
_agent, _checkpointer = build_agent()

# 结构化事件记录器
_conv_logger = ConversationLogger()


@cl.on_chat_start
async def on_chat_start() -> None:
    """初始化会话"""
    thread_id = str(uuid.uuid4())
    cl.user_session.set("thread_id", thread_id)
    logger.info("新会话启动 | thread_id={}", thread_id)
    await cl.Message(
        content="你好！我是 AI 科研论文问答助手。可以问我关于论文的统计信息或内容问题。"
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """处理用户消息，记录完整事件链"""
    thread_id = cl.user_session.get("thread_id")
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 30,
    }

    # 记录用户消息
    logger.info("用户消息 | thread_id={} | content={}", thread_id, message.content)
    _conv_logger.log_user_message(thread_id, message.content)

    # 会话级统计
    msg_start = time.monotonic()
    tool_call_count = 0
    tools_used: list[str] = []
    # tool 调用计时：run_id -> (tool_name, start_time)
    tool_timings: dict[str, tuple[str, float]] = {}

    final_msg = cl.Message(content="")
    await final_msg.send()

    try:
        async for event in _agent.astream_events(
            {"messages": [HumanMessage(content=message.content)]},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            name = event.get("name", "")

            # 工具调用开始
            if kind == "on_tool_start":
                tool_name = name
                tool_input = event.get("data", {}).get("input", {})
                run_id = event.get("run_id", "")

                # loguru 详细日志
                logger.info(
                    "Tool调用 | thread_id={} | tool={} | input={}",
                    thread_id, tool_name, tool_input,
                )
                # JSONL 事件
                _conv_logger.log_tool_start(thread_id, tool_name, tool_input)

                # 记录开始时间
                tool_timings[run_id] = (tool_name, time.monotonic())
                tool_call_count += 1
                if tool_name not in tools_used:
                    tools_used.append(tool_name)

                # Chainlit 中间步骤
                step = cl.Step(name=f"🔧 {tool_name}", type="tool")
                step.input = str(tool_input)
                await step.send()
                cl.user_session.set(f"step_{run_id}", step)

            # 工具调用结束
            elif kind == "on_tool_end":
                run_id = event.get("run_id", "")
                output = event.get("data", {}).get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                output_str = str(output)

                # 计算耗时
                duration_ms = 0
                tool_name = "unknown"
                if run_id in tool_timings:
                    tool_name, start_t = tool_timings.pop(run_id)
                    duration_ms = int((time.monotonic() - start_t) * 1000)

                # loguru 详细日志
                logger.info(
                    "Tool返回 | thread_id={} | tool={} | duration_ms={} | "
                    "output_len={} | output={}",
                    thread_id, tool_name, duration_ms,
                    len(output_str), output_str[:1000],
                )
                # JSONL 事件
                _conv_logger.log_tool_end(
                    thread_id, tool_name, duration_ms, output_str
                )

                # Chainlit 更新步骤
                step = cl.user_session.get(f"step_{run_id}")
                if step:
                    step.output = (
                        output_str[:500] if len(output_str) > 500 else output_str
                    )
                    await step.update()

            # LLM 流式输出
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    await final_msg.stream_token(chunk.content)

        await final_msg.update()

        # 会话统计
        total_ms = int((time.monotonic() - msg_start) * 1000)
        logger.info(
            "会话统计 | thread_id={} | total_ms={} | tool_calls={} | tools_used={}",
            thread_id, total_ms, tool_call_count, tools_used,
        )
        # JSONL 汇总事件
        _conv_logger.log_agent_reply(
            thread_id,
            final_msg.content,
            total_ms,
            tool_call_count,
            tools_used,
        )

    except Exception as e:
        logger.error("Agent 执行异常 | thread_id={} | error={}", thread_id, e)
        final_msg.content = f"抱歉，处理您的问题时出现错误：{e}"
        await final_msg.update()
```

- [ ] **Step 2: 手动验证**

```bash
# 确认文件语法正确
uv run python -c "from deep_paper_qa.app import on_message; print('import ok')"
```

预期：`import ok`（不会真正启动 Chainlit，只验证导入）

- [ ] **Step 3: Commit**

```bash
git add src/deep_paper_qa/app.py
git commit -m "feat: app.py 集成 loguru 文件日志 + ConversationLogger JSONL 记录"
```

---

### Task 5: 端到端验证

- [ ] **Step 1: 确认所有测试通过**

```bash
uv run pytest tests/ -v
```

预期：所有测试 PASSED（含 test_conversation_logger.py 的 6 个测试）

- [ ] **Step 2: 确认 logs/ 被 gitignore**

```bash
mkdir -p logs && touch logs/test.log
git status logs/
```

预期：无输出（logs/ 被忽略）

```bash
rm -rf logs/
```

- [ ] **Step 3: Commit（如有遗漏改动）**

```bash
git status
```

如有未提交的改动，补充 commit。
