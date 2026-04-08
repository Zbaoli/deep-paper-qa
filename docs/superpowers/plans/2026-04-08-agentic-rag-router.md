# 六分类路由架构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将单一 ReAct Agent 改造为路由节点 + 6 条独立 pipeline 的 LangGraph 显式图架构

**Architecture:** 路由节点用 LLM structured output 做六分类，根据分类结果将用户消息分发到对应 subgraph（拒答模板 / ReAct / DeepResearch / PaperReading 占位 / PaperCompare 占位 / TrendAnalysis）。每个 pipeline 是独立的 LangGraph subgraph，通过主图的条件边连接。

**Tech Stack:** LangGraph (StateGraph + conditional_edge), langchain-openai (ChatOpenAI + structured output), Pydantic (状态模型), asyncpg, chainlit

---

## 文件结构

```
src/deep_paper_qa/
├── agent.py                    # 重写：构建主图（路由 + 各 subgraph 编排）
├── prompts.py                  # 重写：拆分为路由 prompt + 各 pipeline 独立 prompt
├── models.py                   # 扩展：新增路由分类模型 + 各 pipeline State
├── app.py                      # 简化：移除 /research 前缀检测
├── pipelines/
│   ├── __init__.py
│   ├── router.py               # 路由节点：LLM 六分类
│   ├── general.py              # 普通问题：ReAct subgraph
│   ├── research.py             # 深度研究：显式多节点 subgraph
│   ├── reading.py              # 论文精读：P2 占位
│   ├── compare.py              # 论文对比：P2 占位
│   └── trend.py                # 趋势分析：固定流程 subgraph
├── config.py                   # 不变
├── conversation_logger.py      # 不变
├── logging_setup.py            # 不变
└── tools/                      # 不变
    ├── __init__.py
    ├── execute_sql.py
    ├── search_abstracts.py
    ├── vector_search.py
    ├── ask_user.py
    └── sql_utils.py

tests/
├── test_router.py              # 新增：路由分类测试
├── test_trend.py               # 新增：趋势分析测试
├── test_research.py            # 新增：深度研究测试
├── test_agent.py               # 更新：适配新架构
└── ...                         # 其余测试不变
```

---

### Task 1: 路由分类模型 + State 定义

**Files:**
- Modify: `src/deep_paper_qa/models.py`
- Test: `tests/test_router.py`

- [ ] **Step 1: 写路由分类模型的测试**

在 `tests/test_router.py` 中：

```python
"""路由分类测试"""

from deep_paper_qa.models import RouteCategory, RouterOutput


class TestRouterOutput:
    """路由输出模型测试"""

    def test_valid_category(self) -> None:
        output = RouterOutput(category=RouteCategory.GENERAL)
        assert output.category == RouteCategory.GENERAL

    def test_all_categories_exist(self) -> None:
        expected = {"reject", "general", "research", "reading", "compare", "trend"}
        actual = {c.value for c in RouteCategory}
        assert actual == expected
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_router.py::TestRouterOutput -v`
Expected: FAIL — `ImportError: cannot import name 'RouteCategory' from 'deep_paper_qa.models'`

- [ ] **Step 3: 实现路由分类模型**

在 `src/deep_paper_qa/models.py` 末尾追加：

```python
from enum import Enum
from typing import Any

from langgraph.graph import MessagesState


class RouteCategory(str, Enum):
    """路由分类枚举"""

    REJECT = "reject"
    GENERAL = "general"
    RESEARCH = "research"
    READING = "reading"
    COMPARE = "compare"
    TREND = "trend"


class RouterOutput(BaseModel):
    """路由节点的 LLM structured output"""

    category: RouteCategory


class ResearchState(MessagesState):
    """深度研究 pipeline 状态"""

    plan: list[str]
    current_step: int
    findings: list[str]
    clarify_count: int


class TrendState(MessagesState):
    """趋势分析 pipeline 状态"""

    query_topic: str
    stats_data: str
    phases: list[dict[str, Any]]
    representative_papers: list[str]
    report: str
```

注意：`import` 语句（`from enum import Enum` 等）放在文件顶部已有的 import 区域。`MessagesState` 来自 `langgraph.graph`，它内置了 `messages` 字段。

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_router.py::TestRouterOutput -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/models.py tests/test_router.py
git commit -m "feat: 新增路由分类模型和 pipeline State 定义"
```

---

### Task 2: 路由 Prompt

**Files:**
- Modify: `src/deep_paper_qa/prompts.py`

- [ ] **Step 1: 重写 prompts.py**

将 `src/deep_paper_qa/prompts.py` 完整重写为以下内容。旧的 `SYSTEM_PROMPT` 会被拆分为 `ROUTER_PROMPT` + `GENERAL_PROMPT` + `RESEARCH_PROMPT` + `TREND_PROMPT`。

```python
"""各 Pipeline 的 System Prompt"""

# ── 路由节点 ──────────────────────────────────────────────
ROUTER_PROMPT = """你是一个问题分类器。根据用户的问题，判断应该走哪个处理流程。

分类标准：
- reject: 与 AI 论文完全无关的问题（闲聊、写代码、非学术问题）
- general: 可以通过 1-4 次工具调用直接回答的问题（统计查询、论文检索、作者查询、简单混合问题）
- research: 需要拆解为 3 个以上子问题、多轮检索后生成结构化研究报告的复杂问题
- reading: 针对一篇特定论文的深入精读解读
- compare: 针对两篇或多篇特定论文的多维度对比分析
- trend: 关注某个研究方向在时间维度上的数量变化趋势和演进

示例：
- "2024年NeurIPS收录了多少篇论文？" → general
- "有哪些关于 RAG 的论文？" → general
- "2024年引用最高的 RAG 论文讲了什么？" → general
- "调研 AI for Science 在蛋白质结构预测方向的最新进展" → research
- "总结 2023-2025 年 LLM Agent 的研究脉络" → research
- "帮我精读 Attention Is All You Need" → reading
- "对比 DPO 和 RLHF 这两篇论文的方法差异" → compare
- "RAG 近三年的发展趋势" → trend
- "知识蒸馏这个方向是在升温还是降温？" → trend
- "今天天气怎么样？" → reject
- "帮我写 Python 代码" → reject

请严格输出分类结果。"""

# ── 普通问题（ReAct）──────────────────────────────────────
GENERAL_PROMPT = """你是一个 AI 科研论文问答助手。你有两个工具：

1. execute_sql: 查询 PostgreSQL 数据库中的论文元数据（统计、排序、筛选、作者查询）。

   数据库 schema:
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

   注意：authors 是 TEXT[] 数组类型。
   查询数组用 ANY()：WHERE 'Yann LeCun' = ANY(authors)
   禁止对 authors 用 LIKE，必须用 ANY()。

   常见错误（禁止）：
   ❌ WHERE authors LIKE '%Hinton%'
   ❌ WHERE directions = 'RAG'       -- directions 字段禁止使用
   ❌ WHERE conference = 'neurips'   -- 必须用 NeurIPS

   全文检索语法（在 SQL 中直接使用）：
   WHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))
         @@ to_tsquery('english', '查询表达式')
   操作符：& (AND), | (OR), <-> (相邻), ! (NOT), :* (前缀匹配)

   示例：
   - SELECT COUNT(*) FROM papers WHERE year=2025 AND conference='ACL'
   - SELECT year, COUNT(*) FROM papers WHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) @@ to_tsquery('english', 'retrieval <-> augment:*') GROUP BY year ORDER BY year

   高级查询模式：
   - CASE WHEN 分段统计
   - unnest(authors) 数组展开+聚合

   只允许 SELECT 查询。查询结果最多返回 20 行。

2. search_abstracts: 搜索论文标题和摘要内容。
   重要限制：只搜索标题和摘要，不搜索作者等元数据。
   两种模式：
   - mode="fulltext"（默认）：关键词全文检索
   - mode="vector"：语义向量检索
   使用策略：先 fulltext，无结果再 vector。

   fulltext 查询语法：空格=AND，OR=或，"引号"=精确短语，-=排除。
   可选参数 where：SQL WHERE 条件片段。

关键词扩展规则（全文检索前必做）：
同一概念扩展为多种英文表述，用 | (OR) 连接。
示例：RAG → 'RAG | (retrieval <-> augment:*) | (retrieval <-> generat:*)'

工具选择规则：
- 统计/计数/排名 → execute_sql
- 按作者查论文 → execute_sql + ANY(authors)
- 查论文内容/方法 → search_abstracts
- 混合问题 → 先 execute_sql 再 search_abstracts

效率规则（硬限制）：
- 单个问题最多调用 4 次工具
- 搜索返回 5+ 条结果就直接回答
- search_abstracts 最多连续 2 次

回答规则：
- 必须基于工具返回数据，禁止编造
- 引用论文附带 title + conference + year
- 无结果时建议用户换关键词"""

# ── 深度研究 ──────────────────────────────────────────────
RESEARCH_CLARIFY_PROMPT = """你是一个研究助手。用户提出了一个需要深入研究的学术问题。
请判断用户的问题是否足够清晰，能否直接制定研究计划。

如果问题模糊或范围过大，生成一个澄清问题来明确研究方向。
如果问题已经足够明确，回复"问题已明确，可以制定研究计划。"

只输出一个澄清问题或确认消息，不要输出其他内容。"""

RESEARCH_PLAN_PROMPT = """你是一个研究助手。根据用户的研究问题，制定一份研究计划。

要求：
- 将问题分解为 3-5 个可独立检索的子问题
- 每个子问题注明计划使用的工具（execute_sql 或 search_abstracts）
- 子问题之间有逻辑递进关系

输出格式（严格 JSON 数组）：
["子问题1: 使用 execute_sql 统计...", "子问题2: 使用 search_abstracts 检索...", ...]"""

RESEARCH_STEP_PROMPT = """你是一个研究助手，正在执行研究计划的一个子问题。

当前子问题：{current_question}

你有两个工具：execute_sql 和 search_abstracts。
请针对这个子问题进行检索，最多调用 2 次工具。完成后总结关键发现。

数据库 schema 同普通问答（papers 表，字段：id, title, abstract, year, conference, authors, citations 等）。
关键词扩展规则同普通问答。"""

RESEARCH_REPORT_PROMPT = """你是一个研究助手。根据以下各子问题的研究发现，生成一份结构化的研究报告。

各子问题发现：
{findings}

要求：
- 结构清晰，使用标题和子标题
- 引用具体论文（标题、会议、年份）
- 如有不同子问题的结果可对比，给出对比分析
- 总结研究现状，指出可能的研究趋势或空白"""

# ── 趋势分析 ──────────────────────────────────────────────
TREND_SQL_PROMPT = """你是一个数据分析师。用户想了解某个 AI 研究方向的时间趋势。

用户问题：{question}

请生成一条 SQL，按年统计该方向的论文数量。使用全文检索过滤主题。
注意关键词扩展：同一概念用多种表述，用 | 连接。

数据库 schema:
CREATE TABLE papers (
    id TEXT PRIMARY KEY, title TEXT, abstract TEXT,
    year INT (2020-2025), conference TEXT, authors TEXT[],
    citations INT DEFAULT 0
);

全文检索语法：
WHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))
      @@ to_tsquery('english', '查询表达式')

只输出 SQL 语句，不要输出其他内容。SQL 必须包含 GROUP BY year ORDER BY year。"""

TREND_PHASES_PROMPT = """你是一个数据分析师。根据以下按年论文数量数据，识别研究趋势的阶段。

统计数据：
{stats_data}

将趋势划分为若干阶段（如：萌芽期、增长期、爆发期、平稳期、下降期）。
每个阶段注明年份范围和特征。

输出格式（严格 JSON 数组）：
[{{"phase": "阶段名", "years": "2020-2021", "description": "特征描述"}}, ...]"""

TREND_REPORT_PROMPT = """你是一个研究趋势分析师。综合以下信息，生成一份研究趋势分析报告。

研究主题：{topic}

按年论文数量：
{stats_data}

趋势阶段：
{phases}

各阶段代表性论文：
{representative_papers}

要求：
- 先给出数据概览（总论文数、时间跨度、增长率）
- 按阶段分析，每个阶段引用代表性论文
- 总结趋势走向和可能的未来发展"""
```

- [ ] **Step 2: 运行 lint 确认无语法错误**

Run: `uv run ruff check src/deep_paper_qa/prompts.py`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
git add src/deep_paper_qa/prompts.py
git commit -m "refactor: 拆分 prompt 为路由 + 各 pipeline 独立 prompt"
```

---

### Task 3: 路由节点实现

**Files:**
- Create: `src/deep_paper_qa/pipelines/__init__.py`
- Create: `src/deep_paper_qa/pipelines/router.py`
- Test: `tests/test_router.py`

- [ ] **Step 1: 写路由节点测试**

在 `tests/test_router.py` 中追加（保留 Task 1 的 `TestRouterOutput`）：

```python
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import HumanMessage

from deep_paper_qa.models import RouteCategory
from deep_paper_qa.pipelines.router import classify_question


class TestClassifyQuestion:
    """路由分类函数测试"""

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router._get_router_llm")
    async def test_general_question(self, mock_get_llm: AsyncMock) -> None:
        """统计类问题应分类为 general"""
        from deep_paper_qa.models import RouterOutput

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = RouterOutput(category=RouteCategory.GENERAL)
        mock_get_llm.return_value = mock_llm

        result = await classify_question("2024年NeurIPS收录了多少篇论文？")
        assert result == RouteCategory.GENERAL

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router._get_router_llm")
    async def test_reject_question(self, mock_get_llm: AsyncMock) -> None:
        """无关问题应分类为 reject"""
        from deep_paper_qa.models import RouterOutput

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = RouterOutput(category=RouteCategory.REJECT)
        mock_get_llm.return_value = mock_llm

        result = await classify_question("今天天气怎么样？")
        assert result == RouteCategory.REJECT

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router._get_router_llm")
    async def test_research_question(self, mock_get_llm: AsyncMock) -> None:
        """复杂研究问题应分类为 research"""
        from deep_paper_qa.models import RouterOutput

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = RouterOutput(category=RouteCategory.RESEARCH)
        mock_get_llm.return_value = mock_llm

        result = await classify_question("总结 2023-2025 年 LLM Agent 的研究脉络")
        assert result == RouteCategory.RESEARCH

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router._get_router_llm")
    async def test_trend_question(self, mock_get_llm: AsyncMock) -> None:
        """趋势类问题应分类为 trend"""
        from deep_paper_qa.models import RouterOutput

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = RouterOutput(category=RouteCategory.TREND)
        mock_get_llm.return_value = mock_llm

        result = await classify_question("RAG 近三年的发展趋势")
        assert result == RouteCategory.TREND

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router._get_router_llm")
    async def test_classify_returns_general_on_error(self, mock_get_llm: AsyncMock) -> None:
        """LLM 调用异常时回退到 general"""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("LLM error")
        mock_get_llm.return_value = mock_llm

        result = await classify_question("任意问题")
        assert result == RouteCategory.GENERAL
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_router.py::TestClassifyQuestion -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'deep_paper_qa.pipelines'`

- [ ] **Step 3: 创建 pipelines 包和路由节点**

创建 `src/deep_paper_qa/pipelines/__init__.py`：

```python
"""Pipeline 模块：路由 + 各独立处理流程"""
```

创建 `src/deep_paper_qa/pipelines/router.py`：

```python
"""路由节点：LLM 六分类"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from deep_paper_qa.config import settings
from deep_paper_qa.models import RouteCategory, RouterOutput
from deep_paper_qa.prompts import ROUTER_PROMPT


def _get_router_llm() -> ChatOpenAI:
    """获取路由分类用的 LLM（with_structured_output）"""
    llm = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0,
    )
    return llm.with_structured_output(RouterOutput)


async def classify_question(question: str) -> RouteCategory:
    """对用户问题进行六分类

    Args:
        question: 用户输入的问题文本

    Returns:
        RouteCategory 枚举值
    """
    try:
        llm = _get_router_llm()
        result = await llm.ainvoke([
            SystemMessage(content=ROUTER_PROMPT),
            HumanMessage(content=question),
        ])
        logger.info("路由分类 | question='{}' | category={}", question[:80], result.category.value)
        return result.category
    except Exception as e:
        logger.warning("路由分类异常，回退到 general | error={}", e)
        return RouteCategory.GENERAL
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_router.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/pipelines/ tests/test_router.py`
Expected: 无错误

- [ ] **Step 6: 提交**

```bash
git add src/deep_paper_qa/pipelines/__init__.py src/deep_paper_qa/pipelines/router.py tests/test_router.py
git commit -m "feat: 实现路由节点 LLM 六分类"
```

---

### Task 4: P2 占位 Pipeline（拒答 + 论文精读 + 论文对比）

**Files:**
- Create: `src/deep_paper_qa/pipelines/reading.py`
- Create: `src/deep_paper_qa/pipelines/compare.py`

这三个 pipeline 逻辑极简，不需要单独测试（拒答是模板字符串，精读/对比是占位消息），会在 Task 7 的主图集成测试中覆盖。

- [ ] **Step 1: 创建论文精读占位**

创建 `src/deep_paper_qa/pipelines/reading.py`：

```python
"""论文精读 Pipeline（P2 占位）"""

from langgraph.graph import MessagesState

READING_PLACEHOLDER = "论文精读功能开发中，敬请期待。目前可以使用普通问答查询论文摘要信息。"


async def paper_reading_node(state: MessagesState) -> dict:
    """论文精读占位节点"""
    from langchain_core.messages import AIMessage

    return {"messages": [AIMessage(content=READING_PLACEHOLDER)]}
```

- [ ] **Step 2: 创建论文对比占位**

创建 `src/deep_paper_qa/pipelines/compare.py`：

```python
"""论文对比 Pipeline（P2 占位）"""

from langgraph.graph import MessagesState

COMPARE_PLACEHOLDER = "论文对比功能开发中，敬请期待。目前可以使用普通问答查询并对比论文摘要。"


async def paper_compare_node(state: MessagesState) -> dict:
    """论文对比占位节点"""
    from langchain_core.messages import AIMessage

    return {"messages": [AIMessage(content=COMPARE_PLACEHOLDER)]}
```

- [ ] **Step 3: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/pipelines/reading.py src/deep_paper_qa/pipelines/compare.py`
Expected: 无错误

- [ ] **Step 4: 提交**

```bash
git add src/deep_paper_qa/pipelines/reading.py src/deep_paper_qa/pipelines/compare.py
git commit -m "feat: 新增论文精读和论文对比 P2 占位 pipeline"
```

---

### Task 5: 普通问题 ReAct Pipeline

**Files:**
- Create: `src/deep_paper_qa/pipelines/general.py`

- [ ] **Step 1: 创建 ReAct subgraph**

创建 `src/deep_paper_qa/pipelines/general.py`：

```python
"""普通问题 Pipeline：ReAct Agent"""

from typing import Any

from langchain_core.messages import trim_messages
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from deep_paper_qa.config import settings
from deep_paper_qa.prompts import GENERAL_PROMPT
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.search_abstracts import search_abstracts

# 消息裁剪：保留最近 N 轮对话
_trimmer = trim_messages(
    max_tokens=16000,
    strategy="last",
    token_counter=len,
    include_system=True,
    allow_partial=False,
)


def _pre_model_hook(state: dict[str, Any]) -> dict[str, Any]:
    """裁剪消息后传给 LLM"""
    trimmed = _trimmer.invoke(state["messages"])
    return {"llm_input_messages": trimmed}


def build_general_subgraph():
    """构建普通问题 ReAct subgraph"""
    model = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )

    return create_react_agent(
        model,
        tools=[execute_sql, search_abstracts],
        prompt=GENERAL_PROMPT,
        pre_model_hook=_pre_model_hook,
    )
```

- [ ] **Step 2: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/pipelines/general.py`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
git add src/deep_paper_qa/pipelines/general.py
git commit -m "feat: 实现普通问题 ReAct pipeline"
```

---

### Task 6: 趋势分析 Pipeline

**Files:**
- Create: `src/deep_paper_qa/pipelines/trend.py`
- Test: `tests/test_trend.py`

- [ ] **Step 1: 写趋势分析节点测试**

创建 `tests/test_trend.py`：

```python
"""趋势分析 Pipeline 测试"""

from unittest.mock import AsyncMock, patch

import pytest

from deep_paper_qa.pipelines.trend import generate_sql_node, synthesize_node


class TestGenerateSqlNode:
    """SQL 生成节点测试"""

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.trend._get_trend_llm")
    async def test_generates_sql(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value.content = (
            "SELECT year, COUNT(*) AS cnt FROM papers "
            "WHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,'')) "
            "@@ to_tsquery('english', 'RAG | (retrieval <-> augment:*)') "
            "GROUP BY year ORDER BY year"
        )
        mock_get_llm.return_value = mock_llm

        from langchain_core.messages import HumanMessage

        state = {
            "messages": [HumanMessage(content="RAG 近三年的发展趋势")],
            "query_topic": "",
            "stats_data": "",
            "phases": [],
            "representative_papers": [],
            "report": "",
        }
        result = await generate_sql_node(state)
        assert "query_topic" in result
        assert result["query_topic"] != ""


class TestSynthesizeNode:
    """报告生成节点测试"""

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.trend._get_trend_llm")
    async def test_generates_report(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value.content = "# RAG 趋势分析报告\n\n..."
        mock_get_llm.return_value = mock_llm

        from langchain_core.messages import HumanMessage

        state = {
            "messages": [HumanMessage(content="RAG 趋势")],
            "query_topic": "RAG",
            "stats_data": "2022: 50\n2023: 120\n2024: 300",
            "phases": [{"phase": "增长期", "years": "2022-2024", "description": "快速增长"}],
            "representative_papers": ["论文A (NeurIPS 2023)", "论文B (ICML 2024)"],
            "report": "",
        }
        result = await synthesize_node(state)
        assert "report" in result
        assert result["report"] != ""
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_trend.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现趋势分析 pipeline**

创建 `src/deep_paper_qa/pipelines/trend.py`：

```python
"""趋势分析 Pipeline：固定流程 subgraph"""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from loguru import logger

from deep_paper_qa.config import settings
from deep_paper_qa.models import TrendState
from deep_paper_qa.prompts import (
    TREND_PHASES_PROMPT,
    TREND_REPORT_PROMPT,
    TREND_SQL_PROMPT,
)
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.search_abstracts import search_abstracts


def _get_trend_llm() -> ChatOpenAI:
    """获取趋势分析用的 LLM"""
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0,
    )


async def generate_sql_node(state: TrendState) -> dict:
    """根据用户问题生成按年统计 SQL"""
    user_msg = state["messages"][-1].content
    llm = _get_trend_llm()
    prompt = TREND_SQL_PROMPT.format(question=user_msg)
    result = await llm.ainvoke([SystemMessage(content=prompt)])

    # 从 LLM 输出中提取 SQL（去掉可能的 markdown 代码块）
    sql = result.content.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    logger.info("趋势分析 | 生成 SQL: {}", sql[:200])
    return {"query_topic": user_msg, "stats_data": sql}


async def execute_stats_node(state: TrendState) -> dict:
    """执行统计 SQL"""
    sql = state["stats_data"]  # 上一步存的是 SQL
    result = await execute_sql.ainvoke({"sql": sql})
    logger.info("趋势分析 | 统计结果: {}", result[:200])
    return {"stats_data": result}


async def identify_phases_node(state: TrendState) -> dict:
    """根据统计数据识别趋势阶段"""
    llm = _get_trend_llm()
    prompt = TREND_PHASES_PROMPT.format(stats_data=state["stats_data"])
    result = await llm.ainvoke([SystemMessage(content=prompt)])

    try:
        phases = json.loads(result.content)
    except json.JSONDecodeError:
        logger.warning("趋势阶段解析失败，使用空列表")
        phases = []

    logger.info("趋势分析 | 识别阶段: {}", phases)
    return {"phases": phases}


async def search_representatives_node(state: TrendState) -> dict:
    """为每个阶段检索代表性论文"""
    topic = state["query_topic"]
    papers: list[str] = []

    for phase in state["phases"]:
        years = phase.get("years", "")
        # 从年份范围提取 WHERE 条件
        where = ""
        if "-" in years:
            start, end = years.split("-", 1)
            where = f"year BETWEEN {start.strip()} AND {end.strip()}"
        elif years.strip().isdigit():
            where = f"year = {years.strip()}"

        result = await search_abstracts.ainvoke({
            "query": topic,
            "mode": "fulltext",
            "limit": 3,
            "where": where,
        })
        papers.append(f"### {phase.get('phase', '')} ({years})\n{result}")

    logger.info("趋势分析 | 检索代表作完成，共 {} 个阶段", len(state["phases"]))
    return {"representative_papers": papers}


async def synthesize_node(state: TrendState) -> dict:
    """综合生成趋势分析报告"""
    llm = _get_trend_llm()
    prompt = TREND_REPORT_PROMPT.format(
        topic=state["query_topic"],
        stats_data=state["stats_data"],
        phases=json.dumps(state["phases"], ensure_ascii=False),
        representative_papers="\n\n".join(state["representative_papers"]),
    )
    result = await llm.ainvoke([SystemMessage(content=prompt)])
    report = result.content

    logger.info("趋势分析 | 报告生成完成，长度={}", len(report))
    return {"report": report, "messages": [AIMessage(content=report)]}


def build_trend_subgraph() -> StateGraph:
    """构建趋势分析 subgraph"""
    graph = StateGraph(TrendState)

    graph.add_node("generate_sql", generate_sql_node)
    graph.add_node("execute_stats", execute_stats_node)
    graph.add_node("identify_phases", identify_phases_node)
    graph.add_node("search_representatives", search_representatives_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("generate_sql")
    graph.add_edge("generate_sql", "execute_stats")
    graph.add_edge("execute_stats", "identify_phases")
    graph.add_edge("identify_phases", "search_representatives")
    graph.add_edge("search_representatives", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_trend.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/pipelines/trend.py tests/test_trend.py`
Expected: 无错误

- [ ] **Step 6: 提交**

```bash
git add src/deep_paper_qa/pipelines/trend.py tests/test_trend.py
git commit -m "feat: 实现趋势分析固定流程 pipeline"
```

---

### Task 7: 深度研究 Pipeline

**Files:**
- Create: `src/deep_paper_qa/pipelines/research.py`
- Test: `tests/test_research.py`

- [ ] **Step 1: 写深度研究节点测试**

创建 `tests/test_research.py`：

```python
"""深度研究 Pipeline 测试"""

from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import HumanMessage

from deep_paper_qa.pipelines.research import clarify_node, plan_node, should_continue_clarify


class TestClarifyNode:
    """澄清节点测试"""

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.research._get_research_llm")
    async def test_increments_clarify_count(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value.content = "问题已明确，可以制定研究计划。"
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [HumanMessage(content="调研 LLM Agent")],
            "plan": [],
            "current_step": 0,
            "findings": [],
            "clarify_count": 0,
        }
        result = await clarify_node(state)
        assert result["clarify_count"] == 1


class TestShouldContinueClarify:
    """澄清循环条件测试"""

    def test_stop_when_clear(self) -> None:
        from langchain_core.messages import AIMessage

        state = {
            "messages": [AIMessage(content="问题已明确，可以制定研究计划。")],
            "clarify_count": 1,
        }
        assert should_continue_clarify(state) == "plan"

    def test_stop_when_max_reached(self) -> None:
        from langchain_core.messages import AIMessage

        state = {
            "messages": [AIMessage(content="请问你想聚焦哪个方面？")],
            "clarify_count": 3,
        }
        assert should_continue_clarify(state) == "plan"

    def test_continue_when_unclear(self) -> None:
        from langchain_core.messages import AIMessage

        state = {
            "messages": [AIMessage(content="请问你想聚焦哪个方面？")],
            "clarify_count": 1,
        }
        assert should_continue_clarify(state) == "ask_clarify"


class TestPlanNode:
    """研究计划节点测试"""

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.research._get_research_llm")
    async def test_generates_plan(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value.content = json.dumps([
            "子问题1: 使用 search_abstracts 检索 LLM Agent 框架",
            "子问题2: 使用 execute_sql 统计各年论文数",
            "子问题3: 使用 search_abstracts 检索多智能体协作",
        ])
        mock_get_llm.return_value = mock_llm

        state = {
            "messages": [HumanMessage(content="调研 LLM Agent")],
            "plan": [],
            "current_step": 0,
            "findings": [],
            "clarify_count": 1,
        }
        result = await plan_node(state)
        assert len(result["plan"]) == 3


import json
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_research.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现深度研究 pipeline**

创建 `src/deep_paper_qa/pipelines/research.py`：

```python
"""深度研究 Pipeline：显式多节点 subgraph"""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent
from loguru import logger

from deep_paper_qa.config import settings
from deep_paper_qa.models import ResearchState
from deep_paper_qa.prompts import (
    RESEARCH_CLARIFY_PROMPT,
    RESEARCH_PLAN_PROMPT,
    RESEARCH_REPORT_PROMPT,
    RESEARCH_STEP_PROMPT,
)
from deep_paper_qa.tools.ask_user import ask_user
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.search_abstracts import search_abstracts


def _get_research_llm() -> ChatOpenAI:
    """获取深度研究用的 LLM"""
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0,
    )


async def clarify_node(state: ResearchState) -> dict:
    """澄清追问节点：判断问题是否足够清晰"""
    llm = _get_research_llm()
    user_msg = state["messages"][-1].content
    result = await llm.ainvoke([
        SystemMessage(content=RESEARCH_CLARIFY_PROMPT),
        HumanMessage(content=user_msg),
    ])

    new_count = state["clarify_count"] + 1
    logger.info("深度研究 | 澄清第{}轮: {}", new_count, result.content[:100])
    return {
        "messages": [AIMessage(content=result.content)],
        "clarify_count": new_count,
    }


async def ask_clarify_node(state: ResearchState) -> dict:
    """通过 ask_user 向用户展示澄清问题并等待回复"""
    last_msg = state["messages"][-1].content
    response = await ask_user.ainvoke({
        "summary": "正在分析您的研究问题...",
        "question": last_msg,
    })
    return {"messages": [HumanMessage(content=response)]}


def should_continue_clarify(state: ResearchState) -> str:
    """判断是否继续澄清"""
    last_msg = state["messages"][-1].content
    if "问题已明确" in last_msg or state["clarify_count"] >= 3:
        return "plan"
    return "ask_clarify"


async def plan_node(state: ResearchState) -> dict:
    """生成研究计划"""
    llm = _get_research_llm()
    # 收集所有用户消息作为上下文
    user_msgs = [m.content for m in state["messages"] if isinstance(m, HumanMessage)]
    context = "\n".join(user_msgs)

    result = await llm.ainvoke([
        SystemMessage(content=RESEARCH_PLAN_PROMPT),
        HumanMessage(content=context),
    ])

    try:
        plan = json.loads(result.content)
    except json.JSONDecodeError:
        logger.warning("研究计划解析失败，尝试提取列表")
        plan = [line.strip() for line in result.content.split("\n") if line.strip()]

    logger.info("深度研究 | 研究计划: {} 个子问题", len(plan))
    return {"plan": plan, "current_step": 0}


async def ask_plan_confirm_node(state: ResearchState) -> dict:
    """向用户展示研究计划并等待确认"""
    plan_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(state["plan"]))
    response = await ask_user.ainvoke({
        "summary": f"已制定研究计划，共 {len(state['plan'])} 个子问题：\n\n{plan_text}",
        "question": "请确认计划，或提出修改意见。回复"继续"开始执行。",
    })
    return {"messages": [HumanMessage(content=response)]}


async def research_step_node(state: ResearchState) -> dict:
    """执行当前子问题的检索"""
    step_idx = state["current_step"]
    if step_idx >= len(state["plan"]):
        return {}

    current_question = state["plan"][step_idx]
    logger.info("深度研究 | 执行子问题 {}/{}: {}", step_idx + 1, len(state["plan"]), current_question)

    llm = _get_research_llm()
    prompt = RESEARCH_STEP_PROMPT.format(current_question=current_question)

    # 用 ReAct agent 执行单个子问题
    step_agent = create_react_agent(
        llm,
        tools=[execute_sql, search_abstracts],
        prompt=prompt,
    )

    result = await step_agent.ainvoke({"messages": [HumanMessage(content=current_question)]})
    # 提取最后一条 AI 消息作为发现
    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content]
    finding = ai_messages[-1].content if ai_messages else "未找到相关结果"

    new_findings = list(state["findings"]) + [f"### 子问题 {step_idx + 1}: {current_question}\n\n{finding}"]

    return {
        "findings": new_findings,
        "current_step": step_idx + 1,
    }


async def ask_step_confirm_node(state: ResearchState) -> dict:
    """子问题执行后，向用户展示发现并等待指令"""
    latest_finding = state["findings"][-1] if state["findings"] else "无"
    step_idx = state["current_step"]
    total = len(state["plan"])

    question = "请选择：继续下一个子问题 / 调整方向（请说明）/ 直接生成总结"
    if step_idx >= total:
        question = "所有子问题已执行完毕。回复"总结"生成研究报告。"

    response = await ask_user.ainvoke({
        "summary": f"子问题 {step_idx}/{total} 完成。\n\n{latest_finding}",
        "question": question,
    })
    return {"messages": [HumanMessage(content=response)]}


def should_continue_research(state: ResearchState) -> str:
    """判断是否继续执行子问题"""
    last_msg = state["messages"][-1].content if state["messages"] else ""
    # 用户要求总结 或 所有子问题已完成
    if "总结" in last_msg or state["current_step"] >= len(state["plan"]):
        return "report"
    return "research_step"


async def report_node(state: ResearchState) -> dict:
    """生成最终研究报告"""
    llm = _get_research_llm()
    findings_text = "\n\n".join(state["findings"])
    prompt = RESEARCH_REPORT_PROMPT.format(findings=findings_text)

    result = await llm.ainvoke([SystemMessage(content=prompt)])
    report = result.content

    logger.info("深度研究 | 报告生成完成，长度={}", len(report))
    return {"messages": [AIMessage(content=report)]}


def build_research_subgraph() -> StateGraph:
    """构建深度研究 subgraph"""
    graph = StateGraph(ResearchState)

    graph.add_node("clarify", clarify_node)
    graph.add_node("ask_clarify", ask_clarify_node)
    graph.add_node("plan", plan_node)
    graph.add_node("ask_plan_confirm", ask_plan_confirm_node)
    graph.add_node("research_step", research_step_node)
    graph.add_node("ask_step_confirm", ask_step_confirm_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("clarify")
    graph.add_conditional_edges("clarify", should_continue_clarify, {
        "plan": "plan",
        "ask_clarify": "ask_clarify",
    })
    graph.add_edge("ask_clarify", "clarify")
    graph.add_edge("plan", "ask_plan_confirm")
    graph.add_edge("ask_plan_confirm", "research_step")
    graph.add_edge("research_step", "ask_step_confirm")
    graph.add_conditional_edges("ask_step_confirm", should_continue_research, {
        "research_step": "research_step",
        "report": "report",
    })
    graph.add_edge("report", END)

    return graph.compile()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_research.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/pipelines/research.py tests/test_research.py`
Expected: 无错误

- [ ] **Step 6: 提交**

```bash
git add src/deep_paper_qa/pipelines/research.py tests/test_research.py
git commit -m "feat: 实现深度研究显式多节点 pipeline"
```

---

### Task 8: 主图编排（重写 agent.py）

**Files:**
- Modify: `src/deep_paper_qa/agent.py`
- Modify: `tests/test_agent.py`

- [ ] **Step 1: 更新 agent 测试**

重写 `tests/test_agent.py`：

```python
"""主图构建测试"""

from unittest.mock import patch


class TestBuildGraph:
    """主图构建测试"""

    def test_graph_builds_successfully(self) -> None:
        """主图能正常构建"""
        from deep_paper_qa.agent import build_graph

        graph, checkpointer = build_graph()
        assert graph is not None
        assert checkpointer is not None

    def test_graph_has_correct_structure(self) -> None:
        """主图应包含正确的图结构"""
        from deep_paper_qa.agent import build_graph

        graph, _ = build_graph()
        assert hasattr(graph, "invoke")
        assert hasattr(graph, "ainvoke")


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

Run: `uv run pytest tests/test_agent.py::TestBuildGraph -v`
Expected: FAIL — `ImportError: cannot import name 'build_graph' from 'deep_paper_qa.agent'`

- [ ] **Step 3: 重写 agent.py**

将 `src/deep_paper_qa/agent.py` 完整重写为：

```python
"""主图构建：路由 + 各 Pipeline subgraph 编排"""

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from loguru import logger

from deep_paper_qa.models import RouteCategory
from deep_paper_qa.pipelines.compare import COMPARE_PLACEHOLDER, paper_compare_node
from deep_paper_qa.pipelines.general import build_general_subgraph
from deep_paper_qa.pipelines.reading import READING_PLACEHOLDER, paper_reading_node
from deep_paper_qa.pipelines.research import build_research_subgraph
from deep_paper_qa.pipelines.router import classify_question
from deep_paper_qa.pipelines.trend import build_trend_subgraph

# 拒答模板
REJECT_MESSAGE = "我是 AI 科研论文问答助手，只能回答与 AI 论文相关的问题。"


async def router_node(state: MessagesState) -> dict:
    """路由节点：提取用户最新消息并分类"""
    last_msg = state["messages"][-1].content
    category = await classify_question(last_msg)
    logger.info("路由决策 | category={}", category.value)
    return {"category": category.value}


async def reject_node(state: MessagesState) -> dict:
    """拒答节点"""
    return {"messages": [AIMessage(content=REJECT_MESSAGE)]}


def route_by_category(state: dict) -> str:
    """根据路由分类结果决定下一个节点"""
    category = state.get("category", "general")
    return category


class MainState(MessagesState):
    """主图状态"""

    category: str


def build_graph():
    """构建并返回主图 + checkpointer"""
    checkpointer = InMemorySaver()

    graph = StateGraph(MainState)

    # 添加节点
    graph.add_node("router", router_node)
    graph.add_node("reject", reject_node)
    graph.add_node("general", build_general_subgraph())
    graph.add_node("research", build_research_subgraph())
    graph.add_node("reading", paper_reading_node)
    graph.add_node("compare", paper_compare_node)
    graph.add_node("trend", build_trend_subgraph())

    # 设置入口
    graph.set_entry_point("router")

    # 路由条件边
    graph.add_conditional_edges("router", route_by_category, {
        "reject": "reject",
        "general": "general",
        "research": "research",
        "reading": "reading",
        "compare": "compare",
        "trend": "trend",
    })

    # 所有终端节点连接到 END
    graph.add_edge("reject", END)
    graph.add_edge("general", END)
    graph.add_edge("research", END)
    graph.add_edge("reading", END)
    graph.add_edge("compare", END)
    graph.add_edge("trend", END)

    compiled = graph.compile(checkpointer=checkpointer)
    return compiled, checkpointer
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_agent.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/agent.py tests/test_agent.py`
Expected: 无错误

- [ ] **Step 6: 提交**

```bash
git add src/deep_paper_qa/agent.py tests/test_agent.py
git commit -m "feat: 重写主图为路由 + 六 pipeline 架构"
```

---

### Task 9: 简化 app.py（移除 /research 前缀检测）

**Files:**
- Modify: `src/deep_paper_qa/app.py`

- [ ] **Step 1: 重写 app.py**

将 `src/deep_paper_qa/app.py` 完整重写。主要改动：
1. `build_agent()` 改为 `build_graph()`
2. 移除 `/research` 前缀检测逻辑
3. `recursion_limit` 统一为 50（各 pipeline 内部自行控制）

```python
"""Chainlit 入口：Agent 流式输出 + 中间步骤展示 + 日志记录"""

import time
import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_graph
from deep_paper_qa.conversation_logger import ConversationLogger
from deep_paper_qa.logging_setup import setup_logging

# 初始化日志
setup_logging()

# 全局 Graph 实例
_graph, _checkpointer = build_graph()

# 结构化事件记录器
_conv_logger = ConversationLogger()


@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    """提供示例问题，引导新用户快速上手"""
    return [
        cl.Starter(label="会议论文统计", message="各会议论文数量是多少？"),
        cl.Starter(label="RAG 研究趋势", message="RAG 最近几年的研究趋势怎么样？"),
        cl.Starter(label="高引论文推荐", message="推荐一些高引用的大语言模型论文"),
        cl.Starter(label="作者论文查询", message="Yann LeCun 发了哪些论文？"),
    ]


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
        "recursion_limit": 50,
    }

    # 记录用户消息
    logger.info("用户消息 | thread_id={} | content={}", thread_id, message.content)
    _conv_logger.log_user_message(thread_id, message.content)

    # 会话级统计
    msg_start = time.monotonic()
    tool_call_count = 0
    tools_used: list[str] = []
    tool_timings: dict[str, tuple[str, float]] = {}

    final_msg = cl.Message(content="")
    await final_msg.send()

    try:
        async for event in _graph.astream_events(
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
                    thread_id, tool_name, tool_input,
                )
                _conv_logger.log_tool_start(thread_id, tool_name, tool_input)

                tool_timings[run_id] = (tool_name, time.monotonic())
                tool_call_count += 1
                if tool_name not in tools_used:
                    tools_used.append(tool_name)

                if tool_name != "ask_user":
                    step = cl.Step(name=tool_name, type="tool")
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

                duration_ms = 0
                tool_name = "unknown"
                if run_id in tool_timings:
                    tool_name, start_t = tool_timings.pop(run_id)
                    duration_ms = int((time.monotonic() - start_t) * 1000)

                logger.info(
                    "Tool返回 | thread_id={} | tool={} | duration_ms={} | "
                    "output_len={} | output={}",
                    thread_id, tool_name, duration_ms,
                    len(output_str), output_str[:1000],
                )
                _conv_logger.log_tool_end(
                    thread_id, tool_name, duration_ms, output_str
                )

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

- [ ] **Step 2: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/app.py`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
git add src/deep_paper_qa/app.py
git commit -m "refactor: 简化 app.py，移除 /research 前缀检测"
```

---

### Task 10: 全量测试 + 最终验证

**Files:**
- 无新文件

- [ ] **Step 1: 运行全量测试**

Run: `uv run pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 2: 运行 lint + format**

Run: `uv run ruff check src/ tests/ && uv run ruff format src/ tests/`
Expected: 无错误

- [ ] **Step 3: 验证应用启动**

Run: `uv run chainlit run src/deep_paper_qa/app.py --port 8000 &`
等待启动后访问 http://localhost:8000 确认页面加载正常，然后 `kill %1` 停止。

- [ ] **Step 4: 提交最终状态（如有 format 改动）**

```bash
git add -A
git commit -m "style: ruff format 格式化"
```
