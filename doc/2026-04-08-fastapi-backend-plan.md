# FastAPI 后端 API 层 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 FastAPI + SSE 构建后端 API 层替代 Chainlit，与现有 `app.py` 并存。提供聊天 SSE 流、论文搜索、统计数据等 REST 接口。

**Architecture:** FastAPI 入口 `api.py` + 三个路由模块 (`routers/chat.py`, `routers/papers.py`, `routers/stats.py`)。核心是 `chat.py` 中的 SSE 事件转换层，将 LangGraph `astream_events` 转为结构化 SSE 事件。`ask_user` 工具改为通过 `asyncio.Event` 与 HTTP endpoint 通信，脱离 Chainlit 依赖。

**Tech Stack:** FastAPI, sse-starlette, uvicorn, asyncpg (已有), pydantic (已有)

---

## 文件结构

| 文件 | 动作 | 职责 |
|---|---|---|
| `src/deep_paper_qa/api.py` | 新建 | FastAPI 入口，挂载路由，CORS，静态文件 |
| `src/deep_paper_qa/routers/__init__.py` | 新建 | 空 |
| `src/deep_paper_qa/routers/chat.py` | 新建 | POST /api/chat SSE 流 + POST /api/chat/{thread_id}/reply |
| `src/deep_paper_qa/routers/papers.py` | 新建 | GET /api/papers + GET /api/papers/{id} |
| `src/deep_paper_qa/routers/stats.py` | 新建 | GET /api/stats |
| `src/deep_paper_qa/sse_events.py` | 新建 | SSE 事件类型定义 + astream_events 转换器 |
| `src/deep_paper_qa/tools/ask_user.py` | 修改 | 脱离 Chainlit，改用 asyncio.Event 机制 |
| `src/deep_paper_qa/config.py` | 修改 | 新增 cors_origins 配置 |
| `pyproject.toml` | 修改 | 新增 fastapi/uvicorn/sse-starlette 依赖 |
| `tests/test_sse_events.py` | 新建 | SSE 事件转换测试 |
| `tests/test_api_chat.py` | 新建 | 聊天 API 端到端测试 |
| `tests/test_api_papers.py` | 新建 | 论文 API 测试 |
| `tests/test_api_stats.py` | 新建 | 统计 API 测试 |
| `tests/test_ask_user_v2.py` | 新建 | 新 ask_user 机制测试 |

---

### Task 1: 添加依赖和配置

**Files:**
- Modify: `pyproject.toml:7-18`
- Modify: `src/deep_paper_qa/config.py:33-39`

- [ ] **Step 1: 在 pyproject.toml 添加依赖**

在 `pyproject.toml` 的 `dependencies` 列表中追加：

```toml
    "fastapi>=0.115",
    "uvicorn>=0.34",
    "sse-starlette>=2.0",
```

- [ ] **Step 2: 在 config.py 添加 CORS 配置**

在 `src/deep_paper_qa/config.py` 的 `Settings` 类中，`external_search_timeout` 之后添加：

```python
    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]
```

- [ ] **Step 3: 安装依赖**

运行: `uv sync --all-extras`
预期: 成功安装 fastapi, uvicorn, sse-starlette

- [ ] **Step 4: 验证**

运行: `uv run python -c "import fastapi; import sse_starlette; print('OK')"`
预期: `OK`

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml src/deep_paper_qa/config.py
git commit -m "feat: 添加 FastAPI/uvicorn/sse-starlette 依赖和 CORS 配置"
```

---

### Task 2: SSE 事件类型定义和转换器

**Files:**
- Create: `src/deep_paper_qa/sse_events.py`
- Create: `tests/test_sse_events.py`

- [ ] **Step 1: 编写测试**

创建 `tests/test_sse_events.py`：

```python
"""SSE 事件转换测试"""

import json

import pytest

from deep_paper_qa.sse_events import (
    sse_ask_user,
    sse_chart,
    sse_done,
    sse_error,
    sse_route,
    sse_token,
    sse_tool_end,
    sse_tool_start,
)


class TestSseEventBuilders:
    """SSE 事件构造函数测试"""

    def test_route_event(self) -> None:
        event = sse_route("general", "普通问答")
        assert event.event == "route"
        data = json.loads(event.data)
        assert data["category"] == "general"
        assert data["label"] == "普通问答"

    def test_tool_start_event(self) -> None:
        event = sse_tool_start("execute_sql", {"sql": "SELECT 1"}, "run-123")
        assert event.event == "tool_start"
        data = json.loads(event.data)
        assert data["tool"] == "execute_sql"
        assert data["input"]["sql"] == "SELECT 1"
        assert data["run_id"] == "run-123"

    def test_tool_end_event(self) -> None:
        event = sse_tool_end("execute_sql", "result", 120, "run-123")
        assert event.event == "tool_end"
        data = json.loads(event.data)
        assert data["tool"] == "execute_sql"
        assert data["output"] == "result"
        assert data["duration_ms"] == 120

    def test_token_event(self) -> None:
        event = sse_token("根据")
        assert event.event == "token"
        data = json.loads(event.data)
        assert data["content"] == "根据"

    def test_chart_event(self) -> None:
        option = {"xAxis": {"data": ["2020", "2021"]}}
        event = sse_chart(option)
        assert event.event == "chart"
        data = json.loads(event.data)
        assert data["type"] == "echarts"
        assert data["option"]["xAxis"]["data"][0] == "2020"

    def test_ask_user_event(self) -> None:
        event = sse_ask_user("请确认", "摘要内容")
        assert event.event == "ask_user"
        data = json.loads(event.data)
        assert data["question"] == "请确认"
        assert data["summary"] == "摘要内容"

    def test_done_event(self) -> None:
        event = sse_done(3200, 2)
        assert event.event == "done"
        data = json.loads(event.data)
        assert data["total_ms"] == 3200
        assert data["tool_calls"] == 2

    def test_error_event(self) -> None:
        event = sse_error("处理失败")
        assert event.event == "error"
        data = json.loads(event.data)
        assert data["message"] == "处理失败"
```

- [ ] **Step 2: 运行测试确认失败**

运行: `uv run pytest tests/test_sse_events.py -v`
预期: FAIL（模块不存在）

- [ ] **Step 3: 实现 sse_events.py**

创建 `src/deep_paper_qa/sse_events.py`：

```python
"""SSE 事件类型定义和构造函数"""

import json
from typing import Any

from sse_starlette.sse import ServerSentEvent


def _event(event_type: str, data: dict[str, Any]) -> ServerSentEvent:
    """构造 SSE 事件"""
    return ServerSentEvent(event=event_type, data=json.dumps(data, ensure_ascii=False))


def sse_route(category: str, label: str) -> ServerSentEvent:
    """路由分类事件"""
    return _event("route", {"category": category, "label": label})


def sse_tool_start(tool: str, input_data: Any, run_id: str) -> ServerSentEvent:
    """工具调用开始事件"""
    return _event("tool_start", {"tool": tool, "input": input_data, "run_id": run_id})


def sse_tool_end(tool: str, output: str, duration_ms: int, run_id: str) -> ServerSentEvent:
    """工具调用结束事件"""
    return _event(
        "tool_end",
        {"tool": tool, "output": output, "duration_ms": duration_ms, "run_id": run_id},
    )


def sse_token(content: str) -> ServerSentEvent:
    """LLM 流式 token 事件"""
    return _event("token", {"content": content})


def sse_chart(option: dict[str, Any]) -> ServerSentEvent:
    """图表事件（ECharts option）"""
    return _event("chart", {"type": "echarts", "option": option})


def sse_ask_user(question: str, summary: str) -> ServerSentEvent:
    """ask_user 交互事件"""
    return _event("ask_user", {"question": question, "summary": summary})


def sse_done(total_ms: int, tool_calls: int) -> ServerSentEvent:
    """完成事件"""
    return _event("done", {"total_ms": total_ms, "tool_calls": tool_calls})


def sse_error(message: str) -> ServerSentEvent:
    """错误事件"""
    return _event("error", {"message": message})
```

- [ ] **Step 4: 运行测试确认通过**

运行: `uv run pytest tests/test_sse_events.py -v`
预期: 8 passed

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/sse_events.py tests/test_sse_events.py
git commit -m "feat: SSE 事件类型定义和构造函数"
```

---

### Task 3: ask_user 工具脱离 Chainlit

**Files:**
- Modify: `src/deep_paper_qa/tools/ask_user.py`
- Create: `tests/test_ask_user_v2.py`

- [ ] **Step 1: 编写新 ask_user 测试**

创建 `tests/test_ask_user_v2.py`：

```python
"""ask_user 工具测试（脱离 Chainlit，基于 asyncio.Event）"""

import asyncio

import pytest

from deep_paper_qa.tools.ask_user import ask_user, get_pending_question, submit_reply


class TestAskUser:
    """ask_user 异步交互测试"""

    @pytest.mark.asyncio
    async def test_submit_reply_wakes_up_ask_user(self) -> None:
        """submit_reply 能唤醒等待中的 ask_user"""

        async def simulate_user_reply(thread_id: str) -> None:
            await asyncio.sleep(0.05)
            submit_reply(thread_id, "继续")

        task = asyncio.create_task(simulate_user_reply("thread-1"))
        result = await ask_user.ainvoke(
            {"summary": "摘要", "question": "是否继续？", "__thread_id": "thread-1"}
        )
        await task
        assert result == "继续"

    @pytest.mark.asyncio
    async def test_timeout_returns_default(self) -> None:
        """超时未回复返回默认消息"""
        result = await ask_user.ainvoke(
            {
                "summary": "摘要",
                "question": "是否继续？",
                "__thread_id": "thread-2",
                "__timeout": 0.1,
            }
        )
        assert "未回复" in result

    @pytest.mark.asyncio
    async def test_get_pending_question(self) -> None:
        """get_pending_question 返回当前等待中的问题"""

        async def invoke_ask() -> str:
            return await ask_user.ainvoke(
                {"summary": "研究进展", "question": "下一步？", "__thread_id": "thread-3"}
            )

        task = asyncio.create_task(invoke_ask())
        await asyncio.sleep(0.05)

        pending = get_pending_question("thread-3")
        assert pending is not None
        assert pending["question"] == "下一步？"
        assert pending["summary"] == "研究进展"

        submit_reply("thread-3", "总结")
        result = await task
        assert result == "总结"

    @pytest.mark.asyncio
    async def test_no_pending_question(self) -> None:
        """没有等待中的问题时返回 None"""
        pending = get_pending_question("nonexistent")
        assert pending is None
```

- [ ] **Step 2: 运行测试确认失败**

运行: `uv run pytest tests/test_ask_user_v2.py -v`
预期: FAIL（get_pending_question, submit_reply 不存在）

- [ ] **Step 3: 重写 ask_user.py**

替换 `src/deep_paper_qa/tools/ask_user.py` 全部内容：

```python
"""ask_user 工具：暂停等待用户输入（脱离 Chainlit，基于 asyncio.Event）"""

import asyncio
from typing import Any

from langchain_core.tools import tool
from loguru import logger

# thread_id → (Event, 回复内容) 映射
_pending: dict[str, dict[str, Any]] = {}

# 默认超时（秒）
_DEFAULT_TIMEOUT = 300


def get_pending_question(thread_id: str) -> dict[str, Any] | None:
    """获取指定 thread 当前等待中的问题，无则返回 None"""
    entry = _pending.get(thread_id)
    if entry and not entry["event"].is_set():
        return {"question": entry["question"], "summary": entry["summary"]}
    return None


def submit_reply(thread_id: str, reply: str) -> bool:
    """提交用户回复，唤醒等待中的 ask_user。成功返回 True。"""
    entry = _pending.get(thread_id)
    if entry and not entry["event"].is_set():
        entry["reply"] = reply
        entry["event"].set()
        logger.info("ask_user | thread={} | 收到用户回复: {}", thread_id, reply[:200])
        return True
    logger.warning("ask_user | thread={} | 无等待中的问题", thread_id)
    return False


@tool
async def ask_user(
    summary: str,
    question: str,
    __thread_id: str = "",
    __timeout: float = 0,
) -> str:
    """暂停研究流程，向用户展示当前发现并等待指令。仅在深度研究模式中使用。

    在每个研究阶段结束后调用，展示阶段性发现摘要，询问用户下一步操作。
    用户可以回复"继续"、"调整方向: ..."、"总结"等指令。

    Args:
        summary: 当前阶段的发现摘要，展示给用户
        question: 向用户提的问题（如"是否继续下一个子问题？"）
    """
    timeout = __timeout if __timeout > 0 else _DEFAULT_TIMEOUT
    logger.info(
        "ask_user | thread={} | summary_len={} | question={}",
        __thread_id,
        len(summary),
        question[:100],
    )

    event = asyncio.Event()
    _pending[__thread_id] = {
        "event": event,
        "question": question,
        "summary": summary,
        "reply": "",
    }

    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
        reply = _pending[__thread_id]["reply"]
        logger.info("ask_user | thread={} | 用户回复: {}", __thread_id, reply[:200])
        return reply
    except asyncio.TimeoutError:
        logger.info("ask_user | thread={} | 用户超时未回复", __thread_id)
        return "用户未回复，请继续执行下一个子问题。"
    finally:
        _pending.pop(__thread_id, None)
```

- [ ] **Step 4: 运行新测试确认通过**

运行: `uv run pytest tests/test_ask_user_v2.py -v`
预期: 4 passed

- [ ] **Step 5: 运行旧 ask_user 测试确认兼容性**

运行: `uv run pytest tests/test_ask_user.py -v`
预期: 可能失败（旧测试 mock Chainlit）。如果失败，更新旧测试适配新实现，或删除旧测试文件，因为 `test_ask_user_v2.py` 已覆盖。

- [ ] **Step 6: 提交**

```bash
git add src/deep_paper_qa/tools/ask_user.py tests/test_ask_user_v2.py
git commit -m "refactor: ask_user 脱离 Chainlit，改用 asyncio.Event 机制"
```

---

### Task 4: FastAPI 入口和 CORS

**Files:**
- Create: `src/deep_paper_qa/api.py`
- Create: `src/deep_paper_qa/routers/__init__.py`

- [ ] **Step 1: 创建路由包**

创建空文件 `src/deep_paper_qa/routers/__init__.py`。

- [ ] **Step 2: 创建 FastAPI 入口**

创建 `src/deep_paper_qa/api.py`：

```python
"""FastAPI 入口：API 路由 + CORS + 静态文件"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from deep_paper_qa.config import settings
from deep_paper_qa.logging_setup import setup_logging
from deep_paper_qa.routers import chat, papers, stats

setup_logging()

app = FastAPI(title="Deep Paper QA", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(papers.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """健康检查"""
    return {"status": "ok"}
```

- [ ] **Step 3: 验证启动（先创建空路由桩）**

暂时创建三个空路由文件（后续 Task 会实现完整逻辑）：

`src/deep_paper_qa/routers/chat.py`：
```python
"""聊天 API 路由"""

from fastapi import APIRouter

router = APIRouter(tags=["chat"])
```

`src/deep_paper_qa/routers/papers.py`：
```python
"""论文浏览 API 路由"""

from fastapi import APIRouter

router = APIRouter(tags=["papers"])
```

`src/deep_paper_qa/routers/stats.py`：
```python
"""统计数据 API 路由"""

from fastapi import APIRouter

router = APIRouter(tags=["stats"])
```

- [ ] **Step 4: 验证 FastAPI 启动**

运行: `uv run uvicorn deep_paper_qa.api:app --port 8001 &`
然后: `curl http://localhost:8001/api/health`
预期: `{"status":"ok"}`
然后终止 uvicorn 进程。

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/api.py src/deep_paper_qa/routers/
git commit -m "feat: FastAPI 入口 + 路由桩 + CORS + 健康检查"
```

---

### Task 5: 聊天路由 — SSE 事件流

**Files:**
- Modify: `src/deep_paper_qa/routers/chat.py`
- Create: `tests/test_api_chat.py`

- [ ] **Step 1: 编写测试**

创建 `tests/test_api_chat.py`：

```python
"""聊天 API 路由测试"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from deep_paper_qa.api import app


class TestHealthEndpoint:
    """健康检查测试"""

    def test_health(self) -> None:
        client = TestClient(app)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestChatEndpoint:
    """POST /api/chat 测试"""

    def test_chat_returns_sse_stream(self) -> None:
        """正常聊天返回 SSE 流"""

        async def fake_stream(*args, **kwargs):
            yield {
                "event": "on_chain_end",
                "name": "router",
                "data": {"output": {"category": "general"}},
            }
            yield {
                "event": "on_chat_model_stream",
                "name": "ChatOpenAI",
                "data": {"chunk": MagicMock(content="你好")},
            }

        with patch("deep_paper_qa.routers.chat._get_graph") as mock_graph_fn:
            mock_graph = MagicMock()
            mock_graph.astream_events = fake_stream
            mock_graph_fn.return_value = mock_graph

            client = TestClient(app)
            resp = client.post(
                "/api/chat",
                json={"message": "测试", "thread_id": "test-thread"},
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]

            lines = resp.text.strip().split("\n")
            events = []
            for line in lines:
                if line.startswith("data:"):
                    data_str = line[len("data:"):].strip()
                    if data_str:
                        events.append(json.loads(data_str))

            # 至少应有 route 和 done 事件
            event_types = [e.get("category") or e.get("content") or e.get("total_ms") for e in events]
            assert len(events) >= 1


class TestReplyEndpoint:
    """POST /api/chat/{thread_id}/reply 测试"""

    def test_reply_no_pending(self) -> None:
        """没有等待中的问题时返回 404"""
        client = TestClient(app)
        resp = client.post(
            "/api/chat/nonexistent/reply",
            json={"reply": "继续"},
        )
        assert resp.status_code == 404
```

- [ ] **Step 2: 运行测试确认失败**

运行: `uv run pytest tests/test_api_chat.py -v`
预期: FAIL（路由未实现）

- [ ] **Step 3: 实现聊天路由**

替换 `src/deep_paper_qa/routers/chat.py` 全部内容：

```python
"""聊天 API 路由：SSE 事件流 + ask_user 回复"""

import re
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from loguru import logger
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from deep_paper_qa.agent import CATEGORY_LABELS, build_graph
from deep_paper_qa.conversation_logger import ConversationLogger
from deep_paper_qa.sse_events import (
    sse_ask_user,
    sse_done,
    sse_error,
    sse_route,
    sse_token,
    sse_tool_end,
    sse_tool_start,
)
from deep_paper_qa.tools.ask_user import get_pending_question, submit_reply

router = APIRouter(tags=["chat"])

_graph, _checkpointer = None, None
_conv_logger = ConversationLogger()


def _get_graph():
    """懒加载 graph（避免 import 时就构建）"""
    global _graph, _checkpointer
    if _graph is None:
        _graph, _checkpointer = build_graph()
    return _graph


class ChatRequest(BaseModel):
    """聊天请求"""

    message: str
    thread_id: str


class ReplyRequest(BaseModel):
    """ask_user 回复请求"""

    reply: str


@router.post("/chat")
async def chat(req: ChatRequest) -> EventSourceResponse:
    """聊天 SSE 流"""

    async def event_stream():
        graph = _get_graph()
        config = {
            "configurable": {"thread_id": req.thread_id},
            "recursion_limit": 50,
        }

        logger.info("API chat | thread={} | message={}", req.thread_id, req.message[:200])
        _conv_logger.log_user_message(req.thread_id, req.message)

        msg_start = time.monotonic()
        tool_call_count = 0
        tools_used: list[str] = []
        tool_timings: dict[str, tuple[str, float]] = {}
        router_shown = False

        try:
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=req.message)]},
                config=config,
                version="v2",
            ):
                kind = event.get("event", "")
                name = event.get("name", "")

                # 路由分类
                if kind == "on_chain_end" and name == "router" and not router_shown:
                    try:
                        output = event.get("data", {}).get("output", {})
                        cat = output.get("category", "")
                        if cat:
                            label = CATEGORY_LABELS.get(cat, cat)
                            yield sse_route(cat, label)
                            router_shown = True
                    except Exception:
                        pass

                # 工具开始
                elif kind == "on_tool_start":
                    run_id = event.get("run_id", "")
                    tool_input = event.get("data", {}).get("input", {})
                    tool_timings[run_id] = (name, time.monotonic())
                    tool_call_count += 1
                    if name not in tools_used:
                        tools_used.append(name)

                    _conv_logger.log_tool_start(req.thread_id, name, tool_input)

                    if name == "ask_user":
                        summary = tool_input.get("summary", "")
                        question = tool_input.get("question", "")
                        yield sse_ask_user(question, summary)
                    else:
                        yield sse_tool_start(name, tool_input, run_id)

                # 工具结束
                elif kind == "on_tool_end":
                    run_id = event.get("run_id", "")
                    output = event.get("data", {}).get("output", "")
                    if hasattr(output, "content"):
                        output = output.content
                    output_str = str(output)

                    duration_ms = 0
                    tool_name = name
                    if run_id in tool_timings:
                        tool_name, start_t = tool_timings.pop(run_id)
                        duration_ms = int((time.monotonic() - start_t) * 1000)

                    _conv_logger.log_tool_end(req.thread_id, tool_name, duration_ms, output_str)

                    if tool_name != "ask_user":
                        yield sse_tool_end(
                            tool_name,
                            output_str[:500] if len(output_str) > 500 else output_str,
                            duration_ms,
                            run_id,
                        )

                # LLM 流式 token
                elif kind == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk", None)
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield sse_token(chunk.content)

            # 非流式 pipeline：从 state 获取最终消息
            try:
                state = _get_graph().get_state(config)
                msgs = state.values.get("messages", [])
                for m in reversed(msgs):
                    if isinstance(m, AIMessage) and m.content:
                        content = m.content
                        # 提取 plotly 图表转为 chart 事件
                        plotly_match = re.search(
                            r"<!--plotly:(.*?)-->", content, re.DOTALL
                        )
                        if plotly_match:
                            import json

                            chart_json = plotly_match.group(1)
                            content = re.sub(
                                r"<!--plotly:.*?-->\n*", "", content, flags=re.DOTALL
                            )
                            try:
                                import plotly.io as pio

                                fig = pio.from_json(chart_json)
                                fig_dict = fig.to_dict()
                                yield sse_token(content)
                                yield sse_chart_plotly(fig_dict)
                            except Exception:
                                yield sse_token(content)
                        break
            except Exception as e:
                logger.warning("获取最终状态失败: {}", e)

            total_ms = int((time.monotonic() - msg_start) * 1000)
            _conv_logger.log_agent_reply(
                req.thread_id, "", total_ms, tool_call_count, tools_used
            )
            yield sse_done(total_ms, tool_call_count)

        except Exception as e:
            logger.error("API chat 异常 | thread={} | error={}", req.thread_id, e)
            yield sse_error(str(e))

    return EventSourceResponse(event_stream())


def sse_chart_plotly(fig_dict: dict[str, Any]):
    """将 Plotly figure dict 转为 chart SSE 事件"""
    from deep_paper_qa.sse_events import _event

    return _event("chart", {"type": "plotly", "figure": fig_dict})


@router.post("/chat/{thread_id}/reply")
async def reply(thread_id: str, req: ReplyRequest) -> dict[str, str]:
    """提交 ask_user 回复"""
    pending = get_pending_question(thread_id)
    if not pending:
        raise HTTPException(status_code=404, detail="没有等待中的问题")

    submit_reply(thread_id, req.reply)
    return {"status": "ok"}
```

- [ ] **Step 4: 运行测试确认通过**

运行: `uv run pytest tests/test_api_chat.py -v`
预期: 3 passed

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/routers/chat.py tests/test_api_chat.py
git commit -m "feat: 聊天路由 — SSE 事件流 + ask_user 回复端点"
```

---

### Task 6: 论文浏览路由

**Files:**
- Modify: `src/deep_paper_qa/routers/papers.py`
- Create: `tests/test_api_papers.py`

- [ ] **Step 1: 编写测试**

创建 `tests/test_api_papers.py`：

```python
"""论文浏览 API 测试"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from deep_paper_qa.api import app


class _FakeRecord(dict):
    """模拟 asyncpg.Record"""

    def keys(self):
        return list(super().keys())

    def values(self):
        return list(super().values())


class _MockAcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_mock_pool(records: list[dict]) -> MagicMock:
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[_FakeRecord(r) for r in records])
    mock_conn.fetchrow = AsyncMock(
        return_value=_FakeRecord(records[0]) if records else None
    )
    mock_pool = MagicMock()
    mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)
    return mock_pool


class TestPapersSearch:
    """GET /api/papers 测试"""

    @pytest.mark.asyncio
    async def test_search_papers(self) -> None:
        records = [
            {
                "id": "acl-2025-1",
                "title": "RAG Survey",
                "year": 2025,
                "conference": "ACL",
                "citations": 10,
                "abstract": "A survey...",
            }
        ]
        mock_pool = _make_mock_pool(records)
        count_conn = AsyncMock()
        count_conn.fetchval = AsyncMock(return_value=1)

        with patch(
            "deep_paper_qa.routers.papers.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            client = TestClient(app)
            resp = client.get("/api/papers?q=RAG")
            assert resp.status_code == 200
            data = resp.json()
            assert "papers" in data
            assert len(data["papers"]) == 1
            assert data["papers"][0]["title"] == "RAG Survey"


class TestPaperDetail:
    """GET /api/papers/{id} 测试"""

    @pytest.mark.asyncio
    async def test_paper_detail(self) -> None:
        record = {
            "id": "acl-2025-1",
            "title": "RAG Survey",
            "abstract": "Full abstract...",
            "year": 2025,
            "conference": "ACL",
            "citations": 10,
            "authors": ["Author A"],
            "url": "https://example.com",
        }
        mock_pool = _make_mock_pool([record])

        with patch(
            "deep_paper_qa.routers.papers.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            client = TestClient(app)
            resp = client.get("/api/papers/acl-2025-1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["title"] == "RAG Survey"

    @pytest.mark.asyncio
    async def test_paper_not_found(self) -> None:
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)

        with patch(
            "deep_paper_qa.routers.papers.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            client = TestClient(app)
            resp = client.get("/api/papers/nonexistent")
            assert resp.status_code == 404
```

- [ ] **Step 2: 运行测试确认失败**

运行: `uv run pytest tests/test_api_papers.py -v`
预期: FAIL

- [ ] **Step 3: 实现论文路由**

替换 `src/deep_paper_qa/routers/papers.py` 全部内容：

```python
"""论文浏览 API 路由"""

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from deep_paper_qa.tools.execute_sql import get_readonly_pool

router = APIRouter(tags=["papers"])


@router.get("/papers")
async def search_papers(
    q: str = Query("", description="搜索关键词"),
    year: int | None = Query(None, description="年份过滤"),
    conference: str | None = Query(None, description="会议过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
) -> dict:
    """搜索论文列表"""
    conditions: list[str] = []
    params: list = []
    param_idx = 1

    if q:
        conditions.append(
            f"to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))"
            f" @@ websearch_to_tsquery('english', ${param_idx})"
        )
        params.append(q)
        param_idx += 1

    if year:
        conditions.append(f"year = ${param_idx}")
        params.append(year)
        param_idx += 1

    if conference:
        conditions.append(f"conference = ${param_idx}")
        params.append(conference)
        param_idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size

    sql = f"""
        SELECT id, title, year, conference, citations,
               LEFT(abstract, 200) AS abstract
        FROM papers
        {where}
        ORDER BY citations DESC, year DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([page_size, offset])

    logger.info("API papers | q='{}' year={} conf={} page={}", q, year, conference, page)

    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        records = await conn.fetch(sql, *params)

    papers = [dict(r) for r in records]
    return {"papers": papers, "page": page, "page_size": page_size}


@router.get("/papers/{paper_id}")
async def paper_detail(paper_id: str) -> dict:
    """论文详情"""
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT id, title, abstract, year, conference, venue_type, "
            "authors, citations, url, pdf_url FROM papers WHERE id = $1",
            paper_id,
        )

    if not record:
        raise HTTPException(status_code=404, detail="论文不存在")

    return dict(record)
```

- [ ] **Step 4: 运行测试确认通过**

运行: `uv run pytest tests/test_api_papers.py -v`
预期: 3 passed

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/routers/papers.py tests/test_api_papers.py
git commit -m "feat: 论文浏览 API 路由（搜索 + 详情）"
```

---

### Task 7: 统计数据路由

**Files:**
- Modify: `src/deep_paper_qa/routers/stats.py`
- Create: `tests/test_api_stats.py`

- [ ] **Step 1: 编写测试**

创建 `tests/test_api_stats.py`：

```python
"""统计数据 API 测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from deep_paper_qa.api import app


class _FakeRecord(dict):
    def keys(self):
        return list(super().keys())

    def values(self):
        return list(super().values())


class _MockAcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


class TestStatsEndpoint:
    """GET /api/stats 测试"""

    @pytest.mark.asyncio
    async def test_stats(self) -> None:
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=81913)
        mock_conn.fetch = AsyncMock(
            side_effect=[
                # by_year
                [_FakeRecord({"year": 2024, "count": 15000}), _FakeRecord({"year": 2025, "count": 18000})],
                # by_conference
                [_FakeRecord({"conference": "NeurIPS", "count": 12000})],
            ]
        )
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)

        with patch(
            "deep_paper_qa.routers.stats.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            client = TestClient(app)
            resp = client.get("/api/stats")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_papers"] == 81913
            assert "by_year" in data
            assert "by_conference" in data
```

- [ ] **Step 2: 运行测试确认失败**

运行: `uv run pytest tests/test_api_stats.py -v`
预期: FAIL

- [ ] **Step 3: 实现统计路由**

替换 `src/deep_paper_qa/routers/stats.py` 全部内容：

```python
"""统计数据 API 路由"""

from fastapi import APIRouter
from loguru import logger

from deep_paper_qa.tools.execute_sql import get_readonly_pool

router = APIRouter(tags=["stats"])


@router.get("/stats")
async def stats() -> dict:
    """论文统计数据"""
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM papers")

        by_year = await conn.fetch(
            "SELECT year, COUNT(*) AS count FROM papers GROUP BY year ORDER BY year"
        )

        by_conference = await conn.fetch(
            "SELECT conference, COUNT(*) AS count FROM papers "
            "GROUP BY conference ORDER BY count DESC"
        )

    logger.info("API stats | total={}", total)
    return {
        "total_papers": total,
        "by_year": [dict(r) for r in by_year],
        "by_conference": [dict(r) for r in by_conference],
    }
```

- [ ] **Step 4: 运行测试确认通过**

运行: `uv run pytest tests/test_api_stats.py -v`
预期: 1 passed

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/routers/stats.py tests/test_api_stats.py
git commit -m "feat: 统计数据 API 路由"
```

---

### Task 8: 历史会话路由

**Files:**
- Modify: `src/deep_paper_qa/routers/chat.py`

- [ ] **Step 1: 在 chat.py 末尾添加历史会话路由**

在 `src/deep_paper_qa/routers/chat.py` 末尾追加：

```python
@router.get("/conversations")
async def list_conversations() -> dict:
    """历史会话列表"""
    import json
    from pathlib import Path

    log_dir = Path("logs")
    if not log_dir.exists():
        return {"conversations": []}

    conversations = []
    for f in sorted(log_dir.glob("*.jsonl"), reverse=True)[:50]:
        try:
            first_line = f.read_text(encoding="utf-8").split("\n", 1)[0]
            event = json.loads(first_line)
            conversations.append(
                {
                    "id": f.stem,
                    "file": f.name,
                    "started_at": event.get("ts", ""),
                    "first_message": event.get("content", "")[:100],
                }
            )
        except Exception:
            continue

    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    """单个会话的完整消息"""
    import json
    from pathlib import Path

    log_file = Path("logs") / f"{conversation_id}.jsonl"
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="会话不存在")

    events = []
    for line in log_file.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return {"id": conversation_id, "events": events}
```

- [ ] **Step 2: 运行全量测试**

运行: `uv run pytest tests/ -v`
预期: 全部通过

- [ ] **Step 3: 提交**

```bash
git add src/deep_paper_qa/routers/chat.py
git commit -m "feat: 历史会话列表和详情 API"
```

---

### Task 9: 全量测试 + lint + 验证

**Files:**
- 无新文件

- [ ] **Step 1: ruff lint**

运行: `uv run ruff check src/ tests/`
预期: 无错误

- [ ] **Step 2: ruff format**

运行: `uv run ruff format src/ tests/`

- [ ] **Step 3: 全量测试**

运行: `uv run pytest tests/ -v`
预期: 全部通过

- [ ] **Step 4: 手动验证 FastAPI 启动**

运行: `uv run uvicorn deep_paper_qa.api:app --port 8001`
访问: `http://localhost:8001/docs`（Swagger UI 应正常显示所有路由）

- [ ] **Step 5: 提交格式化修改（如有）**

```bash
git add -u
git commit -m "style: ruff format 格式化"
```

---

### Task 10: 更新 CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 在常用命令中添加 FastAPI 启动命令**

在 `CLAUDE.md` 的常用命令部分追加：

```bash
uv run uvicorn deep_paper_qa.api:app --reload   # 启动 FastAPI 后端 (http://localhost:8000)
```

- [ ] **Step 2: 更新架构说明**

在架构部分添加 FastAPI 后端说明，标注 Chainlit 和 FastAPI 并存：

```
- **api.py**: FastAPI 入口（新），SSE 事件流，REST API，与 Chainlit app.py 并存
- **routers/**: chat.py（聊天 SSE）、papers.py（论文浏览）、stats.py（统计数据）
```

- [ ] **Step 3: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md 添加 FastAPI 后端说明"
```
