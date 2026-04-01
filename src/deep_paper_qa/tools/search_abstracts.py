"""search_abstracts 工具：基于 PostgreSQL 全文检索搜索论文标题和摘要"""

import asyncio
import re

from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings
from deep_paper_qa.tools.execute_sql import get_pool

_BASE_SEARCH_SQL = """
SELECT id, title, year, conference, citations,
       ts_rank(fts, query) AS rank,
       ts_headline('english', coalesce(abstract, ''), query,
                   'StartSel=【, StopSel=】, MaxWords=60, MinWords=20') AS snippet
FROM papers,
     to_tsvector('english', coalesce(title, '') || ' ' || coalesce(abstract, '')) AS fts,
     websearch_to_tsquery('english', $1) AS query
WHERE fts @@ query
"""

# 禁止出现在 where 片段中的关键词
_FORBIDDEN_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|SELECT)\b",
    re.IGNORECASE,
)


def _validate_where(where: str) -> str | None:
    """校验 WHERE 片段安全性，返回错误信息或 None 表示通过。"""
    if ";" in where:
        return "WHERE 片段不允许包含分号。"
    if _FORBIDDEN_RE.search(where):
        return f"WHERE 片段包含禁止关键词: {_FORBIDDEN_RE.search(where).group()}"
    return None


@tool
async def search_abstracts(query: str, limit: int = 10, where: str = "") -> str:
    """关键词搜索论文标题和摘要。用于在论文内容中查找特定概念、方法或主题。

    使用 PostgreSQL 全文检索，支持英文 websearch 语法。
    返回匹配论文的标题、年份、会议、引用数和摘要高亮片段。

    查询语法：
    - 默认多词之间是 AND 关系："synthetic data" 匹配同时含两词的论文
    - 用 OR 连接可选词："synthetic data OR data augmentation"
    - 用引号精确匹配短语：'"knowledge distillation"'
    - 用 - 排除词：'RAG -survey'

    重要：保持查询简短（2-4 个核心词），不要堆砌同义词。
    错误示例："data synthesis synthetic data generation NLP natural language processing"
    正确示例："synthetic data OR data augmentation"

    适用场景：
    - 查找涉及某个方法/概念的论文："attention mechanism"
    - 搜索特定技术细节：'"knowledge distillation" BERT'
    - 限定范围搜索：query="diffusion model", where="year=2025 AND conference='ICML'"
    - 高引论文搜索：query="reinforcement learning", where="citations >= 10"

    Args:
        query: 搜索关键词（英文，支持 OR / 引号 / - 语法）
        limit: 返回结果数量，默认 10，最大 20
        where: 可选的 SQL WHERE 条件片段，用于按元数据筛选（年份、会议、引用量等）。
               示例："year=2025 AND conference='ICML'"
               支持 papers 表所有字段，支持 AND/OR/IN/BETWEEN/LIKE/ILIKE/ANY() 等。
               不允许包含分号或子查询。
    """
    limit = min(limit, 20)
    logger.info("search_abstracts 查询: '{}', where='{}', limit={}", query[:200], where[:200], limit)

    # 校验 where 片段
    if where:
        err = _validate_where(where)
        if err:
            logger.warning("search_abstracts WHERE 校验失败: {}", err)
            return f"WHERE 条件不合法: {err}"

    # 拼接 SQL
    sql = _BASE_SEARCH_SQL
    if where:
        sql += f"  AND ({where})\n"
    sql += "ORDER BY rank DESC\nLIMIT $2"

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            records = await asyncio.wait_for(
                conn.fetch(sql, query, limit),
                timeout=settings.sql_timeout_seconds,
            )

        if not records:
            return f"未找到与 '{query}' 相关的论文。可以尝试换用英文关键词或更宽泛的搜索词。"

        lines: list[str] = []
        for i, r in enumerate(records, 1):
            lines.append(f"[{i}] {r['title']}")
            lines.append(f"    ID: {r['id']} | {r['conference']} {r['year']} | 引用: {r['citations']} | 相关度: {r['rank']:.4f}")
            lines.append(f"    摘要片段: {r['snippet']}")
            lines.append("")

        lines.append(f"共找到 {len(records)} 篇相关论文（按相关度排序）。")
        return "\n".join(lines)

    except asyncio.TimeoutError:
        logger.warning("search_abstracts 查询超时: {}", query[:100])
        return "搜索超时，请简化查询关键词后重试。"
    except Exception as e:
        logger.error("search_abstracts 异常: {}", e)
        return f"搜索失败: {e}"
