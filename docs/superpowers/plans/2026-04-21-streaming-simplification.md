# Streaming 层简化 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消除 streaming 实现的过度设计：删掉 Chainlit 入口，压缩 `sse_events.py`，让 `ask_user` / `generate_chart` 工具内部用 `get_stream_writer()` 自主发 UI 事件，事件循环通过统一的 `on_custom_event` 分支透传。

**Architecture:** 继续使用 `astream_events(version="v2")`（per-tool run_id / 计时无法被 `stream_mode` 替代）。`sse_events.py` 从 7 个专用函数压缩到单个 `sse(event, data)` 构造器。UI 专属事件迁移到工具内部，事件循环保持单通道的 `on_custom_event` 透传，按约定从 payload 提取 SSE event 名和 data。

**Tech Stack:** LangGraph 0.3 (`astream_events` v2, `langgraph.config.get_stream_writer`)，FastAPI + `sse-starlette`，Plotly（figure.to_dict），pytest + pytest-asyncio。

**Spec:** `docs/superpowers/specs/2026-04-21-streaming-simplification-design.md`

---

## 文件结构

**删除**
- `src/deep_paper_qa/app.py` — Chainlit 入口

**重写**
- `src/deep_paper_qa/sse_events.py` — 60 行 → ~15 行，单个 `sse(event, data)` 构造器
- `src/deep_paper_qa/routers/chat.py` — 事件循环瘦身，移除工具名劫持分支，新增 `on_custom_event` 透传
- `tests/test_sse_events.py` — 测 `sse()` 一个函数
- `tests/test_generate_chart.py` — 测 `_build_figure`（pure）和 mock writer 路径

**小改**
- `src/deep_paper_qa/tools/ask_user.py` — +3 行，调用 `get_stream_writer()`
- `src/deep_paper_qa/tools/generate_chart.py` — 返回类型 `tuple[str,str]` → `str`，装饰器去掉 `response_format`，写 writer
- `tests/test_ask_user_v2.py` — mock `get_stream_writer`
- `pyproject.toml`、`CLAUDE.md`、`README.md` — 删 chainlit 相关

**不改**
- `frontend/**` — SSE 合约保持兼容
- `src/deep_paper_qa/agent.py`、`src/deep_paper_qa/api.py` 及其它工具

---

## 前置准备

- [ ] **Step 0.1：确认在正确的分支和工作目录**

Run: `cd /Users/baoli/Documents/warehouse/deep_paper_qa && git status --short --branch | head -3`
Expected: 在 `experiment/deepagents` 分支；工作区有未提交的无关修改可以忽略。

- [ ] **Step 0.2：确认 baseline 测试可跑**

Run: `uv run pytest tests/ -v 2>&1 | tail -20`
Expected: 全部 PASS（或至少记录下当前 baseline，后续以此为参照）。如有 fail，记录下来，本计划不应让它们变多。

---

## Task 1：删除 Chainlit 入口和依赖

**Files:**
- Delete: `src/deep_paper_qa/app.py`
- Modify: `pyproject.toml`（删 chainlit 依赖）
- Modify: `CLAUDE.md`（删 chainlit 启动命令）
- Modify: `README.md`（删 chainlit 启动命令）

- [ ] **Step 1.1：删除 `app.py`**

Run: `rm src/deep_paper_qa/app.py`

- [ ] **Step 1.2：从 `pyproject.toml` 的 dependencies 中删除 chainlit**

修改 `pyproject.toml`，把这一行：

```toml
    "chainlit>=2.0",
```

删掉（注意保留列表里其它依赖，逗号结构不要错）。

- [ ] **Step 1.3：删除 CLAUDE.md 中的 chainlit 启动命令**

修改 `CLAUDE.md` 第 13 行附近，删除：

```
uv run chainlit run src/deep_paper_qa/app.py   # 启动 Chainlit (http://localhost:8000)
```

- [ ] **Step 1.4：删除 README.md 中的 chainlit 启动命令**

修改 `README.md` 第 57 行附近，删除：

```
uv run chainlit run src/deep_paper_qa/app.py
```

（如果周围有段落说明也一并删除/改写，保持文档通顺）

- [ ] **Step 1.5：重新同步依赖**

Run: `uv sync --all-extras`
Expected: 成功；`uv.lock` 会更新（移除 chainlit 及其独占依赖）。

- [ ] **Step 1.6：验证全项目无 chainlit 引用（除了 uv.lock 和历史文档）**

Run: `grep -rn "chainlit\|from deep_paper_qa.app\|import app" src/ tests/ scripts/ eval/ frontend/src/ 2>/dev/null | grep -v node_modules`
Expected: 无输出。

- [ ] **Step 1.7：跑全量测试**

Run: `uv run pytest tests/ -v 2>&1 | tail -30`
Expected: 全部 PASS（和 Step 0.2 一致）。

- [ ] **Step 1.8：提交**

```bash
git add src/deep_paper_qa/app.py pyproject.toml uv.lock CLAUDE.md README.md
git commit -m "$(cat <<'EOF'
refactor: 删除 Chainlit 入口和依赖

FastAPI + Vue 前端已完全接管 UI，Chainlit 入口 app.py 不再使用。
删除 app.py、chainlit 依赖、文档中的启动命令。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2：压缩 `sse_events.py` 到单个 `sse()` 构造器

**Files:**
- Rewrite: `src/deep_paper_qa/sse_events.py`
- Rewrite: `tests/test_sse_events.py`
- Modify: `src/deep_paper_qa/routers/chat.py`（只改 import 和调用点，行为完全不变）

**注意**：这一步行为零变化，只是改名换形式。SSE 协议对前端完全不变。

- [ ] **Step 2.1：先写新测试**

替换 `tests/test_sse_events.py` 全部内容：

```python
"""SSE 事件构造器测试"""

import json

from deep_paper_qa.sse_events import sse


class TestSseBuilder:
    """sse() 通用构造器测试"""

    def test_event_name_set(self) -> None:
        event = sse("token", {"content": "hi"})
        assert event.event == "token"

    def test_data_is_json(self) -> None:
        event = sse("tool_start", {"tool": "execute_sql", "run_id": "abc"})
        data = json.loads(event.data)
        assert data["tool"] == "execute_sql"
        assert data["run_id"] == "abc"

    def test_none_data_becomes_empty_object(self) -> None:
        event = sse("done")
        data = json.loads(event.data)
        assert data == {}

    def test_ensure_ascii_false_for_chinese(self) -> None:
        event = sse("token", {"content": "论文"})
        # data 字符串应保留中文，不应是 \u escaped
        assert "论文" in event.data
```

- [ ] **Step 2.2：运行测试确认失败（旧 sse_events.py 还没改）**

Run: `uv run pytest tests/test_sse_events.py -v`
Expected: FAIL 或 ERROR — `ImportError: cannot import name 'sse'`。

- [ ] **Step 2.3：重写 `sse_events.py`**

替换 `src/deep_paper_qa/sse_events.py` 全部内容：

```python
"""SSE 事件构造"""

import json
from typing import Any

from sse_starlette.sse import ServerSentEvent


def sse(event: str, data: dict[str, Any] | None = None) -> ServerSentEvent:
    """构造 SSE 事件。data 为空时发空对象，前端 JSON.parse 不出错。"""
    return ServerSentEvent(event=event, data=json.dumps(data or {}, ensure_ascii=False))
```

- [ ] **Step 2.4：运行新测试确认通过**

Run: `uv run pytest tests/test_sse_events.py -v`
Expected: 4 个用例全部 PASS。

- [ ] **Step 2.5：更新 `chat.py` 的 import 和调用点（行为不变）**

修改 `src/deep_paper_qa/routers/chat.py`：

**替换 import（约 14-22 行）**：

```python
from deep_paper_qa.sse_events import sse
```

**替换事件循环里的调用**：

| 旧写法 | 新写法 |
|---|---|
| `yield sse_ask_user(question, summary)` | `yield sse("ask_user", {"question": question, "summary": summary})` |
| `yield sse_tool_start(name, tool_input, run_id)` | `yield sse("tool_start", {"tool": name, "input": tool_input, "run_id": run_id})` |
| `yield sse_tool_end(tool_name, out, duration_ms, run_id)` | `yield sse("tool_end", {"tool": tool_name, "output": out, "duration_ms": duration_ms, "run_id": run_id})` |
| `yield sse_chart_plotly(fig.to_dict())` | `yield sse("chart", {"type": "plotly", "figure": fig.to_dict()})` |
| `yield sse_token(chunk.content)` | `yield sse("token", {"content": chunk.content})` |
| `yield sse_done(total_ms, tool_call_count)` | `yield sse("done", {"total_ms": total_ms, "tool_calls": tool_call_count})` |
| `yield sse_error(f"{type(e).__name__}: {e}")` | `yield sse("error", {"message": f"{type(e).__name__}: {e}"})` |

替换后 `tool_end` 发送里原本的截断表达式简化一下：`output_str[:500] if len(output_str) > 500 else output_str` → 直接 `output_str[:500]`（语义等价，切片对短字符串不产生副作用）。

- [ ] **Step 2.6：跑全量测试**

Run: `uv run pytest tests/ -v 2>&1 | tail -20`
Expected: 全 PASS（包括新的 `test_sse_events.py`）。

- [ ] **Step 2.7：Lint**

Run: `uv run ruff check src/deep_paper_qa/sse_events.py src/deep_paper_qa/routers/chat.py tests/test_sse_events.py`
Expected: 无报错。

- [ ] **Step 2.8：提交**

```bash
git add src/deep_paper_qa/sse_events.py src/deep_paper_qa/routers/chat.py tests/test_sse_events.py
git commit -m "$(cat <<'EOF'
refactor: sse_events 压缩为单个 sse() 构造器

7 个专用函数（含 2 个死函数 sse_route、sse_chart echarts 版）→
1 个通用 sse(event, data)。事件名和 payload 结构直接写在调用点，
grep 可定位所有发送位置。SSE 协议对前端完全不变。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3：`chat.py` 事件循环增加 `on_custom_event` 透传分支

**Files:**
- Modify: `src/deep_paper_qa/routers/chat.py`（追加一个分支，不删任何现有逻辑）

**注意**：这是纯增量变更，为后续 Task 4、5 铺路。本任务结束后，如果有工具用 `get_stream_writer()` 发事件，循环会透传；目前还没有工具这么做，所以行为上不变化。

- [ ] **Step 3.1：修改 `chat.py` 事件循环，追加 `on_custom_event` 分支**

在 `src/deep_paper_qa/routers/chat.py` 的 `elif kind == "on_chat_model_stream":` 分支之后（约第 138 行 `yield sse_token(...)` 之后），加一个新分支：

```python
            elif kind == "on_custom_event":
                # 工具内部通过 get_stream_writer() 发的 UI 事件
                # payload 约定 {"event": "<name>", "data": {...}}
                payload = event.get("data", {})
                if isinstance(payload, dict) and "event" in payload:
                    yield sse(payload["event"], payload.get("data", {}))
```

完整对齐后，`async for` 循环内的最后一个 `elif` 就是这段新分支。

- [ ] **Step 3.2：跑全量测试验证无回归**

Run: `uv run pytest tests/ -v 2>&1 | tail -20`
Expected: 全 PASS。

- [ ] **Step 3.3：Lint**

Run: `uv run ruff check src/deep_paper_qa/routers/chat.py`
Expected: 无报错。

- [ ] **Step 3.4：提交**

```bash
git add src/deep_paper_qa/routers/chat.py
git commit -m "$(cat <<'EOF'
refactor: chat 事件循环追加 on_custom_event 透传分支

作为后续工具内 get_stream_writer() 迁移的统一接入点。
当前尚无工具使用，行为不变。

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4：`generate_chart` 改用 writer，退出 `content_and_artifact`

**Files:**
- Modify: `src/deep_paper_qa/tools/generate_chart.py`
- Modify: `tests/test_generate_chart.py`
- Modify: `src/deep_paper_qa/routers/chat.py`（移除 artifact 处理分支）

**注意**：本任务合并了工具改造和 chat.py 的 artifact 分支移除。两者必须一起提交——否则中间状态下前端收不到 chart。

- [ ] **Step 4.1：改测试：从"断言 content_and_artifact 返回"改为"断言 str 返回 + writer 被调用"**

替换 `tests/test_generate_chart.py` 全部内容为：

```python
"""generate_chart 工具测试"""

from unittest.mock import MagicMock, patch

import plotly.graph_objects as go


class TestBuildFigure:
    """纯函数 _build_figure 单元测试（不经过 get_stream_writer）"""

    def test_bar_figure(self) -> None:
        from deep_paper_qa.tools.generate_chart import _build_figure

        fig = _build_figure("bar", {"x": ["2020", "2021"], "y": [10, 25]})
        assert isinstance(fig, go.Figure)
        assert fig.data[0].type == "bar"

    def test_pie_figure(self) -> None:
        from deep_paper_qa.tools.generate_chart import _build_figure

        fig = _build_figure("pie", {"labels": ["ACL", "NeurIPS"], "values": [100, 200]})
        assert fig.data[0].type == "pie"

    def test_mismatched_lengths_raises(self) -> None:
        """x/y 长度不一致应抛 ValueError"""
        import pytest
        from deep_paper_qa.tools.generate_chart import _build_figure

        with pytest.raises(ValueError, match="长度不一致"):
            _build_figure("bar", {"x": ["a"], "y": [1, 2]})


class TestGenerateChartTool:
    """tool 入口测试：mock get_stream_writer"""

    @patch("deep_paper_qa.tools.generate_chart.get_stream_writer")
    async def test_bar_chart_returns_str_and_writes_event(self, mock_writer_factory) -> None:
        """生成柱状图：返回 str，通过 writer 发 chart 事件"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        writer = MagicMock()
        mock_writer_factory.return_value = writer

        result = await generate_chart.ainvoke(
            {
                "chart_type": "bar",
                "data": {"x": ["2020", "2021"], "y": [10, 25]},
                "title": "论文趋势",
            }
        )

        assert isinstance(result, str)
        assert "已生成" in result and "bar" in result
        # writer 被调用一次，payload 结构符合约定
        assert writer.call_count == 1
        (payload,), _ = writer.call_args
        assert payload["event"] == "chart"
        assert payload["data"]["type"] == "plotly"
        assert "figure" in payload["data"]

    @patch("deep_paper_qa.tools.generate_chart.get_stream_writer")
    async def test_invalid_chart_type_returns_error_str(self, mock_writer_factory) -> None:
        """不支持的图表类型返回错误字符串，不调用 writer"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        writer = MagicMock()
        mock_writer_factory.return_value = writer

        result = await generate_chart.ainvoke(
            {
                "chart_type": "unknown",
                "data": {"x": [1], "y": [1]},
                "title": "test",
            }
        )

        assert isinstance(result, str)
        assert "不支持" in result
        assert writer.call_count == 0

    @patch("deep_paper_qa.tools.generate_chart.get_stream_writer")
    async def test_mismatched_lengths_returns_error_str(self, mock_writer_factory) -> None:
        """x/y 长度不一致返回错误字符串，不调用 writer"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        writer = MagicMock()
        mock_writer_factory.return_value = writer

        result = await generate_chart.ainvoke(
            {
                "chart_type": "bar",
                "data": {"x": ["2020", "2021"], "y": [10]},
                "title": "test",
            }
        )

        assert isinstance(result, str)
        assert "错误" in result or "长度" in result
        assert writer.call_count == 0
```

- [ ] **Step 4.2：跑新测试，确认失败（工具还没改）**

Run: `uv run pytest tests/test_generate_chart.py -v`
Expected: 多数用例 FAIL — 因为当前 `generate_chart` 返回 tuple、没有 `get_stream_writer` 调用。

- [ ] **Step 4.3：重写 `generate_chart.py`**

替换 `src/deep_paper_qa/tools/generate_chart.py` 全部内容：

```python
"""通用数据可视化工具：根据数据和图表类型生成 Plotly 图表"""

import plotly.graph_objects as go
from langchain_core.tools import tool
from langgraph.config import get_stream_writer
from loguru import logger

# 支持的图表类型
SUPPORTED_TYPES = {"bar", "line", "scatter", "pie", "heatmap", "area", "box"}

# 与前端 Academic Observatory 主题一致的配色方案
_DEFAULT_LAYOUT = {
    "template": "plotly_dark",
    "height": 320,
    "font": {"size": 13, "color": "#e8eaf0", "family": "system-ui, sans-serif"},
    "margin": {"l": 50, "r": 30, "t": 50, "b": 50},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "title_font": {"size": 15, "color": "#e8eaf0"},
    "xaxis": {"gridcolor": "rgba(255,255,255,0.06)", "zerolinecolor": "rgba(255,255,255,0.06)"},
    "yaxis": {"gridcolor": "rgba(255,255,255,0.06)", "zerolinecolor": "rgba(255,255,255,0.06)"},
    "legend": {"font": {"color": "#8a92a8"}},
}

# 与前端 accent 配色对齐
_COLORS = ["#f0a030", "#4ecdc4", "#e8637a", "#8b5cf6", "#3b82f6", "#10b981", "#06b6d4"]


@tool
async def generate_chart(
    chart_type: str,
    data: dict,
    title: str,
    x_label: str = "",
    y_label: str = "",
) -> str:
    """根据数据生成 Plotly 图表。

    支持的图表类型：bar（柱状图）、line（折线图）、scatter（散点图）、
    pie（饼图）、heatmap（热力图）、area（面积图）、box（箱线图）。

    Args:
        chart_type: 图表类型
        data: 图表数据。xy 类图表用 {"x": [...], "y": [...]}；
              饼图用 {"labels": [...], "values": [...]}；
              箱线图用 {"y": [...]} 或 {"groups": {"组名": [数值...]}}
        title: 图表标题
        x_label: X 轴标签（可选）
        y_label: Y 轴标签（可选）

    Returns:
        简短确认文本（LLM 可见）。figure 通过 get_stream_writer() 直接推给前端，
        不进入 LLM 上下文。
    """
    chart_type = chart_type.lower().strip()
    if chart_type not in SUPPORTED_TYPES:
        return f"错误：不支持的图表类型 '{chart_type}'，支持的类型：{', '.join(sorted(SUPPORTED_TYPES))}"

    try:
        fig = _build_figure(chart_type, data)
    except ValueError as e:
        return f"错误：{e}"

    fig.update_layout(
        title=title,
        xaxis_title=x_label or None,
        yaxis_title=y_label or None,
        **_DEFAULT_LAYOUT,
    )

    # figure 通过 SSE custom 事件推给前端，避免污染 LLM 上下文
    writer = get_stream_writer()
    writer({"event": "chart", "data": {"type": "plotly", "figure": fig.to_dict()}})

    logger.info("generate_chart | type={} | title={}", chart_type, title)
    return f"已生成 {chart_type} 图表：{title}"


def _build_figure(chart_type: str, data: dict) -> go.Figure:
    """根据图表类型和数据构建 Plotly Figure"""
    if chart_type == "pie":
        labels = data.get("labels", [])
        values = data.get("values", [])
        if len(labels) != len(values):
            raise ValueError(f"labels 和 values 长度不一致：{len(labels)} vs {len(values)}")
        return go.Figure(data=[go.Pie(labels=labels, values=values, marker_colors=_COLORS)])

    if chart_type == "box":
        groups = data.get("groups", {})
        if groups:
            traces = [go.Box(y=vals, name=name) for name, vals in groups.items()]
            return go.Figure(data=traces)
        return go.Figure(data=[go.Box(y=data.get("y", []))])

    if chart_type == "heatmap":
        z = data.get("z", data.get("y", []))
        x = data.get("x", None)
        y_labels = data.get("y_labels", None)
        return go.Figure(data=[go.Heatmap(z=z, x=x, y=y_labels, colorscale="Blues")])

    # xy 类图表：bar, line, scatter, area
    x = data.get("x", [])
    y = data.get("y", [])
    if len(x) != len(y):
        raise ValueError(f"x 和 y 数据长度不一致：{len(x)} vs {len(y)}")

    trace_map = {
        "bar": go.Bar(x=x, y=y, marker_color=_COLORS[0]),
        "line": go.Scatter(x=x, y=y, mode="lines+markers", line={"color": _COLORS[0]}),
        "scatter": go.Scatter(x=x, y=y, mode="markers", marker={"color": _COLORS[0], "size": 8}),
        "area": go.Scatter(x=x, y=y, fill="tozeroy", line={"color": _COLORS[0]}),
    }
    return go.Figure(data=[trace_map[chart_type]])
```

- [ ] **Step 4.4：跑新测试确认通过**

Run: `uv run pytest tests/test_generate_chart.py -v`
Expected: 6 个用例全部 PASS。

- [ ] **Step 4.5：移除 `chat.py` 里的 artifact 处理分支**

在 `src/deep_paper_qa/routers/chat.py` 的 `on_tool_end` 分支里：

**删除**这几行（原约 102-105 行的 artifact 提取，以及约 124-132 行的 generate_chart 特殊分支）：

```python
                    # 先提取 artifact（content_and_artifact 格式），再转为字符串
                    artifact = getattr(output, "artifact", None)
```

```python
                    # generate_chart 通过 artifact 传递 Plotly JSON，避免污染 LLM 上下文
                    if tool_name == "generate_chart" and artifact:
                        try:
                            import plotly.io as pio

                            fig = pio.from_json(artifact)
                            yield sse("chart", {"type": "plotly", "figure": fig.to_dict()})
                        except Exception as chart_err:
                            logger.warning("Plotly artifact 解析失败: {}", chart_err)
```

保留 `if hasattr(output, "content"): output = output.content`（这对 LangChain ToolMessage 的通用解包仍然需要，与 content_and_artifact 无关）。

- [ ] **Step 4.6：跑全量测试**

Run: `uv run pytest tests/ -v 2>&1 | tail -20`
Expected: 全 PASS。

- [ ] **Step 4.7：Lint**

Run: `uv run ruff check src/deep_paper_qa/tools/generate_chart.py src/deep_paper_qa/routers/chat.py tests/test_generate_chart.py`
Expected: 无报错。

- [ ] **Step 4.8：提交**

```bash
git add src/deep_paper_qa/tools/generate_chart.py src/deep_paper_qa/routers/chat.py tests/test_generate_chart.py
git commit -m "$(cat <<'EOF'
refactor: generate_chart 改用 get_stream_writer 发 chart 事件

- 装饰器从 @tool(response_format="content_and_artifact") 退回 @tool
- 返回类型从 tuple[str, str] 改为 str
- figure 通过 writer 推到 SSE，不再走 LangChain artifact
- 移除 chat.py 事件循环中的 artifact 提取和 generate_chart 特殊分支
- 测试改为验证 writer 调用 + _build_figure 纯函数

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5：`ask_user` 改用 writer，移除 `chat.py` 中的 ask_user 特殊分支

**Files:**
- Modify: `src/deep_paper_qa/tools/ask_user.py`
- Modify: `tests/test_ask_user_v2.py`
- Modify: `src/deep_paper_qa/routers/chat.py`（移除 ask_user 特殊分支）

**注意**：同 Task 4，工具改造和 chat.py 分支移除需要一起提交——否则中间状态下前端收不到 `ask_user` 事件。

- [ ] **Step 5.1：改测试，mock `get_stream_writer`，新增一个断言 writer 被调用的用例**

修改 `tests/test_ask_user_v2.py`。保留现有所有测试结构和断言，做三处修改：

1. 在顶部 import 增加：

```python
from unittest.mock import MagicMock, patch
```

2. 现有 5 个测试中，凡是直接或间接调用 `ask_user.ainvoke(...)` 的（`test_submit_reply_wakes_up_ask_user`、`test_get_pending_question`、`test_concurrent_threads_isolated`），在函数体顶部加 `@patch` 装饰器：

```python
    @pytest.mark.asyncio
    @patch("deep_paper_qa.tools.ask_user.get_stream_writer")
    async def test_submit_reply_wakes_up_ask_user(self, mock_writer_factory) -> None:
        mock_writer_factory.return_value = MagicMock()
        # ...（原逻辑不变）
```

顺序是 `@pytest.mark.asyncio` 在上、`@patch` 在下；patch 注入的 `mock_writer_factory` 作为方法第二个参数。

`test_timeout_returns_default` 和 `test_no_pending_question` 不需要 patch（它们不走 `ask_user.ainvoke`）。

3. 新增一个用例 `test_ask_user_emits_custom_event` 放在类尾：

```python
    @pytest.mark.asyncio
    @patch("deep_paper_qa.tools.ask_user.get_stream_writer")
    async def test_ask_user_emits_custom_event(self, mock_writer_factory) -> None:
        """ask_user 通过 get_stream_writer 发送 ask_user 自定义事件"""
        writer = MagicMock()
        mock_writer_factory.return_value = writer

        async def simulate_user_reply() -> None:
            await asyncio.sleep(0.05)
            submit_reply("thread-event", "OK")

        task = asyncio.create_task(simulate_user_reply())
        await ask_user.ainvoke(
            {"summary": "阶段摘要", "question": "是否继续？"},
            config=_make_config("thread-event"),
        )
        await task

        assert writer.call_count == 1
        (payload,), _ = writer.call_args
        assert payload["event"] == "ask_user"
        assert payload["data"]["question"] == "是否继续？"
        assert payload["data"]["summary"] == "阶段摘要"
```

- [ ] **Step 5.2：跑新测试确认失败（工具还没改）**

Run: `uv run pytest tests/test_ask_user_v2.py -v`
Expected: `test_ask_user_emits_custom_event` FAIL（`get_stream_writer` 在 ask_user.py 中未 import）；其它用例可能仍 PASS（因为 patch 目标不存在时行为取决于 strict 设置，不保证）。

- [ ] **Step 5.3：修改 `ask_user.py`，加 `get_stream_writer` 调用**

修改 `src/deep_paper_qa/tools/ask_user.py`：

1. 顶部 import 增加：

```python
from langgraph.config import get_stream_writer
```

2. 在 `@tool` 装饰的 `async def ask_user(...)` 函数体开头、日志 `logger.info("ask_user | thread={} | summary_len=...")` 之后，加：

```python
    # 通知前端显示问答卡片
    writer = get_stream_writer()
    writer({"event": "ask_user", "data": {"question": question, "summary": summary}})
```

其余逻辑（asyncio.Event 等待、超时、回复提取）完全不动。

- [ ] **Step 5.4：跑测试确认通过**

Run: `uv run pytest tests/test_ask_user_v2.py -v`
Expected: 6 个用例全部 PASS。

- [ ] **Step 5.5：移除 `chat.py` 中的 ask_user 特殊分支**

修改 `src/deep_paper_qa/routers/chat.py`：

1. 在 `on_tool_start` 分支里，**删除**：

```python
                    if name == "ask_user":
                        summary = tool_input.get("summary", "")
                        question = tool_input.get("question", "")
                        yield sse("ask_user", {"question": question, "summary": summary})
                    else:
                        yield sse("tool_start", {"tool": name, "input": tool_input, "run_id": run_id})
```

**替换为**（无条件发 tool_start）：

```python
                    yield sse("tool_start", {"tool": name, "input": tool_input, "run_id": run_id})
```

2. 在 `on_tool_end` 分支里，**删除** `if tool_name != "ask_user":` 包装（让 ask_user 也正常发 tool_end）：

```python
                    if tool_name != "ask_user":
                        yield sse(
                            "tool_end",
                            {
                                "tool": tool_name,
                                "output": output_str[:500],
                                "duration_ms": duration_ms,
                                "run_id": run_id,
                            },
                        )
```

**替换为**（去掉 `if tool_name != "ask_user":` 这层 guard，只保留里面的 yield）：

```python
                    yield sse(
                        "tool_end",
                        {
                            "tool": tool_name,
                            "output": output_str[:500],
                            "duration_ms": duration_ms,
                            "run_id": run_id,
                        },
                    )
```

- [ ] **Step 5.6：跑全量测试**

Run: `uv run pytest tests/ -v 2>&1 | tail -20`
Expected: 全 PASS。

- [ ] **Step 5.7：Lint**

Run: `uv run ruff check src/deep_paper_qa/tools/ask_user.py src/deep_paper_qa/routers/chat.py tests/test_ask_user_v2.py`
Expected: 无报错。

- [ ] **Step 5.8：提交**

```bash
git add src/deep_paper_qa/tools/ask_user.py src/deep_paper_qa/routers/chat.py tests/test_ask_user_v2.py
git commit -m "$(cat <<'EOF'
refactor: ask_user 改用 get_stream_writer 发 ask_user 事件

- 在 tool 函数体内通过 writer 主动发 ask_user 自定义事件
- 移除 chat.py 事件循环中按 tool 名劫持 ask_user 的两处分支
- ask_user 现在作为普通工具正常出现在前端工具时间线
- 测试 mock get_stream_writer 并新增 writer 调用断言

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6：端到端手动验证

**Files:** 无改动，只验证。

前面所有任务只靠 pytest 保证了单元级别正确。这一步用真实后端 + 前端做一次烟测，确认 SSE 合约对前端仍然兼容。

- [ ] **Step 6.1：启动 FastAPI 后端**

Run: `uv run uvicorn deep_paper_qa.api:app --reload` （另开终端执行；本任务检查启动是否报错）
Expected: 无 ImportError / 启动异常；日志正常打到 stdout。

- [ ] **Step 6.2：启动前端（另一终端）**

Run: `cd frontend && npm run dev`
Expected: Vite 启动，无报错。

- [ ] **Step 6.3：浏览器端手动测试三条流**

打开 `http://localhost:5173`（或 Vite 输出的地址），依次测：

1. **SQL 查询流**：问"2024 年 NeurIPS 接收多少篇"。验证：工具时间线显示 `execute_sql` 卡片，LLM 正确流式输出答案。
2. **图表生成流**：问"画一张 2020-2024 年 ACL 论文数量的柱状图"。验证：工具时间线显示 `execute_sql` + `generate_chart` 卡片；消息区域下方渲染出 Plotly 图表。
3. **ask_user 交互流**（如果能触发到深度研究管线）：触发到 `ask_user` 时，验证：前端弹出问答卡片，工具时间线里**也**有一个 `ask_user` 卡片（这是本次重构刻意接受的行为变化）。回复后流程继续。

如果任何一条流的 UI 表现与重构前有实质差异（图表不显示、ask_user 卡片不弹出、token 不流），回到对应 Task 排查。

- [ ] **Step 6.4：Lint + 测试最终扫一遍**

Run: `uv run ruff check src/ tests/ && uv run pytest tests/ -v`
Expected: 全 PASS。

- [ ] **Step 6.5：如有文档/CLAUDE.md 描述需要更新，跟一个 docs commit**

检查 `CLAUDE.md` 里的"架构"小节是否还在用"Chainlit UI (app.py)"字样；如还有残留，改为 "Vue 前端 + FastAPI (api.py)"。如需改动：

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md 架构图同步移除 Chainlit"
```

如无残留，跳过。

---

## Self-Review 结果（plan 作者）

**Spec 覆盖**
- 决策 1（保留 astream_events）：未改动底层 API，决策体现在 Task 3 追加 on_custom_event 而非切换 stream_mode。✓
- 决策 2（删 Chainlit）：Task 1 完整覆盖。✓
- 决策 3（sse_events 压缩）：Task 2 完整覆盖。✓
- 决策 4（工具内 writer）：Task 4（generate_chart）+ Task 5（ask_user）覆盖。✓
- 决策 5（退出 content_and_artifact）：Task 4 覆盖。✓
- 风险 1（uv.lock 牵连）：Task 1 Step 1.5 + 1.7 覆盖。✓
- 风险 2（artifact prompt 依赖）：spec 已 grep 确认无，plan 不重复。✓
- 风险 3（get_stream_writer 非 graph 行为）：plan 编写前已验证会抛 RuntimeError，Task 4 / 5 均用 mock 处理。✓
- 风险 4（ask_user 出现在时间线）：Task 5 Step 5.5 明确改变，Task 6 Step 6.3 明确接受。✓

**占位符扫描**：无 TBD / TODO。所有 code block 写完整内容。

**类型一致**：所有 `sse("event_name", {"key": value})` 的 event name 与前端 `useChat.ts` 中的 `switch (event)` 分支逐一对齐（tool_start / tool_end / token / chart / ask_user / done / error）。payload 字段与 `handleEvent` 中读取的字段一致。

---

## 执行建议

每个 Task 之间建议人工 review 一次 diff 再进下一个 Task，便于出问题时回退。

Task 4 / Task 5 的 commit 涉及工具 + chat.py 两个模块同时变，是刻意合并——分拆会让前端在中间状态下丢事件。
