"""execute_sql 工具：Text-to-SQL 查询 PostgreSQL 论文元数据"""

import asyncio
import re
from typing import Any

import asyncpg
from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings

# 模块级连接池
_pool: asyncpg.Pool | None = None
_readonly_pool: asyncpg.Pool | None = None

# 只允许 SELECT / WITH ... SELECT 语句的正则
_SELECT_PATTERN = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)
_FORBIDDEN_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


async def get_pool() -> asyncpg.Pool:
    """获取或创建连接池（读写）"""
    global _pool
    if _pool is None or _pool._closed:
        _pool = await asyncpg.create_pool(settings.pg_database_url, min_size=1, max_size=5)
        logger.info("asyncpg 读写连接池已创建")
    return _pool


async def get_readonly_pool() -> asyncpg.Pool:
    """获取或创建只读连接池（用于 search_abstracts/vector_search 安全隔离）。
    如果未配置 pg_readonly_url，回退到普通连接池。
    """
    global _readonly_pool
    if not settings.pg_readonly_url:
        return await get_pool()
    if _readonly_pool is None or _readonly_pool._closed:
        _readonly_pool = await asyncpg.create_pool(settings.pg_readonly_url, min_size=1, max_size=5)
        logger.info("asyncpg 只读连接池已创建")
    return _readonly_pool


def validate_sql(sql: str) -> str | None:
    """校验 SQL 语句，返回错误消息或 None（通过）"""
    if not _SELECT_PATTERN.match(sql):
        return "只允许 SELECT 查询操作，禁止执行其他 SQL 语句。"
    if _FORBIDDEN_PATTERN.search(sql):
        return "检测到禁止的 SQL 操作（INSERT/UPDATE/DELETE/DROP 等），已拒绝执行。"
    return None


def _truncate_abstract(row: dict[str, Any]) -> dict[str, Any]:
    """截断 abstract 字段"""
    if "abstract" in row and row["abstract"] and len(row["abstract"]) > settings.abstract_max_chars:
        row["abstract"] = row["abstract"][: settings.abstract_max_chars] + "..."
    return row


def _format_results(records: list[asyncpg.Record]) -> str:
    """将查询结果格式化为可读字符串"""
    if not records:
        return "查询成功，但未找到匹配结果。"

    rows = [_truncate_abstract(dict(r)) for r in records[: settings.sql_max_rows]]
    # 简洁的表格格式
    if len(rows) == 1 and len(rows[0]) == 1:
        # 单值结果（如 COUNT(*)）
        return str(list(rows[0].values())[0])

    lines: list[str] = []
    headers = list(rows[0].keys())
    lines.append(" | ".join(headers))
    lines.append("-" * len(lines[0]))
    for row in rows:
        lines.append(" | ".join(str(v) for v in row.values()))

    total = len(records)
    if total > settings.sql_max_rows:
        lines.append(f"\n（共 {total} 条结果，仅显示前 {settings.sql_max_rows} 条）")

    return "\n".join(lines)


@tool
async def execute_sql(sql: str) -> str:
    """执行 SQL 查询 PostgreSQL 论文元数据数据库。

    只允许 SELECT 查询。数据库包含 papers 表，字段：
    id(TEXT), title(TEXT), abstract(TEXT), year(INT, 2020-2025),
    conference(TEXT, 枚举: ACL/EMNLP/NeurIPS/ICLR/ICML/AAAI/IJCAI/KDD/NAACL/WWW),
    venue_type(TEXT, 枚举: conference/journal/preprint),
    authors(TEXT[], 用 ANY() 查询), citations(INT, 默认 0),
    url(TEXT), pdf_url(TEXT), created_at(TIMESTAMPTZ)。

    示例：
    - 查作者：SELECT title FROM papers WHERE 'Hinton' = ANY(authors)
    - 全文检索+统计：SELECT year, COUNT(*) FROM papers
      WHERE to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))
      @@ to_tsquery('english', 'attention <-> mechanism') GROUP BY year ORDER BY year

    Args:
        sql: 要执行的 SELECT SQL 语句
    """
    logger.info("execute_sql 收到查询: {}", sql[:200])

    # 校验
    error = validate_sql(sql)
    if error:
        logger.warning("SQL 校验失败: {}", error)
        return error

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            records = await asyncio.wait_for(
                conn.fetch(sql),
                timeout=settings.sql_timeout_seconds,
            )
        result = _format_results(records)
        logger.info("execute_sql 返回 {} 条记录", len(records))
        return result
    except asyncio.TimeoutError:
        logger.warning("SQL 查询超时: {}", sql[:100])
        return "查询超时，请简化查询条件后重试。"
    except asyncpg.PostgresSyntaxError as e:
        logger.warning("SQL 语法错误: {}", e)
        return f"SQL 语法错误: {e}。请检查 SQL 语法后重试。"
    except asyncpg.UndefinedColumnError as e:
        logger.warning("SQL 列名错误: {}", e)
        available_cols = (
            "id, title, abstract, year, conference, venue_type, "
            "authors, citations, url, pdf_url, created_at"
        )
        return f"列名错误: {e}。可用列名: {available_cols}"
    except Exception as e:
        logger.error("execute_sql 执行异常: {}", e)
        return f"查询执行失败: {e}。请检查 SQL 语句后重试。"
