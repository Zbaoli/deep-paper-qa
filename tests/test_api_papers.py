"""论文浏览 API 测试"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from deep_paper_qa.api import app


class _FakeRecord(dict):
    """模拟 asyncpg.Record"""

    def keys(self):
        return list(super().keys())

    def values(self):
        return list(super().values())


class _MockAcquireCtx:
    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


def _make_mock_pool(records: list[dict]) -> MagicMock:
    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[_FakeRecord(r) for r in records])
    mock_conn.fetchrow = AsyncMock(return_value=_FakeRecord(records[0]) if records else None)
    mock_pool = MagicMock()
    mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)
    return mock_pool


class TestPapersSearch:
    """GET /api/papers 测试"""

    def test_search_papers(self) -> None:
        records = [
            {
                "id": "acl-2025-1",
                "title": "RAG Survey",
                "year": 2025,
                "conference": "ACL",
                "citations": 10,
                "abstract": "A survey...",
            }
        ]
        mock_pool = _make_mock_pool(records)

        with patch(
            "deep_paper_qa.routers.papers.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            client = TestClient(app)
            resp = client.get("/api/papers?q=RAG")
            assert resp.status_code == 200
            data = resp.json()
            assert "papers" in data
            assert len(data["papers"]) == 1
            assert data["papers"][0]["title"] == "RAG Survey"


class TestPaperDetail:
    """GET /api/papers/{id} 测试"""

    def test_paper_detail(self) -> None:
        record = {
            "id": "acl-2025-1",
            "title": "RAG Survey",
            "abstract": "Full abstract...",
            "year": 2025,
            "conference": "ACL",
            "citations": 10,
            "authors": ["Author A"],
            "url": "https://example.com",
        }
        mock_pool = _make_mock_pool([record])

        with patch(
            "deep_paper_qa.routers.papers.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            client = TestClient(app)
            resp = client.get("/api/papers/acl-2025-1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["title"] == "RAG Survey"

    def test_paper_not_found(self) -> None:
        mock_conn = AsyncMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)

        with patch(
            "deep_paper_qa.routers.papers.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            client = TestClient(app)
            resp = client.get("/api/papers/nonexistent")
            assert resp.status_code == 404
