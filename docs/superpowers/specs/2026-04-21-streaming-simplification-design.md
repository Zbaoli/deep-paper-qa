# Streaming 层简化设计

**日期**：2026-04-21
**分支**：experiment/deepagents
**目标**：消除当前 streaming 实现的过度设计，使架构对齐 LangGraph 官方推荐形态，降低维护成本。

---

## 背景

当前 `chat.py` 使用 `astream_events(version="v2")` 将 LangGraph 事件流转换为 SSE 事件，供前端 Vue 应用消费。实现过程中积累了三处冗余：

1. **双入口重复**：`src/deep_paper_qa/app.py` (Chainlit) 和 `src/deep_paper_qa/routers/chat.py` (FastAPI) 共享约 85 行几乎完全相同的事件处理代码。Chainlit 入口已被 FastAPI + Vue 前端取代，但未彻底退役。
2. **`sse_events.py` 抽象空转**：7 个专用事件构造函数本质是同一个 `ServerSentEvent(event=..., data=json.dumps(...))` 的一行包装，还存在两个从未被调用的死函数（`sse_route`、`sse_chart` ECharts 版）。
3. **事件循环"按工具名劫持"**：`ask_user` 和 `generate_chart` 的 UI 副作用（弹问答卡片、渲染 Plotly 图）写在事件循环里，靠 `if name == "ask_user"`、`if tool_name == "generate_chart" and artifact` 这种字符串比较触发。工具的 UI 行为和框架事件循环耦合在一起。

## 设计决策

### 决策 1：保留 `astream_events(version="v2")`，不切换到 `astream(stream_mode=[...])`

LangGraph 官方推荐的 `astream(stream_mode=[...])` 在本项目场景下不适用：

| 需求 | `astream_events(v2)` | `astream(stream_mode=[...])` |
|---|---|---|
| 每个工具独立的 run_id | ✓ 事件自带 run_id | ✗ ToolNode 整批输出，需自行合成 |
| 每个工具独立起止时间戳 | ✓ `on_tool_start` / `on_tool_end` 分别触发 | ✗ `updates` 只在节点结束时触发一次 |
| LLM token 流 | ✓ `on_chat_model_stream` | ✓ `messages` mode |
| 自定义事件透传 | ✓ `on_custom_event` | ✓ `custom` mode |

前端依赖 `run_id` 配对 `tool_start` / `tool_end` 卡片，依赖 `duration_ms` 显示耗时。换用 `stream_mode` 需要每个工具内手写开始事件 + 合成 run_id + 手动计时，复杂度反而升高。

**结论**：继续用 `astream_events(v2)`，过度设计不在这层，在它外面的包装。

### 决策 2：删除 Chainlit 入口（`app.py`）

Chainlit UI 已被 FastAPI + Vue 前端（`frontend/`）替代，`app.py` 不再是产品入口。保留它只会让每次改动都要在两处重复。

### 决策 3：`sse_events.py` 压缩到单个通用构造器

7 个专用函数 → 1 个 `sse(event, data)`。事件名和 payload 结构直接写在调用点，`grep` 可定位所有发送位置，无需类型系统。

### 决策 4：UI 专属事件由工具内部用 `get_stream_writer()` 发送

`ask_user` 和 `generate_chart` 的 UI 副作用（前端问答卡片、前端图表渲染）从事件循环迁移到工具内部。事件循环新增 `on_custom_event` 分支，按约定透传为 SSE 事件。

工具从"被动，等事件循环解读输出"变为"主动，声明自己要发什么 UI 信号"，循环和工具解耦。

### 决策 5：`generate_chart` 退出 `content_and_artifact` 格式

`content_and_artifact` 机制在本项目唯一的作用是绕开事件循环传 figure。改为 `get_stream_writer()` 后不再需要。工具回归普通 `@tool`，返回简短字符串给 LLM，figure 通过 writer 推给前端。

---

## 改动清单

### 删除

| 文件 | 说明 |
|---|---|
| `src/deep_paper_qa/app.py` | Chainlit 入口 |
| `pyproject.toml` 中的 `chainlit>=2.0` 依赖 | |
| `CLAUDE.md`、`README.md` 中的 Chainlit 启动命令 | |
| `.gitignore` 中的 `.chainlit/` 条目（可选） | |

### 重写

#### `src/deep_paper_qa/sse_events.py`

压缩为：

```python
"""SSE 事件构造"""

import json
from typing import Any

from sse_starlette.sse import ServerSentEvent


def sse(event: str, data: dict[str, Any] | None = None) -> ServerSentEvent:
    """构造 SSE 事件。data 为空时发空对象，前端 JSON.parse 不出错。"""
    return ServerSentEvent(event=event, data=json.dumps(data or {}, ensure_ascii=False))
```

#### `src/deep_paper_qa/routers/chat.py` 事件循环

```python
async for event in graph.astream_events(
    {"messages": [HumanMessage(content=req.message)]},
    config=config,
    version="v2",
):
    kind = event.get("event", "")
    name = event.get("name", "")

    if kind == "on_tool_start":
        run_id = event["run_id"]
        tool_input = event["data"].get("input", {})
        tool_timings[run_id] = (name, time.monotonic())
        tool_call_count += 1
        if name not in tools_used:
            tools_used.append(name)
        _conv_logger.log_tool_start(req.thread_id, name, tool_input)
        yield sse("tool_start", {"tool": name, "input": tool_input, "run_id": run_id})

    elif kind == "on_tool_end":
        run_id = event["run_id"]
        output = event["data"].get("output", "")
        if hasattr(output, "content"):
            output = output.content
        output_str = str(output)
        tool_name, start_t = tool_timings.pop(run_id, (name, time.monotonic()))
        duration_ms = int((time.monotonic() - start_t) * 1000)
        _conv_logger.log_tool_end(req.thread_id, tool_name, duration_ms, output_str)
        yield sse("tool_end", {
            "tool": tool_name,
            "output": output_str[:500],
            "duration_ms": duration_ms,
            "run_id": run_id,
        })

    elif kind == "on_chat_model_stream":
        chunk = event["data"].get("chunk")
        if chunk and chunk.content:
            yield sse("token", {"content": chunk.content})

    elif kind == "on_custom_event":
        # 工具内部通过 get_stream_writer() 发的 UI 事件
        # payload 约定 {"event": "<name>", "data": {...}}
        payload = event.get("data", {})
        yield sse(payload.get("event", "custom"), payload.get("data", {}))
```

变化：
- 从约 85 行瘦身到约 30 行
- 删除 `if name == "ask_user"` 分支（`ask_user` 现在作为普通工具处理）
- 删除 `if tool_name == "generate_chart" and artifact` 分支（`artifact` 机制已移除）
- 新增 `on_custom_event` 分支作为工具→前端信号的统一通道

### 小改

#### `src/deep_paper_qa/tools/ask_user.py`

在 `tool` 函数体开头添加 `get_stream_writer()` 调用，发送 `ask_user` 自定义事件。`asyncio.Event` 阻塞等待回复的机制完全不变。

```python
from langgraph.config import get_stream_writer

@tool
async def ask_user(summary: str, question: str, config: RunnableConfig) -> str:
    thread_id: str = config.get("configurable", {}).get("thread_id", "")

    writer = get_stream_writer()
    writer({"event": "ask_user", "data": {"question": question, "summary": summary}})

    # 下面的 asyncio.Event 等待逻辑完全不动
    event = asyncio.Event()
    _pending[thread_id] = {"event": event, "question": question, "summary": summary, "reply": ""}
    ...
```

#### `src/deep_paper_qa/tools/generate_chart.py`

```python
from langgraph.config import get_stream_writer

@tool  # 去掉 response_format="content_and_artifact"
async def generate_chart(chart_type, data, title, x_label="", y_label="") -> str:
    ...
    fig.update_layout(...)

    writer = get_stream_writer()
    writer({"event": "chart", "data": {"type": "plotly", "figure": fig.to_dict()}})

    return f"已生成 {chart_type} 图表：{title}"
```

变化：
- 装饰器 `@tool(response_format="content_and_artifact")` → `@tool`
- 返回类型 `tuple[str, str]` → `str`
- 错误分支返回 `tuple` → 返回 `str`（如 `f"错误：不支持的图表类型 '{chart_type}'..."`)

---

## 前端合约

### 不变

- 事件名：`tool_start`、`tool_end`、`token`、`chart`、`ask_user`、`done`、`error`
- payload 字段：`tool_start.{tool,input,run_id}`、`tool_end.{tool,output,duration_ms,run_id}`、`token.{content}`、`chart.{type,figure}`、`ask_user.{question,summary}`

### 向后兼容的清理

- 后端不再发 `route` 事件（本来就没发过，前端 `handleEvent` 里对应的 case 为死代码）
- `chart.type` 固定为 `"plotly"`（删除 echarts 分支，前端 case 仍可保留容错）
- `done` 事件 payload 可清空（前端未读取任何字段）

### 新行为

- `ask_user` 工具会出现在前端的工具时间线上（作为一次普通工具调用）。前端如不希望显示，可在 `ToolStep` 渲染时增加 `if tool === 'ask_user'` 过滤（非本 spec 范围）。

---

## 测试影响

- `tests/test_agent.py` 中验证 `agent` 可 `astream_events` 的断言保持有效（底层 API 未变）
- 若存在 `generate_chart` / `ask_user` 的单元测试，需要 mock `langgraph.config.get_stream_writer`。若没有测试，不新增（Spec 保持最小改动）
- Chainlit 相关的测试：全项目 `grep chainlit tests/` 无结果，无需清理

## 风险与缓解

1. **`chainlit` 依赖删除可能牵连 `uv.lock` 中其他包**
   缓解：`uv sync --all-extras` 重新解析锁文件，跑 `uv run pytest tests/` 确认无进口失败。

2. **`generate_chart` 从 `content_and_artifact` 退化后，LLM 上下文中 content 从"图表已生成"字符串变为同一字符串（无实质变化），但 artifact 相关的 agent prompt 假设需要核查**
   缓解：`grep -ri "artifact" src/ prompts.py`，确认 agent prompt 没有依赖 artifact 字段；研究管线的 prompts 未提及 artifact。

3. **`get_stream_writer()` 在非 streaming 上下文调用会 no-op 还是报错？**
   缓解：LangGraph 0.3 文档确认 `get_stream_writer()` 在无 stream 时返回 no-op writer。需要在实施阶段写一个最小 smoke test 验证。

4. **前端在接收 `ask_user` 工具的 `tool_start` / `tool_end` 事件后，可能同时渲染工具卡片和 ask_user 对话卡片**
   缓解：这是用户在设计块 3 中显式接受的行为（选项 A）。如果体验问题明显，前端补 1 行过滤即可，不在本 spec 范围。

## 成功标准

- `app.py` 及 `chainlit` 依赖完全移除，`grep chainlit` 全项目无残留（uv.lock 除外）
- `sse_events.py` 行数 ≤ 15
- `chat.py` 事件循环行数 ≤ 50（原约 85）
- 前端 `useChat.ts` 未修改，端到端功能（工具调用展示、token 流、图表渲染、ask_user 交互）回归通过
- `uv run pytest tests/ -v` 全部通过
- `uv run ruff check src/ tests/` 无报错

## 非目标

- 不重构 `agent.py` 的 graph 构建逻辑
- 不修改前端代码
- 不新增事件类型、不删除前端已定义的事件（如 `route`）
- 不引入 TypedDict / Pydantic 校验 SSE payload
- 不改 `execute_sql` / `search_abstracts` 等其它工具
