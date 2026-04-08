"""search_abstracts 工具：论文内容检索（全文检索 + 向量语义检索）"""

import asyncio
from typing import Literal

import aiohttp
from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings
from deep_paper_qa.tools.execute_sql import get_readonly_pool
from deep_paper_qa.tools.sql_utils import validate_where

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


async def _get_embedding(text: str) -> list[float]:
    """调用 Embedding 服务获取向量"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{settings.embedding_base_url}/embeddings",
            json={"model": settings.embedding_model, "input": text},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data["data"][0]["embedding"]


async def _fulltext_search(query: str, limit: int, where: str) -> str:
    """全文检索模式"""
    sql = _BASE_SEARCH_SQL
    if where:
        sql += f"  AND ({where})\n"
    sql += "ORDER BY rank DESC\nLIMIT $2"

    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        records = await asyncio.wait_for(
            conn.fetch(sql, query, limit),
            timeout=settings.sql_timeout_seconds,
        )

    if not records:
        return f"未找到与 '{query}' 相关的论文。可尝试换用英文关键词、更宽泛的搜索词，或切换到 mode='vector' 进行语义检索。"

    lines: list[str] = []
    for i, r in enumerate(records, 1):
        lines.append(f"[{i}] {r['title']}")
        lines.append(
            f"    ID: {r['id']} | {r['conference']} {r['year']} "
            f"| 引用: {r['citations']} | 相关度: {r['rank']:.4f}"
        )
        lines.append(f"    摘要片段: {r['snippet']}")
        lines.append("")

    lines.append(f"共找到 {len(records)} 篇相关论文（按相关度排序）。")
    return "\n".join(lines)


async def _vector_search(query: str, limit: int, where: str) -> str:
    """向量语义检索模式"""
    try:
        query_embedding = await _get_embedding(query)
    except aiohttp.ClientError as e:
        logger.warning("Embedding 服务连接失败: {}", e)
        return "Embedding 服务暂不可用，请改用 mode='fulltext' 进行关键词搜索。"

    embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

    where_clause = "WHERE abstract_embedding IS NOT NULL"
    if where:
        where_clause += f" AND ({where})"

    sql = f"""
        SELECT id, title, year, conference, citations,
               LEFT(abstract, {settings.abstract_max_chars}) AS abstract_snippet,
               1 - (abstract_embedding <=> $1::vector) AS similarity
        FROM papers
        {where_clause}
        ORDER BY abstract_embedding <=> $1::vector
        LIMIT $2
    """

    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        await conn.execute("SET hnsw.ef_search = 400")
        records = await conn.fetch(sql, embedding_str, limit)

    if not records:
        return "未找到相关论文。可尝试换用 mode='fulltext' 进行关键词搜索。"

    lines: list[str] = []
    for i, r in enumerate(records, 1):
        lines.append(f"[{i}] {r['title']}")
        lines.append(
            f"    ID: {r['id']} | {r['conference']} {r['year']} "
            f"| 引用: {r['citations']} | 相似度: {r['similarity']:.4f}"
        )
        snippet = (r["abstract_snippet"] or "").replace("\n", " ")
        if snippet:
            lines.append(f"    摘要: {snippet}")
        lines.append("")

    lines.append(f"共找到 {len(records)} 篇语义相关论文（按相似度排序）。")
    return "\n".join(lines)


@tool
async def search_abstracts(
    query: str,
    mode: Literal["fulltext", "vector"] = "fulltext",
    limit: int = 10,
    where: str = "",
) -> str:
    """搜索论文标题和摘要内容。支持两种检索模式。

    注意：此工具只搜索论文的标题和摘要正文，不搜索作者、会议等元数据字段。
    按作者查论文请用 execute_sql + ANY(authors)。

    两种模式：
    - mode="fulltext"（默认）：关键词全文检索，适合精确术语搜索，返回高亮摘要片段
    - mode="vector"：语义向量检索，适合模糊/概念性查询，返回完整摘要片段

    使用策略：优先用 fulltext 模式。如果 fulltext 返回结果不相关或为空，再用 vector 模式补充。

    fulltext 查询语法：
    - 默认多词之间是 AND 关系
    - 用 OR 连接可选词："synthetic data OR data augmentation"
    - 用引号精确匹配短语：'"knowledge distillation"'
    - 用 - 排除词：'RAG -survey'

    适用场景：
    - 查找涉及某个方法/概念的论文："attention mechanism"
    - 搜索特定技术细节：'"knowledge distillation" BERT'
    - 模糊/概念性搜索（用 vector 模式）："如何提升低资源语言的模型表现"

    Args:
        query: 搜索查询（fulltext 模式用英文关键词，vector 模式用自然语言描述）
        mode: 检索模式，"fulltext"（关键词）或 "vector"（语义）
        limit: 返回结果数量，默认 10，最大 20
        where: 可选的 SQL WHERE 条件片段，用于按元数据筛选（年份、会议、引用量等）。
               示例："year=2025 AND conference='ICML'"、"citations >= 10"
               不允许包含分号或子查询。
    """
    limit = min(limit, 20)
    logger.info(
        "search_abstracts [{}] 查询: '{}', where='{}', limit={}",
        mode,
        query[:200],
        where[:200],
        limit,
    )

    # 校验 where 片段
    if where:
        err = validate_where(where)
        if err:
            logger.warning("search_abstracts WHERE 校验失败: {}", err)
            return f"WHERE 条件不合法: {err}"

    try:
        if mode == "vector":
            return await _vector_search(query, limit, where)
        else:
            return await _fulltext_search(query, limit, where)
    except asyncio.TimeoutError:
        logger.warning("search_abstracts 查询超时: {}", query[:100])
        return "搜索超时，请简化查询关键词后重试。"
    except Exception as e:
        logger.error("search_abstracts [{}] 异常: {}", mode, e)
        return f"搜索失败: {e}"
