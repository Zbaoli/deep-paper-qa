# DeepAgents 重写实验 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `experiment/deepagents` 分支上，用 LangChain DeepAgents 替换手动路由+多管线架构，让单一 agent 自主规划调度，保留全部工具和领域知识。

**Architecture:** 删除 6 路路由和 5 条管线（general/research/trend/reading/compare），用 `create_deep_agent()` 构建单一 agent。保留 6 个现有工具，新增 `generate_chart` 通用可视化工具。System prompt 合并领域知识但不约束行为。

**Tech Stack:** deepagents, langgraph, langchain-core, langchain-openai, plotly, chainlit, asyncpg, aiohttp

**Spec:** `docs/superpowers/specs/2026-04-08-deepagents-rewrite-design.md`

---

### Task 1: 创建实验分支并添加依赖

**Files:**
- Modify: `pyproject.toml:9` (dependencies list)

- [ ] **Step 1: 创建分支**

```bash
git checkout -b experiment/deepagents
```

- [ ] **Step 2: 添加 deepagents 依赖**

在 `pyproject.toml` 的 `dependencies` 列表中添加 `deepagents`：

```python
dependencies = [
    "deepagents>=0.1",
    "langgraph>=0.3",
    "langchain-openai>=0.3",
    "langchain-core>=0.3",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "chainlit>=2.0",
    "loguru>=0.7",
    "python-dotenv>=1.0",
    "asyncpg>=0.30",
    "aiohttp>=3.9",
    "plotly>=6.0",
]
```

- [ ] **Step 3: 安装依赖**

```bash
uv sync --all-extras
```

Expected: 安装成功，`deepagents` 包可用。

- [ ] **Step 4: 验证 deepagents 可导入**

```bash
uv run python -c "from deepagents import create_deep_agent; print('OK')"
```

Expected: 输出 `OK`。

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: 添加 deepagents 依赖"
```

---

### Task 2: 新建 generate_chart 工具

**Files:**
- Create: `src/deep_paper_qa/tools/generate_chart.py`
- Create: `tests/test_generate_chart.py`

- [ ] **Step 1: 写 generate_chart 的测试**

创建 `tests/test_generate_chart.py`：

```python
"""generate_chart 工具测试"""

import json

import pytest


class TestGenerateChart:
    """通用图表生成工具测试"""

    async def test_bar_chart(self) -> None:
        """生成柱状图"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "bar",
                "data": {"x": ["2020", "2021", "2022"], "y": [10, 25, 40]},
                "title": "论文数量趋势",
                "x_label": "年份",
                "y_label": "数量",
            }
        )
        assert "<!--plotly:" in result
        assert "-->" in result
        # 提取 JSON 并验证可解析
        chart_json = result.split("<!--plotly:")[1].split("-->")[0]
        fig_data = json.loads(chart_json)
        assert "data" in fig_data
        assert "layout" in fig_data

    async def test_line_chart(self) -> None:
        """生成折线图"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "line",
                "data": {"x": ["2020", "2021", "2022"], "y": [10, 25, 40]},
                "title": "增长趋势",
            }
        )
        assert "<!--plotly:" in result

    async def test_pie_chart(self) -> None:
        """生成饼图"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "pie",
                "data": {"labels": ["ACL", "NeurIPS", "ICLR"], "values": [100, 200, 150]},
                "title": "会议分布",
            }
        )
        assert "<!--plotly:" in result

    async def test_invalid_chart_type(self) -> None:
        """不支持的图表类型返回错误信息"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "unknown",
                "data": {"x": [1], "y": [1]},
                "title": "test",
            }
        )
        assert "不支持" in result or "error" in result.lower()

    async def test_mismatched_data_lengths(self) -> None:
        """x/y 长度不一致返回错误信息"""
        from deep_paper_qa.tools.generate_chart import generate_chart

        result = await generate_chart.ainvoke(
            {
                "chart_type": "bar",
                "data": {"x": ["2020", "2021"], "y": [10]},
                "title": "test",
            }
        )
        assert "长度" in result or "mismatch" in result.lower() or "error" in result.lower()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_generate_chart.py -v
```

Expected: FAIL，`ModuleNotFoundError: No module named 'deep_paper_qa.tools.generate_chart'`

- [ ] **Step 3: 实现 generate_chart 工具**

创建 `src/deep_paper_qa/tools/generate_chart.py`：

```python
"""通用数据可视化工具：根据数据和图表类型生成 Plotly 图表"""

import json

import plotly.graph_objects as go
from langchain_core.tools import tool
from loguru import logger

# 支持的图表类型
SUPPORTED_TYPES = {"bar", "line", "scatter", "pie", "heatmap", "area", "box"}

# 中文友好默认布局
_DEFAULT_LAYOUT = {
    "template": "plotly_dark",
    "height": 400,
    "font": {"size": 14},
    "margin": {"l": 60, "r": 40, "t": 60, "b": 60},
}

# 默认配色
_COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4"]


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
        包含 Plotly JSON 的字符串，格式为 <!--plotly:{json}-->
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

    chart_json = fig.to_json()
    logger.info("generate_chart | type={} | title={}", chart_type, title)
    return f"<!--plotly:{chart_json}-->"


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

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_generate_chart.py -v
```

Expected: 5 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/deep_paper_qa/tools/generate_chart.py tests/test_generate_chart.py
git commit -m "feat: 新增 generate_chart 通用可视化工具"
```

---

### Task 3: 重写 prompts.py — 合并为单一 SYSTEM_PROMPT

**Files:**
- Rewrite: `src/deep_paper_qa/prompts.py`

- [ ] **Step 1: 重写 prompts.py**

将 `src/deep_paper_qa/prompts.py` 替换为以下内容：

```python
"""DeepAgents 单一 System Prompt — 领域知识 + 工具说明"""

SYSTEM_PROMPT = """你是一个 AI 科研论文智能问答助手。你可以访问一个包含 81,913 篇 AI 会议论文（2020-2025）的数据库，并能使用多种工具回答用户问题。

## 数据库 Schema

```sql
CREATE TABLE papers (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    abstract    TEXT,
    year        INT NOT NULL,       -- 范围: 2020-2025
    conference  TEXT,               -- 枚举: ACL, EMNLP, NeurIPS, ICLR, ICML, AAAI, IJCAI, KDD, NAACL, WWW
    venue_type  TEXT,               -- 枚举: conference, journal, preprint
    authors     TEXT[],             -- PostgreSQL 数组，查询用 ANY()
    citations   INT DEFAULT 0,
    url         TEXT,
    pdf_url     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

## SQL 规范

- 只允许 SELECT 查询，结果最多 20 行
- authors 是 TEXT[] 数组：用 `WHERE 'Name' = ANY(authors)`，禁止用 LIKE
- conference 名称大小写敏感：NeurIPS（非 neurips）、ACL、EMNLP 等
- directions 字段数据质量差，**禁止使用**
- 全文检索语法：
  ```sql
  WHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))
        @@ to_tsquery('english', '查询表达式')
  ```
  操作符：& (AND), | (OR), <-> (相邻), ! (NOT), :* (前缀)

## 关键词扩展规则

全文检索前，将同一概念扩展为多种英文表述，用 | (OR) 连接：
- RAG → `'RAG | (retrieval <-> augment:*) | (retrieval <-> generat:*)'`
- LLM Agent → `'(LLM <-> agent:*) | (language <-> model <-> agent:*) | (autonomous <-> agent:*)'`
- 知识蒸馏 → `'(knowledge <-> distill:*) | (model <-> compress:*)'`

## 工具使用策略

你有 7 个工具：

1. **execute_sql** — 查询数据库元数据（统计、排名、筛选、作者查询）
2. **search_abstracts** — 搜索论文标题和摘要（fulltext 全文检索 / vector 语义检索）
3. **search_arxiv** — 搜索 arXiv 预印本（适用于最新论文、数据库未收录论文）
4. **search_semantic_scholar** — 搜索 Semantic Scholar（引用数据、跨库搜索）
5. **search_web** — 搜索互联网（非论文信息：会议日期、行业动态、博客）
6. **ask_user** — 向用户提问澄清（仅在问题歧义或方向不明确时使用，执行过程中不要打断用户）
7. **generate_chart** — 生成数据可视化图表（bar/line/scatter/pie/heatmap/area/box）

### 优先级
- **本地优先**：优先用 execute_sql 和 search_abstracts 查询本地数据库
- **联网补充**：本地结果不足（< 3 条）或用户询问数据库范围外内容时，用外部搜索补充
- **可视化**：涉及数量统计、趋势分析、分布对比时，先用 execute_sql 获取数据，再用 generate_chart 生成图表

### 工具选择
- 统计/计数/排名 → execute_sql
- 按作者查论文 → execute_sql + ANY(authors)
- 查论文内容/方法 → search_abstracts（先 fulltext，无结果再 vector）
- 趋势分析 → execute_sql（GROUP BY year）+ search_abstracts（代表作）+ generate_chart
- 联网查最新/外部论文 → search_arxiv 或 search_semantic_scholar
- 非学术信息 → search_web

## 回答规则

- 必须基于工具返回的数据，禁止编造论文或数据
- 引用论文时附带 title + conference + year
- 无结果时明确告知用户并建议换关键词
- 与 AI 论文完全无关的问题（闲聊、写代码），直接说明你只能回答 AI 论文相关问题

## generate_chart 输出格式

调用 generate_chart 后，图表会自动渲染在聊天界面中。使用示例：
- 年度论文数量趋势 → chart_type="bar" 或 "line"
- 会议论文分布 → chart_type="pie"
- 引用分布 → chart_type="box"
- 多维度对比 → chart_type="bar"（分组）
"""
```

- [ ] **Step 2: 验证语法正确**

```bash
uv run python -c "from deep_paper_qa.prompts import SYSTEM_PROMPT; print(len(SYSTEM_PROMPT), 'chars')"
```

Expected: 输出字符数，无报错。

- [ ] **Step 3: Commit**

```bash
git add src/deep_paper_qa/prompts.py
git commit -m "refactor: 合并多个 prompt 为单一 SYSTEM_PROMPT"
```

---

### Task 4: 清理 models.py — 删除路由和管线状态

**Files:**
- Modify: `src/deep_paper_qa/models.py`

- [ ] **Step 1: 删除 RouteCategory、ResearchState、TrendState**

编辑 `src/deep_paper_qa/models.py`，移除以下代码（第 1-6 行保留，第 42-68 行删除）：

删除 `RouteCategory` 枚举（第 42-50 行）：
```python
class RouteCategory(str, Enum):
    ...
```

删除 `ResearchState`（第 53-60 行）：
```python
class ResearchState(MessagesState):
    ...
```

删除 `TrendState`（第 63-68 行）：
```python
class TrendState(MessagesState):
    ...
```

同时清理不再需要的导入：删除 `from enum import Enum`、`from typing import Any`、`from langgraph.graph import MessagesState`。

最终 `models.py` 只保留：

```python
"""Pydantic 数据模型"""

from pydantic import BaseModel


class PaperRecord(BaseModel):
    """论文元数据记录（对应 PostgreSQL papers 表）"""

    id: str
    title: str
    abstract: str | None = None
    year: int
    conference: str | None = None
    venue_type: str | None = None
    authors: list[str] = []
    citations: int = 0
    directions: list[str] = []
    url: str | None = None
    pdf_url: str | None = None


class SearchChunk(BaseModel):
    """向量检索返回的单个文档片段"""

    paper_id: str = ""
    paper_title: str = ""
    content: str = ""
    score: float = 0.0


class SearchResult(BaseModel):
    """向量检索结果"""

    query: str
    chunks: list[SearchChunk] = []
```

- [ ] **Step 2: 验证 models 测试通过**

```bash
uv run pytest tests/test_agent.py::TestModels -v
```

Expected: 2 tests PASSED（PaperRecord 和 SearchResult 测试不受影响）

- [ ] **Step 3: Commit**

```bash
git add src/deep_paper_qa/models.py
git commit -m "refactor: 删除 RouteCategory/ResearchState/TrendState"
```

---

### Task 5: 重写 agent.py — 用 create_deep_agent 构建

**Files:**
- Rewrite: `src/deep_paper_qa/agent.py`
- Rewrite: `tests/test_agent.py`

- [ ] **Step 1: 写新 agent 的测试**

重写 `tests/test_agent.py`：

```python
"""DeepAgent 构建测试"""

from unittest.mock import AsyncMock, patch


class TestBuildAgent:
    """DeepAgent 构建测试"""

    def test_agent_builds_successfully(self) -> None:
        """agent 能正常构建"""
        from deep_paper_qa.agent import build_agent

        agent, checkpointer = build_agent()
        assert agent is not None
        assert checkpointer is not None

    def test_agent_has_invoke_methods(self) -> None:
        """agent 应支持 invoke 和 ainvoke"""
        from deep_paper_qa.agent import build_agent

        agent, _ = build_agent()
        assert hasattr(agent, "invoke")
        assert hasattr(agent, "ainvoke")

    def test_agent_has_stream_methods(self) -> None:
        """agent 应支持流式输出"""
        from deep_paper_qa.agent import build_agent

        agent, _ = build_agent()
        assert hasattr(agent, "astream_events")


class TestModels:
    """数据模型测试"""

    def test_paper_record_creation(self) -> None:
        from deep_paper_qa.models import PaperRecord

        paper = PaperRecord(
            id="arxiv:2312.07559",
            title="Test Paper",
            year=2025,
            authors=["Author A", "Author B"],
            directions=["RAG", "NLP"],
        )
        assert paper.id == "arxiv:2312.07559"
        assert len(paper.authors) == 2
        assert paper.citations == 0

    def test_search_result_creation(self) -> None:
        from deep_paper_qa.models import SearchChunk, SearchResult

        result = SearchResult(
            query="RAG methods",
            chunks=[
                SearchChunk(
                    paper_id="arxiv:2312.10997",
                    paper_title="RAG Survey",
                    content="Retrieval augmented generation...",
                    score=0.95,
                )
            ],
        )
        assert len(result.chunks) == 1
        assert result.chunks[0].score == 0.95
```

- [ ] **Step 2: 运行测试确认失败**

```bash
uv run pytest tests/test_agent.py -v
```

Expected: FAIL，`ImportError: cannot import name 'build_agent'`

- [ ] **Step 3: 重写 agent.py**

将 `src/deep_paper_qa/agent.py` 替换为：

```python
"""DeepAgent 构建：单一 agent + 7 工具 + 领域知识 prompt"""

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger

from deep_paper_qa.config import get_llm
from deep_paper_qa.prompts import SYSTEM_PROMPT
from deep_paper_qa.tools.ask_user import ask_user
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.generate_chart import generate_chart
from deep_paper_qa.tools.search_abstracts import search_abstracts
from deep_paper_qa.tools.search_arxiv import search_arxiv
from deep_paper_qa.tools.search_semantic_scholar import search_semantic_scholar
from deep_paper_qa.tools.search_web import search_web

# 全部工具
ALL_TOOLS = [
    execute_sql,
    search_abstracts,
    search_arxiv,
    search_semantic_scholar,
    search_web,
    ask_user,
    generate_chart,
]

# eval 用的工具列表（排除 ask_user，避免 eval 时阻塞）
EVAL_TOOLS = [t for t in ALL_TOOLS if t.name != "ask_user"]


def build_agent(*, include_ask_user: bool = True):
    """构建 DeepAgent 并返回 (agent, checkpointer)

    Args:
        include_ask_user: 是否包含 ask_user 工具。eval 时设为 False。
    """
    checkpointer = InMemorySaver()
    tools = ALL_TOOLS if include_ask_user else EVAL_TOOLS

    agent = create_deep_agent(
        model=get_llm(temperature=0.7),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    logger.info("DeepAgent 构建完成 | tools={}", [t.name for t in tools])
    return agent, checkpointer
```

- [ ] **Step 4: 运行测试确认通过**

```bash
uv run pytest tests/test_agent.py -v
```

Expected: 5 tests PASSED

- [ ] **Step 5: Commit**

```bash
git add src/deep_paper_qa/agent.py tests/test_agent.py
git commit -m "feat: 用 create_deep_agent 重写 agent 层"
```

---

### Task 6: 删除 pipelines 目录

**Files:**
- Delete: `src/deep_paper_qa/pipelines/router.py`
- Delete: `src/deep_paper_qa/pipelines/general.py`
- Delete: `src/deep_paper_qa/pipelines/research.py`
- Delete: `src/deep_paper_qa/pipelines/trend.py`
- Delete: `src/deep_paper_qa/pipelines/reading.py`
- Delete: `src/deep_paper_qa/pipelines/compare.py`
- Delete: `src/deep_paper_qa/pipelines/__init__.py`（如果存在）
- Delete: `tests/test_router.py`
- Delete: `tests/test_research.py`
- Delete: `tests/test_trend.py`

- [ ] **Step 1: 删除 pipelines 目录和相关测试**

```bash
rm -rf src/deep_paper_qa/pipelines/
rm -f tests/test_router.py tests/test_research.py tests/test_trend.py
```

- [ ] **Step 2: 验证剩余测试不受影响**

```bash
uv run pytest tests/test_execute_sql.py tests/test_search_abstracts.py tests/test_generate_chart.py tests/test_agent.py -v
```

Expected: 全部 PASSED

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: 删除 pipelines 目录和相关测试"
```

---

### Task 7: 重写 app.py — 适配 DeepAgent 流式输出

**Files:**
- Rewrite: `src/deep_paper_qa/app.py`

- [ ] **Step 1: 重写 app.py**

将 `src/deep_paper_qa/app.py` 替换为：

```python
"""Chainlit 入口：DeepAgent 流式输出 + 中间步骤展示 + 日志记录"""

import re
import time
import uuid

import chainlit as cl
import plotly.io as pio
from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_agent
from deep_paper_qa.conversation_logger import ConversationLogger
from deep_paper_qa.logging_setup import setup_logging

setup_logging()

_agent, _checkpointer = build_agent()
_conv_logger = ConversationLogger()

# DeepAgents 内置工具名称（用于特殊展示）
_BUILTIN_TOOL_LABELS = {
    "write_todos": "📋 制定计划",
    "task": "🔀 委派子任务",
}


@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    """提供示例问题，引导新用户快速上手"""
    return [
        cl.Starter(label="会议论文统计", message="各会议论文数量是多少？"),
        cl.Starter(label="RAG 研究趋势", message="RAG 近三年的发展趋势怎么样？"),
        cl.Starter(label="深度调研", message="总结 2023-2025 年 LLM Agent 的研究脉络"),
        cl.Starter(label="高引论文推荐", message="推荐一些高引用的大语言模型论文"),
    ]


@cl.on_chat_start
async def on_chat_start() -> None:
    """初始化会话"""
    thread_id = str(uuid.uuid4())
    cl.user_session.set("thread_id", thread_id)
    logger.info("新会话启动 | thread_id={}", thread_id)
    await cl.Message(
        content="你好！我是 AI 科研论文问答助手，支持论文统计查询、内容检索、研究趋势分析和深度调研。"
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """处理用户消息"""
    if cl.user_session.get("waiting_for_ask_user"):
        return

    thread_id = cl.user_session.get("thread_id")
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50,
    }

    logger.info("用户消息 | thread_id={} | content={}", thread_id, message.content)
    _conv_logger.log_user_message(thread_id, message.content)

    msg_start = time.monotonic()
    tool_call_count = 0
    tools_used: list[str] = []
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

                logger.info(
                    "Tool调用 | thread_id={} | tool={} | input={}",
                    thread_id,
                    tool_name,
                    tool_input,
                )
                _conv_logger.log_tool_start(thread_id, tool_name, tool_input)

                tool_timings[run_id] = (tool_name, time.monotonic())
                tool_call_count += 1
                if tool_name not in tools_used:
                    tools_used.append(tool_name)

                if tool_name == "ask_user":
                    cl.user_session.set("waiting_for_ask_user", True)
                else:
                    display_name = _BUILTIN_TOOL_LABELS.get(tool_name, tool_name)
                    step = cl.Step(name=display_name, type="tool")
                    step.input = str(tool_input)
                    await step.send()
                    cl.user_session.set(f"step_{run_id}", step)

            # 工具调用结束
            elif kind == "on_tool_end":
                if name == "ask_user":
                    cl.user_session.set("waiting_for_ask_user", False)
                run_id = event.get("run_id", "")
                output = event.get("data", {}).get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                output_str = str(output)

                duration_ms = 0
                tool_name = "unknown"
                if run_id in tool_timings:
                    tool_name, start_t = tool_timings.pop(run_id)
                    duration_ms = int((time.monotonic() - start_t) * 1000)

                logger.info(
                    "Tool返回 | thread_id={} | tool={} | duration_ms={} | "
                    "output_len={} | output={}",
                    thread_id,
                    tool_name,
                    duration_ms,
                    len(output_str),
                    output_str[:1000],
                )
                _conv_logger.log_tool_end(thread_id, tool_name, duration_ms, output_str)

                step = cl.user_session.get(f"step_{run_id}")
                if step:
                    step.output = output_str[:500] if len(output_str) > 500 else output_str
                    await step.update()

            # LLM 流式输出（统一流式，不再区分管线）
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    await final_msg.stream_token(chunk.content)

        # 处理图表（generate_chart 输出嵌入在最终消息中）
        if "<!--plotly:" in final_msg.content:
            plotly_match = re.search(r"<!--plotly:(.*?)-->", final_msg.content, re.DOTALL)
            if plotly_match:
                chart_json = plotly_match.group(1)
                final_msg.content = re.sub(
                    r"<!--plotly:.*?-->\n*", "", final_msg.content, flags=re.DOTALL
                )
                try:
                    fig = pio.from_json(chart_json)
                    final_msg.elements = [
                        cl.Plotly(name="数据图表", figure=fig, display="inline")
                    ]
                except Exception as plot_err:
                    logger.warning("Plotly 图表渲染失败: {}", plot_err)

        await final_msg.update()

        total_ms = int((time.monotonic() - msg_start) * 1000)
        logger.info(
            "会话统计 | thread_id={} | total_ms={} | tool_calls={} | tools_used={}",
            thread_id,
            total_ms,
            tool_call_count,
            tools_used,
        )
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

- [ ] **Step 2: 验证语法**

```bash
uv run python -c "import ast; ast.parse(open('src/deep_paper_qa/app.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/deep_paper_qa/app.py
git commit -m "refactor: app.py 适配 DeepAgent 统一流式输出"
```

---

### Task 8: 适配 eval/run_eval.py

**Files:**
- Modify: `eval/run_eval.py:1-15,268-275`

- [ ] **Step 1: 修改 eval 导入和 agent 构建**

在 `eval/run_eval.py` 中修改导入和 `run_eval` 函数：

将第 9-10 行：
```python
from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_graph
```

替换为：
```python
from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_agent
```

将第 274 行的 `run_eval` 函数中：
```python
    agent, checkpointer = build_graph()
```

替换为：
```python
    agent, checkpointer = build_agent(include_ask_user=False)
```

- [ ] **Step 2: 移除路由类型相关的 eval 逻辑中对 trend/research/reject 的特殊处理**

当前 eval 按 `q_type` 判断工具路由正确性（第 81-115 行）。DeepAgent 没有路由分类，但 eval 的工具正确性判断仍然有效（判断的是工具组合是否合理，不依赖路由）。保持这部分不变。

- [ ] **Step 3: 运行 eval 语法检查**

```bash
uv run python -c "import ast; ast.parse(open('eval/run_eval.py').read()); print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add eval/run_eval.py
git commit -m "refactor: eval 适配 build_agent 接口"
```

---

### Task 9: 更新 tools/__init__.py

**Files:**
- Modify: `src/deep_paper_qa/tools/__init__.py`

- [ ] **Step 1: 更新 __init__.py 导出**

将 `src/deep_paper_qa/tools/__init__.py` 替换为：

```python
"""工具模块：execute_sql + search_abstracts + 外部搜索 + ask_user + generate_chart"""
```

- [ ] **Step 2: Commit**

```bash
git add src/deep_paper_qa/tools/__init__.py
git commit -m "chore: 更新 tools __init__.py 注释"
```

---

### Task 10: 全量测试 + Lint

**Files:** （无新文件）

- [ ] **Step 1: 运行 ruff lint**

```bash
uv run ruff check src/ tests/ eval/
```

Expected: 无错误。如有未使用的导入等问题，逐个修复。

- [ ] **Step 2: 运行 ruff format**

```bash
uv run ruff format src/ tests/ eval/
```

- [ ] **Step 3: 运行全量测试**

```bash
uv run pytest tests/ -v
```

Expected: 所有保留的测试全部 PASSED。忽略已删除的测试文件。

- [ ] **Step 4: 修复任何失败**

如果有测试导入了已删除的模块（如 `RouteCategory`），修复相关导入。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: lint + format + 修复测试"
```

---

### Task 11: 冒烟测试 — 手动验证 Chainlit UI

**Files:** （无新文件）

- [ ] **Step 1: 启动应用**

```bash
uv run chainlit run src/deep_paper_qa/app.py
```

- [ ] **Step 2: 测试基本问答**

在浏览器打开 http://localhost:8000，依次测试：

1. 简单统计："各会议论文数量是多少？" → 应返回 SQL 查询结果
2. 内容检索："有哪些关于 RAG 的论文？" → 应用 search_abstracts
3. 趋势分析："RAG 近三年的发展趋势" → 应生成图表
4. 无关问题："今天天气怎么样" → 应拒答
5. 深度问题："总结 LLM Agent 的研究脉络" → 观察 DeepAgent 是否自动规划

- [ ] **Step 3: 检查 DeepAgent 内置功能**

观察复杂问题（如第 5 题）时：
- 是否出现 `write_todos`（制定计划）步骤
- 是否出现 `task`（委派子任务）步骤
- 流式输出是否正常

- [ ] **Step 4: 记录问题**

记下遇到的问题，在后续 commit 中修复。
