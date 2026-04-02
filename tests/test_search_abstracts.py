"""search_abstracts 工具测试"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deep_paper_qa.tools.search_abstracts import search_abstracts


class _FakeRecord(dict):
    """模拟 asyncpg.Record"""

    def keys(self):
        return list(super().keys())

    def values(self):
        return list(super().values())


class _MockAcquireCtx:
    """模拟 asyncpg pool.acquire() 的异步上下文管理器"""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_mock_pool(records: list[dict]) -> MagicMock:
    """构造 mock asyncpg pool"""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[_FakeRecord(r) for r in records])

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)
    return mock_pool


class TestSearchAbstracts:
    """search_abstracts 集成测试（mock asyncpg）"""

    @pytest.mark.asyncio
    async def test_normal_search(self) -> None:
        """正常全文检索返回结果"""
        records = [
            {
                "id": "acl-2025-long-42",
                "title": "RAG Survey",
                "year": 2025,
                "conference": "ACL",
                "citations": 15,
                "rank": 0.85,
                "snippet": "This paper surveys 【retrieval augmented generation】 methods...",
            }
        ]
        mock_pool = _make_mock_pool(records)

        with patch(
            "deep_paper_qa.tools.search_abstracts.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            result = await search_abstracts.ainvoke({"query": "RAG survey"})
            assert "RAG Survey" in result
            assert "ACL" in result
            assert "retrieval augmented generation" in result

    @pytest.mark.asyncio
    async def test_with_where_condition(self) -> None:
        """带 where 条件的搜索"""
        records = [
            {
                "id": "neurips-2024-1",
                "title": "Attention Paper",
                "year": 2024,
                "conference": "NeurIPS",
                "citations": 5,
                "rank": 0.72,
                "snippet": "We propose 【efficient attention】...",
            }
        ]
        mock_pool = _make_mock_pool(records)

        with patch(
            "deep_paper_qa.tools.search_abstracts.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            result = await search_abstracts.ainvoke(
                {"query": "attention", "where": "year=2024 AND conference='NeurIPS'"}
            )
            assert "Attention Paper" in result

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        """无匹配结果时返回提示"""
        mock_pool = _make_mock_pool([])

        with patch(
            "deep_paper_qa.tools.search_abstracts.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            result = await search_abstracts.ainvoke({"query": "nonexistent topic xyz"})
            assert "未找到" in result

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        """查询超时时返回提示"""
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(side_effect=asyncio.TimeoutError())

        mock_pool = MagicMock()
        mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)

        with patch(
            "deep_paper_qa.tools.search_abstracts.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            result = await search_abstracts.ainvoke({"query": "test"})
            assert "超时" in result
