"""路由分类测试"""

from unittest.mock import AsyncMock, patch

import pytest

from deep_paper_qa.models import RouteCategory
from deep_paper_qa.pipelines.router import classify_question


class TestRouteCategory:
    """路由分类枚举测试"""

    def test_all_categories_exist(self) -> None:
        expected = {"reject", "general", "research", "reading", "compare", "trend"}
        actual = {c.value for c in RouteCategory}
        assert actual == expected


class _FakeAIMessage:
    """模拟 AIMessage，只需要 .content 属性"""

    def __init__(self, content: str) -> None:
        self.content = content


class TestClassifyQuestion:
    """路由分类函数测试"""

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router.get_llm")
    async def test_general_question(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _FakeAIMessage("general")
        mock_get_llm.return_value = mock_llm
        result = await classify_question("2024年NeurIPS收录了多少篇论文？")
        assert result == RouteCategory.GENERAL

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router.get_llm")
    async def test_reject_question(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _FakeAIMessage("reject")
        mock_get_llm.return_value = mock_llm
        result = await classify_question("今天天气怎么样？")
        assert result == RouteCategory.REJECT

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router.get_llm")
    async def test_research_question(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _FakeAIMessage("research")
        mock_get_llm.return_value = mock_llm
        result = await classify_question("总结 2023-2025 年 LLM Agent 的研究脉络")
        assert result == RouteCategory.RESEARCH

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router.get_llm")
    async def test_trend_question(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _FakeAIMessage("trend")
        mock_get_llm.return_value = mock_llm
        result = await classify_question("RAG 近三年的发展趋势")
        assert result == RouteCategory.TREND

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router.get_llm")
    async def test_classify_returns_general_on_error(self, mock_get_llm: AsyncMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = Exception("LLM error")
        mock_get_llm.return_value = mock_llm
        result = await classify_question("任意问题")
        assert result == RouteCategory.GENERAL

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router.get_llm")
    async def test_parse_json_format(self, mock_get_llm: AsyncMock) -> None:
        """LLM 返回 JSON 格式也能正确解析"""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _FakeAIMessage('{"category": "trend"}')
        mock_get_llm.return_value = mock_llm
        result = await classify_question("RAG 趋势")
        assert result == RouteCategory.TREND

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.router.get_llm")
    async def test_parse_with_explanation(self, mock_get_llm: AsyncMock) -> None:
        """LLM 带解释文本也能提取分类"""
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _FakeAIMessage(
            "这是一个需要深入研究的问题，分类为 research"
        )
        mock_get_llm.return_value = mock_llm
        result = await classify_question("调研 LLM Agent")
        assert result == RouteCategory.RESEARCH
