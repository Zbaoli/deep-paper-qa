"""路由分类测试"""

from unittest.mock import AsyncMock, patch

import pytest

from deep_paper_qa.models import RouteCategory, RouterOutput
from deep_paper_qa.pipelines.router import classify_question


class TestRouterOutput:
    """路由输出模型测试"""

    def test_valid_category(self) -> None:
        output = RouterOutput(category=RouteCategory.GENERAL)
        assert output.category == RouteCategory.GENERAL

    def test_all_categories_exist(self) -> None:
        expected = {"reject", "general", "research", "reading", "compare", "trend"}
        actual = {c.value for c in RouteCategory}
        assert actual == expected


class TestClassifyQuestion:
    """路由分类函数测试"""

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router._get_router_llm")
    async def test_general_question(self, mock_get_llm: AsyncMock) -> None:
        from deep_paper_qa.models import RouterOutput

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = RouterOutput(category=RouteCategory.GENERAL)
        mock_get_llm.return_value = mock_llm
        result = await classify_question("2024年NeurIPS收录了多少篇论文？")
        assert result == RouteCategory.GENERAL

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router._get_router_llm")
    async def test_reject_question(self, mock_get_llm: AsyncMock) -> None:
        from deep_paper_qa.models import RouterOutput

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = RouterOutput(category=RouteCategory.REJECT)
        mock_get_llm.return_value = mock_llm
        result = await classify_question("今天天气怎么样？")
        assert result == RouteCategory.REJECT

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router._get_router_llm")
    async def test_research_question(self, mock_get_llm: AsyncMock) -> None:
        from deep_paper_qa.models import RouterOutput

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = RouterOutput(category=RouteCategory.RESEARCH)
        mock_get_llm.return_value = mock_llm
        result = await classify_question("总结 2023-2025 年 LLM Agent 的研究脉络")
        assert result == RouteCategory.RESEARCH

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router._get_router_llm")
    async def test_trend_question(self, mock_get_llm: AsyncMock) -> None:
        from deep_paper_qa.models import RouterOutput

        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = RouterOutput(category=RouteCategory.TREND)
        mock_get_llm.return_value = mock_llm
        result = await classify_question("RAG 近三年的发展趋势")
        assert result == RouteCategory.TREND

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router._get_router_llm")
    async def test_classify_returns_general_on_error(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("LLM error")
        mock_get_llm.return_value = mock_llm
        result = await classify_question("任意问题")
        assert result == RouteCategory.GENERAL
