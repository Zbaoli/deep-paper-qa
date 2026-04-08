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
