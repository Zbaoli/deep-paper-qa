"""vector_search 工具测试（pgvector 实现）"""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from deep_paper_qa.tools.vector_search import vector_search


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
    """构造 mock asyncpg pool，返回指定记录"""
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[_FakeRecord(r) for r in records])
    mock_conn.execute = AsyncMock()

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)
    return mock_pool


def _make_mock_embedding(dim: int = 1024) -> list[float]:
    """构造 mock embedding 向量"""
    return [0.1] * dim


class TestVectorSearch:
    """vector_search 集成测试（mock asyncpg + aiohttp）"""

    @pytest.mark.asyncio
    async def test_normal_search(self) -> None:
        """正常 pgvector 搜索返回结果"""
        records = [
            {
                "id": "acl-2025-long-1",
                "title": "RAG Survey",
                "year": 2025,
                "conference": "ACL",
                "citations": 10,
                "abstract_snippet": "Retrieval-augmented generation improves...",
                "similarity": 0.92,
            }
        ]
        mock_pool = _make_mock_pool(records)

        mock_embedding_resp = AsyncMock()
        mock_embedding_resp.raise_for_status = MagicMock()
        mock_embedding_resp.json = AsyncMock(
            return_value={"data": [{"embedding": _make_mock_embedding()}]}
        )
        mock_embedding_resp.__aenter__ = AsyncMock(return_value=mock_embedding_resp)
        mock_embedding_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_embedding_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("deep_paper_qa.tools.vector_search.get_readonly_pool", AsyncMock(return_value=mock_pool)),
            patch("deep_paper_qa.tools.vector_search.aiohttp.ClientSession", return_value=mock_session),
        ):
            result = await vector_search.ainvoke({"query": "RAG chunking strategies"})
            assert "RAG Survey" in result
            assert "0.92" in result

    @pytest.mark.asyncio
    async def test_embedding_service_unavailable(self) -> None:
        """Embedding 服务不可用时返回降级提示"""
        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Connection refused"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_paper_qa.tools.vector_search.aiohttp.ClientSession", return_value=mock_session):
            result = await vector_search.ainvoke({"query": "test query"})
            assert "暂不可用" in result

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        """无匹配结果时返回提示"""
        mock_pool = _make_mock_pool([])

        mock_embedding_resp = AsyncMock()
        mock_embedding_resp.raise_for_status = MagicMock()
        mock_embedding_resp.json = AsyncMock(
            return_value={"data": [{"embedding": _make_mock_embedding()}]}
        )
        mock_embedding_resp.__aenter__ = AsyncMock(return_value=mock_embedding_resp)
        mock_embedding_resp.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_embedding_resp)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("deep_paper_qa.tools.vector_search.get_readonly_pool", AsyncMock(return_value=mock_pool)),
            patch("deep_paper_qa.tools.vector_search.aiohttp.ClientSession", return_value=mock_session),
        ):
            result = await vector_search.ainvoke({"query": "nonexistent topic"})
            assert "未找到" in result
