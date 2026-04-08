"""统计数据 API 测试"""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from deep_paper_qa.api import app


class _FakeRecord(dict):
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


class TestStatsEndpoint:
    """GET /api/stats 测试"""

    def test_stats(self) -> None:
        mock_conn = AsyncMock()
        mock_conn.fetchval = AsyncMock(return_value=81913)
        mock_conn.fetch = AsyncMock(
            side_effect=[
                [
                    _FakeRecord({"year": 2024, "count": 15000}),
                    _FakeRecord({"year": 2025, "count": 18000}),
                ],
                [_FakeRecord({"conference": "NeurIPS", "count": 12000})],
            ]
        )
        mock_pool = MagicMock()
        mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)

        with patch(
            "deep_paper_qa.routers.stats.get_readonly_pool",
            AsyncMock(return_value=mock_pool),
        ):
            client = TestClient(app)
            resp = client.get("/api/stats")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_papers"] == 81913
            assert "by_year" in data
            assert "by_conference" in data
            assert len(data["by_year"]) == 2
            assert data["by_year"][0]["year"] == 2024
