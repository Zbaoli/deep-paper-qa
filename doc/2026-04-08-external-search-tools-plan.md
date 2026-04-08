# 外部搜索工具集成 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 LangGraph 多管线 Agent 增加 3 个外部搜索工具（search_arxiv, search_semantic_scholar, search_web），实现"本地优先，fallback 联网"的检索策略。

**Architecture:** 3 个独立的 `@tool` 文件放在 `src/deep_paper_qa/tools/` 下，全部用 `aiohttp` 直接调 API，不引入新 SDK。通过 prompt 策略指导 Agent 何时使用外部工具。所有管线均可使用这 6 个工具。

**Tech Stack:** aiohttp, xml.etree.ElementTree (stdlib), langchain_core.tools, loguru, pydantic-settings

---

### Task 1: config.py 新增外部搜索配置

**Files:**
- Modify: `src/deep_paper_qa/config.py:6-36`
- Modify: `.env.example`

- [ ] **Step 1: 在 Settings 类中添加外部搜索配置字段**

在 `src/deep_paper_qa/config.py` 的 `Settings` 类中，`max_conversation_turns` 之后、`model_config` 之前添加：

```python
    # 外部搜索 API
    arxiv_max_results: int = 5
    semantic_scholar_api_key: str = ""
    semantic_scholar_max_results: int = 5
    tavily_api_key: str = ""
    tavily_max_results: int = 5
    external_search_timeout: int = 15
```

- [ ] **Step 2: 更新 .env.example**

在 `.env.example` 末尾追加：

```
# 外部搜索 API（可选）
SEMANTIC_SCHOLAR_API_KEY=
TAVILY_API_KEY=
```

- [ ] **Step 3: 验证配置加载**

运行: `uv run python -c "from deep_paper_qa.config import settings; print(settings.external_search_timeout, settings.tavily_api_key)"`
预期输出: `15 `（空字符串）

- [ ] **Step 4: 提交**

```bash
git add src/deep_paper_qa/config.py .env.example
git commit -m "feat: config 新增外部搜索 API 配置项"
```

---

### Task 2: 实现 search_arxiv 工具

**Files:**
- Create: `src/deep_paper_qa/tools/search_arxiv.py`
- Create: `tests/test_search_arxiv.py`

- [ ] **Step 1: 编写 search_arxiv 测试**

创建 `tests/test_search_arxiv.py`：

```python
"""search_arxiv 工具测试"""

from unittest.mock import AsyncMock, patch

import pytest

from deep_paper_qa.tools.search_arxiv import search_arxiv

# arXiv API 返回的 Atom XML 样例
SAMPLE_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1</totalResults>
  <entry>
    <id>http://arxiv.org/abs/2312.10997v1</id>
    <title>Retrieval-Augmented Generation for Large Language Models: A Survey</title>
    <summary>Large language models have shown remarkable capabilities but still face challenges such as hallucination. Retrieval-Augmented Generation (RAG) has emerged as a promising approach.</summary>
    <published>2023-12-18T00:00:00Z</published>
    <updated>2023-12-18T00:00:00Z</updated>
    <author><name>Yunfan Gao</name></author>
    <author><name>Yun Xiong</name></author>
    <author><name>Xinyu Gao</name></author>
    <author><name>Others</name></author>
    <arxiv:primary_category term="cs.CL"/>
    <link href="http://arxiv.org/abs/2312.10997v1" rel="alternate" type="text/html"/>
    <link href="http://arxiv.org/pdf/2312.10997v1" title="pdf" rel="related" type="application/pdf"/>
  </entry>
</feed>"""

EMPTY_ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">0</totalResults>
</feed>"""


def _mock_response(text: str, status: int = 200):
    """构造 mock aiohttp response"""
    resp = AsyncMock()
    resp.status = status
    resp.text = AsyncMock(return_value=text)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _mock_session(response):
    """构造 mock aiohttp.ClientSession"""
    session = AsyncMock()
    session.get = AsyncMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


class TestSearchArxiv:
    """search_arxiv 工具测试"""

    @pytest.mark.asyncio
    async def test_normal_search(self) -> None:
        """正常搜索返回格式化结果"""
        response = _mock_response(SAMPLE_ARXIV_XML)
        session = _mock_session(response)

        with patch("deep_paper_qa.tools.search_arxiv.aiohttp.ClientSession", return_value=session):
            result = await search_arxiv.ainvoke({"query": "RAG survey"})
            assert "Retrieval-Augmented Generation" in result
            assert "Yunfan Gao" in result
            assert "2023" in result
            assert "cs.CL" in result
            assert "arxiv.org" in result

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        """无结果时返回提示"""
        response = _mock_response(EMPTY_ARXIV_XML)
        session = _mock_session(response)

        with patch("deep_paper_qa.tools.search_arxiv.aiohttp.ClientSession", return_value=session):
            result = await search_arxiv.ainvoke({"query": "nonexistent xyz"})
            assert "未找到" in result

    @pytest.mark.asyncio
    async def test_with_category(self) -> None:
        """带分类过滤的搜索"""
        response = _mock_response(SAMPLE_ARXIV_XML)
        session = _mock_session(response)

        with patch("deep_paper_qa.tools.search_arxiv.aiohttp.ClientSession", return_value=session):
            result = await search_arxiv.ainvoke(
                {"query": "RAG", "category": "cs.CL", "max_results": 3}
            )
            assert "Retrieval-Augmented Generation" in result
            # 验证请求 URL 中包含 category
            call_args = session.get.call_args
            assert "cs.CL" in str(call_args)

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        """超时时返回提示"""
        import asyncio

        response = _mock_response("")
        session = _mock_session(response)
        session.get = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("deep_paper_qa.tools.search_arxiv.aiohttp.ClientSession", return_value=session):
            result = await search_arxiv.ainvoke({"query": "test"})
            assert "超时" in result or "暂不可用" in result

    @pytest.mark.asyncio
    async def test_network_error(self) -> None:
        """网络错误时返回提示"""
        import aiohttp

        response = _mock_response("")
        session = _mock_session(response)
        session.get = AsyncMock(side_effect=aiohttp.ClientError("Connection refused"))

        with patch("deep_paper_qa.tools.search_arxiv.aiohttp.ClientSession", return_value=session):
            result = await search_arxiv.ainvoke({"query": "test"})
            assert "暂不可用" in result
```

- [ ] **Step 2: 运行测试确认失败**

运行: `uv run pytest tests/test_search_arxiv.py -v`
预期: FAIL（模块不存在）

- [ ] **Step 3: 实现 search_arxiv 工具**

创建 `src/deep_paper_qa/tools/search_arxiv.py`：

```python
"""search_arxiv 工具：搜索 arXiv 预印本论文"""

import asyncio
import xml.etree.ElementTree as ET
from urllib.parse import quote

import aiohttp
from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings

_ARXIV_API = "http://export.arxiv.org/api/query"
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _parse_entries(xml_text: str) -> list[dict]:
    """解析 arXiv Atom XML 返回条目列表"""
    root = ET.fromstring(xml_text)
    entries = []
    for entry in root.findall("atom:entry", _NS):
        # 标题
        title_el = entry.find("atom:title", _NS)
        title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""

        # 作者（取前 3）
        authors_els = entry.findall("atom:author/atom:name", _NS)
        authors = [a.text.strip() for a in authors_els[:3] if a.text]
        if len(authors_els) > 3:
            authors.append(f"等共 {len(authors_els)} 位作者")

        # 摘要
        summary_el = entry.find("atom:summary", _NS)
        abstract = (summary_el.text or "").strip().replace("\n", " ") if summary_el is not None else ""
        if len(abstract) > settings.abstract_max_chars:
            abstract = abstract[: settings.abstract_max_chars] + "..."

        # 发布年份
        published_el = entry.find("atom:published", _NS)
        year = (published_el.text or "")[:4] if published_el is not None else ""

        # 分类
        cat_el = entry.find("arxiv:primary_category", _NS)
        category = cat_el.get("term", "") if cat_el is not None else ""

        # 链接
        arxiv_url = ""
        pdf_url = ""
        for link in entry.findall("atom:link", _NS):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
            elif link.get("rel") == "alternate":
                arxiv_url = link.get("href", "")

        entries.append(
            {
                "title": title,
                "authors": authors,
                "year": year,
                "category": category,
                "abstract": abstract,
                "url": arxiv_url,
                "pdf_url": pdf_url,
            }
        )
    return entries


def _format_results(entries: list[dict]) -> str:
    """格式化结果为可读字符串"""
    if not entries:
        return "未找到相关 arXiv 论文。可尝试换用英文关键词或更宽泛的搜索词。"

    lines: list[str] = []
    for i, e in enumerate(entries, 1):
        authors_str = ", ".join(e["authors"])
        lines.append(f"[{i}] {e['title']}")
        lines.append(f"    作者: {authors_str} | 年份: {e['year']} | 分类: {e['category']}")
        if e["abstract"]:
            lines.append(f"    摘要: {e['abstract']}")
        lines.append(f"    链接: {e['url']}")
        lines.append("")

    lines.append(f"共找到 {len(entries)} 篇 arXiv 论文。")
    return "\n".join(lines)


@tool
async def search_arxiv(
    query: str,
    max_results: int = 5,
    category: str = "",
) -> str:
    """搜索 arXiv 预印本论文。适用于：查找最新预印本、数据库未收录的论文、特定 arXiv 分类下的论文。

    注意：本地数据库已包含 2020-2025 年主流 AI 会议论文。仅在以下情况使用此工具：
    - 需要查找最新预印本（尚未被会议收录）
    - 需要查找本地数据库未收录的会议/领域的论文
    - 用户明确要求搜索 arXiv

    Args:
        query: 搜索关键词（英文）
        max_results: 最多返回条数，默认 5，最大 10
        category: arXiv 分类过滤，如 "cs.CL"、"cs.AI"、"cs.LG"。留空不过滤。
    """
    max_results = min(max_results, 10)
    logger.info("search_arxiv 查询: '{}', category='{}', max_results={}", query[:200], category, max_results)

    search_query = f"all:{quote(query)}"
    if category:
        search_query += f"+AND+cat:{category}"

    url = f"{_ARXIV_API}?search_query={search_query}&sortBy=relevance&sortOrder=descending&max_results={max_results}"

    try:
        timeout = aiohttp.ClientTimeout(total=settings.external_search_timeout)
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=timeout) as resp:
                if resp.status != 200:
                    logger.warning("arXiv API 返回错误: status={}", resp.status)
                    return f"arXiv API 返回错误 ({resp.status})，请稍后重试。"
                xml_text = await resp.text()

        entries = _parse_entries(xml_text)
        result = _format_results(entries)
        logger.info("search_arxiv 返回 {} 条结果", len(entries))
        return result
    except asyncio.TimeoutError:
        logger.warning("search_arxiv 查询超时: {}", query[:100])
        return "arXiv 搜索超时，请稍后重试或使用本地数据库查询。"
    except aiohttp.ClientError as e:
        logger.warning("search_arxiv 网络错误: {}", e)
        return "arXiv 服务暂不可用，请使用本地数据库查询。"
    except ET.ParseError as e:
        logger.error("search_arxiv XML 解析失败: {}", e)
        return "arXiv 返回数据解析失败，请稍后重试。"
```

- [ ] **Step 4: 运行测试确认通过**

运行: `uv run pytest tests/test_search_arxiv.py -v`
预期: 5 passed

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/tools/search_arxiv.py tests/test_search_arxiv.py
git commit -m "feat: 实现 search_arxiv 工具（arXiv API 搜索）"
```

---

### Task 3: 实现 search_semantic_scholar 工具

**Files:**
- Create: `src/deep_paper_qa/tools/search_semantic_scholar.py`
- Create: `tests/test_search_semantic_scholar.py`

- [ ] **Step 1: 编写 search_semantic_scholar 测试**

创建 `tests/test_search_semantic_scholar.py`：

```python
"""search_semantic_scholar 工具测试"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from deep_paper_qa.tools.search_semantic_scholar import search_semantic_scholar

SAMPLE_S2_RESPONSE = {
    "total": 1,
    "data": [
        {
            "paperId": "abc123",
            "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
            "abstract": "Large pre-trained language models have been shown to store factual knowledge in their parameters. However, their ability to access and manipulate knowledge is limited.",
            "year": 2020,
            "citationCount": 3500,
            "venue": "NeurIPS",
            "authors": [
                {"name": "Patrick Lewis"},
                {"name": "Ethan Perez"},
                {"name": "Aleksandra Piktus"},
                {"name": "Fabio Petroni"},
            ],
            "openAccessPdf": {"url": "https://arxiv.org/pdf/2005.11401.pdf"},
            "externalIds": {"ArXiv": "2005.11401"},
        }
    ],
}

EMPTY_S2_RESPONSE = {"total": 0, "data": []}


def _mock_response(data: dict, status: int = 200):
    """构造 mock aiohttp response"""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=data)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _mock_session(response):
    """构造 mock aiohttp.ClientSession"""
    session = AsyncMock()
    session.get = AsyncMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


class TestSearchSemanticScholar:
    """search_semantic_scholar 工具测试"""

    @pytest.mark.asyncio
    async def test_normal_search(self) -> None:
        """正常搜索返回格式化结果"""
        response = _mock_response(SAMPLE_S2_RESPONSE)
        session = _mock_session(response)

        with patch(
            "deep_paper_qa.tools.search_semantic_scholar.aiohttp.ClientSession",
            return_value=session,
        ):
            result = await search_semantic_scholar.ainvoke({"query": "RAG"})
            assert "Retrieval-Augmented Generation" in result
            assert "Patrick Lewis" in result
            assert "3500" in result
            assert "NeurIPS" in result
            assert "2020" in result

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        """无结果时返回提示"""
        response = _mock_response(EMPTY_S2_RESPONSE)
        session = _mock_session(response)

        with patch(
            "deep_paper_qa.tools.search_semantic_scholar.aiohttp.ClientSession",
            return_value=session,
        ):
            result = await search_semantic_scholar.ainvoke({"query": "nonexistent xyz"})
            assert "未找到" in result

    @pytest.mark.asyncio
    async def test_with_year_filter(self) -> None:
        """带年份过滤的搜索"""
        response = _mock_response(SAMPLE_S2_RESPONSE)
        session = _mock_session(response)

        with patch(
            "deep_paper_qa.tools.search_semantic_scholar.aiohttp.ClientSession",
            return_value=session,
        ):
            result = await search_semantic_scholar.ainvoke(
                {"query": "RAG", "year": "2024-2026"}
            )
            assert "Retrieval-Augmented Generation" in result
            # 验证请求参数包含 year
            call_args = session.get.call_args
            assert "year" in str(call_args)

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        """超时时返回提示"""
        import asyncio

        response = _mock_response({})
        session = _mock_session(response)
        session.get = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch(
            "deep_paper_qa.tools.search_semantic_scholar.aiohttp.ClientSession",
            return_value=session,
        ):
            result = await search_semantic_scholar.ainvoke({"query": "test"})
            assert "超时" in result or "暂不可用" in result

    @pytest.mark.asyncio
    async def test_rate_limit(self) -> None:
        """429 限频时返回提示"""
        response = _mock_response({}, status=429)
        session = _mock_session(response)

        with patch(
            "deep_paper_qa.tools.search_semantic_scholar.aiohttp.ClientSession",
            return_value=session,
        ):
            result = await search_semantic_scholar.ainvoke({"query": "test"})
            assert "429" in result or "限频" in result or "稍后" in result
```

- [ ] **Step 2: 运行测试确认失败**

运行: `uv run pytest tests/test_search_semantic_scholar.py -v`
预期: FAIL（模块不存在）

- [ ] **Step 3: 实现 search_semantic_scholar 工具**

创建 `src/deep_paper_qa/tools/search_semantic_scholar.py`：

```python
"""search_semantic_scholar 工具：搜索 Semantic Scholar 学术论文"""

import asyncio

import aiohttp
from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings

_S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
_S2_FIELDS = "title,abstract,year,citationCount,authors,venue,openAccessPdf,externalIds"


def _format_results(data: dict) -> str:
    """格式化 Semantic Scholar API 响应"""
    papers = data.get("data", [])
    if not papers:
        return "未找到相关论文。"

    lines: list[str] = []
    for i, p in enumerate(papers, 1):
        title = p.get("title", "")
        year = p.get("year", "")
        venue = p.get("venue", "")
        citations = p.get("citationCount", 0)

        # 作者（取前 3）
        authors_raw = p.get("authors", [])
        authors = [a.get("name", "") for a in authors_raw[:3]]
        if len(authors_raw) > 3:
            authors.append(f"等共 {len(authors_raw)} 位作者")
        authors_str = ", ".join(authors)

        # 摘要截断
        abstract = (p.get("abstract") or "").strip().replace("\n", " ")
        if len(abstract) > settings.abstract_max_chars:
            abstract = abstract[: settings.abstract_max_chars] + "..."

        # PDF 链接
        pdf_info = p.get("openAccessPdf") or {}
        pdf_url = pdf_info.get("url", "")

        # arXiv ID
        ext_ids = p.get("externalIds") or {}
        arxiv_id = ext_ids.get("ArXiv", "")

        lines.append(f"[{i}] {title}")
        meta_parts = [f"作者: {authors_str}"]
        if year:
            meta_parts.append(f"年份: {year}")
        if venue:
            meta_parts.append(f"venue: {venue}")
        meta_parts.append(f"引用: {citations}")
        lines.append(f"    {' | '.join(meta_parts)}")
        if abstract:
            lines.append(f"    摘要: {abstract}")
        if pdf_url:
            lines.append(f"    PDF: {pdf_url}")
        elif arxiv_id:
            lines.append(f"    arXiv: {arxiv_id}")
        lines.append("")

    lines.append(f"共找到 {len(papers)} 篇论文（Semantic Scholar）。")
    return "\n".join(lines)


@tool
async def search_semantic_scholar(
    query: str,
    max_results: int = 5,
    fields_of_study: str = "",
    year: str = "",
) -> str:
    """搜索 Semantic Scholar 学术论文数据库。适用于：查询引用数据、跨数据库搜索论文、按领域和年份过滤。

    注意：本地数据库已包含 2020-2025 年主流 AI 会议论文。仅在以下情况使用此工具：
    - 需要引用数据（本地数据库引用数可能不准确或缺失）
    - 需要查找本地数据库未收录的论文
    - 需要跨领域搜索（非 AI 顶会论文）

    Args:
        query: 搜索关键词（英文）
        max_results: 最多返回条数，默认 5，最大 10
        fields_of_study: 领域过滤，如 "Computer Science"。留空不过滤。
        year: 年份过滤，如 "2024-2026" 或 "2025"。留空不过滤。
    """
    max_results = min(max_results, 10)
    logger.info(
        "search_semantic_scholar 查询: '{}', fields='{}', year='{}', max={}",
        query[:200], fields_of_study, year, max_results,
    )

    params: dict[str, str] = {
        "query": query,
        "limit": str(max_results),
        "fields": _S2_FIELDS,
    }
    if fields_of_study:
        params["fieldsOfStudy"] = fields_of_study
    if year:
        params["year"] = year

    headers: dict[str, str] = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key

    try:
        timeout = aiohttp.ClientTimeout(total=settings.external_search_timeout)
        async with aiohttp.ClientSession() as session:
            async with session.get(_S2_API, params=params, headers=headers, timeout=timeout) as resp:
                if resp.status == 429:
                    logger.warning("Semantic Scholar API 限频 (429)")
                    return "Semantic Scholar API 请求限频 (429)，请稍后重试。"
                if resp.status != 200:
                    logger.warning("Semantic Scholar API 返回错误: status={}", resp.status)
                    return f"Semantic Scholar API 返回错误 ({resp.status})，请稍后重试。"
                data = await resp.json()

        result = _format_results(data)
        logger.info("search_semantic_scholar 返回 {} 条结果", len(data.get("data", [])))
        return result
    except asyncio.TimeoutError:
        logger.warning("search_semantic_scholar 查询超时: {}", query[:100])
        return "Semantic Scholar 搜索超时，请稍后重试或使用本地数据库查询。"
    except aiohttp.ClientError as e:
        logger.warning("search_semantic_scholar 网络错误: {}", e)
        return "Semantic Scholar 服务暂不可用，请使用本地数据库查询。"
```

- [ ] **Step 4: 运行测试确认通过**

运行: `uv run pytest tests/test_search_semantic_scholar.py -v`
预期: 5 passed

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/tools/search_semantic_scholar.py tests/test_search_semantic_scholar.py
git commit -m "feat: 实现 search_semantic_scholar 工具（Semantic Scholar API 搜索）"
```

---

### Task 4: 实现 search_web 工具

**Files:**
- Create: `src/deep_paper_qa/tools/search_web.py`
- Create: `tests/test_search_web.py`

- [ ] **Step 1: 编写 search_web 测试**

创建 `tests/test_search_web.py`：

```python
"""search_web 工具测试"""

from unittest.mock import AsyncMock, patch

import pytest

from deep_paper_qa.tools.search_web import search_web

SAMPLE_TAVILY_RESPONSE = {
    "results": [
        {
            "title": "ICML 2026 - Call for Papers",
            "url": "https://icml.cc/2026/call-for-papers",
            "content": "ICML 2026 will be held in San Francisco. Paper submission deadline: January 31, 2026.",
            "score": 0.95,
        },
        {
            "title": "ICML 2026 Important Dates",
            "url": "https://icml.cc/2026/dates",
            "content": "Abstract deadline: January 24, 2026. Full paper deadline: January 31, 2026.",
            "score": 0.88,
        },
    ]
}

EMPTY_TAVILY_RESPONSE = {"results": []}


def _mock_response(data: dict, status: int = 200):
    """构造 mock aiohttp response"""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=data)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=False)
    return resp


def _mock_session(response):
    """构造 mock aiohttp.ClientSession"""
    session = AsyncMock()
    session.post = AsyncMock(return_value=response)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return session


class TestSearchWeb:
    """search_web 工具测试"""

    @pytest.mark.asyncio
    async def test_normal_search(self) -> None:
        """正常搜索返回格式化结果"""
        response = _mock_response(SAMPLE_TAVILY_RESPONSE)
        session = _mock_session(response)

        with (
            patch("deep_paper_qa.tools.search_web.aiohttp.ClientSession", return_value=session),
            patch("deep_paper_qa.tools.search_web.settings") as mock_settings,
        ):
            mock_settings.tavily_api_key = "test-key"
            mock_settings.tavily_max_results = 5
            mock_settings.external_search_timeout = 15
            result = await search_web.ainvoke({"query": "ICML 2026 deadline"})
            assert "ICML 2026" in result
            assert "January 31" in result or "icml.cc" in result

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        """无结果时返回提示"""
        response = _mock_response(EMPTY_TAVILY_RESPONSE)
        session = _mock_session(response)

        with (
            patch("deep_paper_qa.tools.search_web.aiohttp.ClientSession", return_value=session),
            patch("deep_paper_qa.tools.search_web.settings") as mock_settings,
        ):
            mock_settings.tavily_api_key = "test-key"
            mock_settings.tavily_max_results = 5
            mock_settings.external_search_timeout = 15
            result = await search_web.ainvoke({"query": "nonexistent xyz"})
            assert "未找到" in result

    @pytest.mark.asyncio
    async def test_no_api_key(self) -> None:
        """未配置 API key 时返回提示"""
        with patch("deep_paper_qa.tools.search_web.settings") as mock_settings:
            mock_settings.tavily_api_key = ""
            result = await search_web.ainvoke({"query": "test"})
            assert "未配置" in result or "API key" in result

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        """超时时返回提示"""
        import asyncio

        response = _mock_response({})
        session = _mock_session(response)
        session.post = AsyncMock(side_effect=asyncio.TimeoutError())

        with (
            patch("deep_paper_qa.tools.search_web.aiohttp.ClientSession", return_value=session),
            patch("deep_paper_qa.tools.search_web.settings") as mock_settings,
        ):
            mock_settings.tavily_api_key = "test-key"
            mock_settings.tavily_max_results = 5
            mock_settings.external_search_timeout = 15
            result = await search_web.ainvoke({"query": "test"})
            assert "超时" in result or "暂不可用" in result
```

- [ ] **Step 2: 运行测试确认失败**

运行: `uv run pytest tests/test_search_web.py -v`
预期: FAIL（模块不存在）

- [ ] **Step 3: 实现 search_web 工具**

创建 `src/deep_paper_qa/tools/search_web.py`：

```python
"""search_web 工具：Tavily 通用网络搜索"""

import asyncio

import aiohttp
from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings

_TAVILY_API = "https://api.tavily.com/search"


def _format_results(data: dict) -> str:
    """格式化 Tavily 搜索结果"""
    results = data.get("results", [])
    if not results:
        return "未找到相关网页结果。"

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "").strip().replace("\n", " ")
        score = r.get("score", 0)

        if len(content) > 500:
            content = content[:500] + "..."

        lines.append(f"[{i}] {title}")
        lines.append(f"    链接: {url}")
        lines.append(f"    摘要: {content}")
        lines.append(f"    相关度: {score:.2f}")
        lines.append("")

    lines.append(f"共找到 {len(results)} 条网页结果。")
    return "\n".join(lines)


@tool
async def search_web(
    query: str,
    max_results: int = 5,
) -> str:
    """搜索互联网获取最新信息。适用于：查找非论文信息，如会议日期、行业动态、开源项目、博客文章、教程等。

    注意：此工具搜索整个互联网，不限于学术论文。仅在以下情况使用此工具：
    - 需要非学术信息（会议截止日期、行业新闻、产品发布等）
    - 需要查找开源项目、GitHub 仓库、技术博客
    - 其他学术搜索工具无法回答的问题

    Args:
        query: 搜索关键词
        max_results: 最多返回条数，默认 5，最大 10
    """
    max_results = min(max_results, 10)
    logger.info("search_web 查询: '{}', max_results={}", query[:200], max_results)

    if not settings.tavily_api_key:
        return "Tavily API key 未配置，无法进行网络搜索。请在 .env 中设置 TAVILY_API_KEY。"

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }

    try:
        timeout = aiohttp.ClientTimeout(total=settings.external_search_timeout)
        async with aiohttp.ClientSession() as session:
            async with session.post(_TAVILY_API, json=payload, timeout=timeout) as resp:
                if resp.status != 200:
                    logger.warning("Tavily API 返回错误: status={}", resp.status)
                    return f"Tavily API 返回错误 ({resp.status})，请稍后重试。"
                data = await resp.json()

        result = _format_results(data)
        logger.info("search_web 返回 {} 条结果", len(data.get("results", [])))
        return result
    except asyncio.TimeoutError:
        logger.warning("search_web 查询超时: {}", query[:100])
        return "网络搜索超时，请稍后重试。"
    except aiohttp.ClientError as e:
        logger.warning("search_web 网络错误: {}", e)
        return "网络搜索服务暂不可用，请稍后重试。"
```

- [ ] **Step 4: 运行测试确认通过**

运行: `uv run pytest tests/test_search_web.py -v`
预期: 4 passed

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/tools/search_web.py tests/test_search_web.py
git commit -m "feat: 实现 search_web 工具（Tavily 网络搜索）"
```

---

### Task 5: 更新 Prompt 策略

**Files:**
- Modify: `src/deep_paper_qa/prompts.py:40-111` (GENERAL_PROMPT)
- Modify: `src/deep_paper_qa/prompts.py:132-140` (RESEARCH_STEP_PROMPT)

- [ ] **Step 1: 在 GENERAL_PROMPT 末尾追加外部搜索工具说明**

在 `src/deep_paper_qa/prompts.py` 的 `GENERAL_PROMPT` 中，在 `回答规则：` 段之前（第 108 行之前），插入：

```python
3. search_arxiv: 搜索 arXiv 预印本论文。
   适用场景：查找最新预印本、数据库未收录的论文、特定 arXiv 分类的论文。
   可选参数 category：arXiv 分类，如 "cs.CL", "cs.AI"。

4. search_semantic_scholar: 搜索 Semantic Scholar 学术论文数据库。
   适用场景：查询引用数据、跨数据库搜索论文、按领域和年份过滤。
   可选参数 fields_of_study, year。

5. search_web: 搜索互联网获取最新信息。
   适用场景：非论文信息（会议日期、行业动态、开源项目、博客、教程）。

外部搜索使用原则：
- **本地优先**：优先使用 execute_sql 和 search_abstracts 查询本地数据库
- **联网补充**：以下情况使用外部搜索工具：
  - 本地搜索结果不足（少于 3 条相关结果）
  - 用户明确询问数据库范围外的内容（2026年论文、非收录会议、非论文信息）
  - 需要引用数据、论文推荐等本地数据库不具备的信息
```

同时更新工具选择规则和效率规则：

- 工具选择规则中增加：`联网查最新/外部论文 → search_arxiv 或 search_semantic_scholar`、`非学术信息 → search_web`
- 效率规则中 tool call 上限从 4 调到 6

- [ ] **Step 2: 更新 RESEARCH_STEP_PROMPT 中的工具列表**

将 `RESEARCH_STEP_PROMPT`（第 132-140 行）中的 `你有两个工具：execute_sql 和 search_abstracts。` 改为：

```
你有五个工具：execute_sql、search_abstracts（本地数据库）和 search_arxiv、search_semantic_scholar、search_web（外部搜索）。
优先使用本地工具，结果不足时用外部工具补充。最多调用 3 次工具。
```

- [ ] **Step 3: 运行现有测试确认不破坏**

运行: `uv run pytest tests/ -v`
预期: 全部通过

- [ ] **Step 4: 提交**

```bash
git add src/deep_paper_qa/prompts.py
git commit -m "feat: prompt 策略增加外部搜索工具说明和本地优先规则"
```

---

### Task 6: 各管线注册新工具

**Files:**
- Modify: `src/deep_paper_qa/pipelines/general.py:11-32`
- Modify: `src/deep_paper_qa/pipelines/research.py:19-21,109`
- Modify: `src/deep_paper_qa/pipelines/trend.py:19-20,91`

- [ ] **Step 1: 更新 general.py 导入和 tools 列表**

在 `src/deep_paper_qa/pipelines/general.py` 中：

添加导入（第 11 行后）：
```python
from deep_paper_qa.tools.search_arxiv import search_arxiv
from deep_paper_qa.tools.search_semantic_scholar import search_semantic_scholar
from deep_paper_qa.tools.search_web import search_web
```

修改 `build_general_subgraph` 中的 tools 参数（第 32 行）：
```python
        tools=[execute_sql, search_abstracts, search_arxiv, search_semantic_scholar, search_web],
```

- [ ] **Step 2: 更新 research.py 导入和 tools 列表**

在 `src/deep_paper_qa/pipelines/research.py` 中：

添加导入（第 21 行后）：
```python
from deep_paper_qa.tools.search_arxiv import search_arxiv
from deep_paper_qa.tools.search_semantic_scholar import search_semantic_scholar
from deep_paper_qa.tools.search_web import search_web
```

修改 `research_step_node` 中创建 step_agent 的 tools 参数（第 109 行）：
```python
    step_agent = create_react_agent(llm, tools=[execute_sql, search_abstracts, search_arxiv, search_semantic_scholar, search_web], prompt=prompt)
```

- [ ] **Step 3: 更新 trend.py 导入和工具使用**

在 `src/deep_paper_qa/pipelines/trend.py` 中：

添加导入（第 20 行后）：
```python
from deep_paper_qa.tools.search_arxiv import search_arxiv
from deep_paper_qa.tools.search_semantic_scholar import search_semantic_scholar
from deep_paper_qa.tools.search_web import search_web
```

trend 管线是固定流程（非 ReAct），工具通过 `.ainvoke()` 直接调用。当前 `search_representatives_node` 只用 `search_abstracts`。趋势管线不需要改动工具调用逻辑——新工具已通过 import 可用，但固定流程中暂无需主动使用外部搜索。

> 注意：reading.py 和 compare.py 是 P2 占位节点，不包含工具调用，无需修改。

- [ ] **Step 4: 运行全部测试确认不破坏**

运行: `uv run pytest tests/ -v`
预期: 全部通过

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/pipelines/general.py src/deep_paper_qa/pipelines/research.py src/deep_paper_qa/pipelines/trend.py
git commit -m "feat: 各管线注册外部搜索工具"
```

---

### Task 7: 运行全量测试 + lint

**Files:**
- 无新文件

- [ ] **Step 1: 运行 ruff lint**

运行: `uv run ruff check src/deep_paper_qa/tools/search_arxiv.py src/deep_paper_qa/tools/search_semantic_scholar.py src/deep_paper_qa/tools/search_web.py`
预期: 无错误

- [ ] **Step 2: 运行 ruff format**

运行: `uv run ruff format src/ tests/`
预期: 格式化完成

- [ ] **Step 3: 运行全量测试**

运行: `uv run pytest tests/ -v`
预期: 全部通过（含新增的 14 个测试）

- [ ] **Step 4: 提交格式化修改（如有）**

```bash
git add -u
git commit -m "style: ruff format 格式化"
```

---

### Task 8: 更新 CLAUDE.md 架构文档

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 更新架构图**

在 `CLAUDE.md` 的架构部分，更新工具列表：

```
Chainlit UI (app.py)
  └─ LangGraph 多管线 Agent (agent.py) + InMemorySaver
       ├─ execute_sql    — asyncpg → PostgreSQL（元数据统计，仅 SELECT）
       ├─ search_abstracts — 全文检索 + 向量语义检索（本地数据库）
       ├─ search_arxiv   — aiohttp → arXiv API（最新预印本）
       ├─ search_semantic_scholar — aiohttp → Semantic Scholar API（引用数据、跨库搜索）
       └─ search_web     — aiohttp → Tavily API（网络搜索、非学术信息）
```

- [ ] **Step 2: 更新配置说明**

在配置部分追加：

```
- `SEMANTIC_SCHOLAR_API_KEY` — Semantic Scholar API key（可选，提高速率限制）
- `TAVILY_API_KEY` — Tavily Search API key（必填，启用网络搜索）
```

- [ ] **Step 3: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: CLAUDE.md 更新架构图和配置说明"
```
