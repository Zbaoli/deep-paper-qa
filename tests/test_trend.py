"""趋势分析 Pipeline 测试"""

from unittest.mock import AsyncMock, patch

import pytest

from deep_paper_qa.pipelines.trend import generate_sql_node, synthesize_node


class TestGenerateSqlNode:
    """SQL 生成节点测试"""

    @pytest.mark.asyncio
    @patch("deep_paper_qa.pipelines.trend.get_llm")
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
    @patch("deep_paper_qa.pipelines.trend.get_llm")
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
        }
        result = await synthesize_node(state)
        assert "messages" in result
        assert len(result["messages"]) > 0
