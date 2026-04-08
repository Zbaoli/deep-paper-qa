"""search_semantic_scholar 工具测试"""

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
            result = await search_semantic_scholar.ainvoke({"query": "RAG", "year": "2024-2026"})
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
