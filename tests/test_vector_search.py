"""vector_search 工具测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from deep_paper_qa.tools.vector_search import _format_chunks, vector_search


class TestFormatChunks:
    """检索结果格式化测试"""

    def test_empty_chunks(self) -> None:
        assert "未找到" in _format_chunks([])

    def test_normal_chunks(self) -> None:
        chunks = [
            {
                "paper_title": "Test Paper",
                "paper_id": "arxiv:2312.00001",
                "content": "This is a test chunk content.",
                "score": 0.95,
            }
        ]
        result = _format_chunks(chunks)
        assert "Test Paper" in result
        assert "arxiv:2312.00001" in result
        assert "0.950" in result


class TestVectorSearch:
    """vector_search 集成测试（mock API）"""

    @pytest.mark.asyncio
    async def test_normal_search(self) -> None:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "chunks": [
                    {
                        "paper_title": "RAG Survey",
                        "paper_id": "arxiv:2312.10997",
                        "content": "Retrieval-augmented generation improves...",
                        "score": 0.92,
                    }
                ]
            }
        )
        mock_response.text = AsyncMock(return_value="")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_paper_qa.tools.vector_search.aiohttp.ClientSession", return_value=mock_session):
            result = await vector_search.ainvoke({"query": "RAG chunking strategies"})
            assert "RAG Survey" in result

    @pytest.mark.asyncio
    async def test_api_unavailable(self) -> None:
        mock_session = AsyncMock()
        mock_session.post = MagicMock(side_effect=aiohttp.ClientError("Connection refused"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_paper_qa.tools.vector_search.aiohttp.ClientSession", return_value=mock_session):
            result = await vector_search.ainvoke({"query": "test query"})
            assert "暂不可用" in result

    @pytest.mark.asyncio
    async def test_empty_results(self) -> None:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"chunks": []})
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("deep_paper_qa.tools.vector_search.aiohttp.ClientSession", return_value=mock_session):
            result = await vector_search.ainvoke({"query": "nonexistent topic"})
            assert "未找到" in result
