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
