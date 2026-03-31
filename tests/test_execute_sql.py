"""execute_sql 工具测试"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from deep_paper_qa.tools.execute_sql import _format_results, execute_sql, validate_sql


class _FakeRecord(dict):
    """模拟 asyncpg.Record"""

    def keys(self):
        return list(super().keys())

    def values(self):
        return list(super().values())

    def items(self):
        return list(super().items())


class TestValidateSql:
    """SQL 校验测试"""

    def test_valid_select(self) -> None:
        assert validate_sql("SELECT * FROM papers") is None

    def test_valid_select_with_whitespace(self) -> None:
        assert validate_sql("  SELECT count(*) FROM papers") is None

    def test_reject_insert(self) -> None:
        result = validate_sql("INSERT INTO papers VALUES ('x', 'y', 2025)")
        assert result is not None
        assert "只允许" in result

    def test_reject_delete(self) -> None:
        result = validate_sql("DELETE FROM papers WHERE id='x'")
        assert result is not None

    def test_reject_drop_in_select(self) -> None:
        result = validate_sql("SELECT * FROM papers; DROP TABLE papers")
        assert result is not None
        assert "禁止" in result


class TestFormatResults:
    """结果格式化测试"""

    def test_empty_results(self) -> None:
        result = _format_results([])
        assert "未找到" in result

    def test_single_count(self) -> None:
        record = _FakeRecord(count=42)
        result = _format_results([record])
        assert "42" in result

    def test_multiple_rows(self) -> None:
        records = [
            _FakeRecord(title="Paper A", year=2025),
            _FakeRecord(title="Paper B", year=2024),
        ]
        result = _format_results(records)
        assert "Paper A" in result
        assert "Paper B" in result


class _MockAcquireCtx:
    """模拟 asyncpg pool.acquire() 的异步上下文管理器"""

    def __init__(self, conn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, *args):
        pass


class TestExecuteSql:
    """execute_sql 集成测试（mock 数据库）"""

    @pytest.mark.asyncio
    async def test_reject_non_select(self) -> None:
        result = await execute_sql.ainvoke({"sql": "DROP TABLE papers"})
        assert "只允许" in result

    @pytest.mark.asyncio
    async def test_valid_query_with_mock(self) -> None:
        mock_record = _FakeRecord(title="Test Paper", year=2025)

        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[mock_record])

        mock_pool = MagicMock()
        mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)

        with patch("deep_paper_qa.tools.execute_sql.get_pool", AsyncMock(return_value=mock_pool)):
            result = await execute_sql.ainvoke({"sql": "SELECT title, year FROM papers LIMIT 5"})
            assert "Test Paper" in result

    @pytest.mark.asyncio
    async def test_empty_result(self) -> None:
        mock_conn = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        mock_pool = MagicMock()
        mock_pool.acquire.return_value = _MockAcquireCtx(mock_conn)

        with patch("deep_paper_qa.tools.execute_sql.get_pool", AsyncMock(return_value=mock_pool)):
            result = await execute_sql.ainvoke(
                {"sql": "SELECT * FROM papers WHERE year=9999"}
            )
            assert "未找到" in result

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        with patch(
            "deep_paper_qa.tools.execute_sql.get_pool",
            AsyncMock(side_effect=asyncio.TimeoutError()),
        ), patch(
            "asyncio.wait_for",
            AsyncMock(side_effect=asyncio.TimeoutError()),
        ):
            result = await execute_sql.ainvoke({"sql": "SELECT * FROM papers"})
            assert "超时" in result or "失败" in result
