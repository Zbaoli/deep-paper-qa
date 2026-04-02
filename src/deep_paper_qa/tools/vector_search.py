"""vector_search 工具：基于 pgvector 的 abstract 语义检索"""

import aiohttp
from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings
from deep_paper_qa.tools.execute_sql import get_readonly_pool
from deep_paper_qa.tools.sql_utils import validate_where


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


@tool
async def vector_search(query: str, top_k: int = 5, where: str = "") -> str:
    """语义检索论文摘要。用于查找与查询语义相关的论文，比关键词搜索更能理解自然语言含义。

    输入自然语言查询，返回语义最相关的论文标题、摘要片段和元数据。
    底层使用向量相似度匹配（余弦距离），适合模糊或概念性的查询。

    适用场景：
    - 概念性问题："如何提升模型在低资源语言上的表现"
    - 方法类比："类似于 LoRA 的参数高效微调方法"
    - 研究趋势："多模态大模型的最新进展"

    Args:
        query: 自然语言检索查询
        top_k: 返回结果数量，默认 5，最大 20
        where: 可选的 SQL WHERE 条件片段，用于按元数据筛选。
               示例："year=2025 AND conference='ICML'"
    """
    top_k = min(top_k, 20)
    logger.info("vector_search 查询: '{}', where='{}', top_k={}", query[:200], where[:200], top_k)

    # 校验 where 片段
    if where:
        err = validate_where(where)
        if err:
            logger.warning("vector_search WHERE 校验失败: {}", err)
            return f"WHERE 条件不合法: {err}"

    try:
        # 获取查询向量
        query_embedding = await _get_embedding(query)
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        # 构建 SQL
        where_clause = "WHERE abstract_embedding IS NOT NULL"
        if where:
            where_clause += f" AND ({where})"

        sql = f"""
            SELECT id, title, year, conference, citations,
                   LEFT(abstract, 800) AS abstract_snippet,
                   1 - (abstract_embedding <=> $1::vector) AS similarity
            FROM papers
            {where_clause}
            ORDER BY abstract_embedding <=> $1::vector
            LIMIT $2
        """

        pool = await get_readonly_pool()
        async with pool.acquire() as conn:
            # 增大 ef_search 确保带 WHERE 过滤时 HNSW 索引有足够候选集
            await conn.execute("SET hnsw.ef_search = 400")
            records = await conn.fetch(sql, embedding_str, top_k)

        if not records:
            return "未找到相关论文。可以尝试使用 search_abstracts 进行关键词搜索。"

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

    except aiohttp.ClientError as e:
        logger.warning("Embedding 服务连接失败: {}", e)
        return "Embedding 服务暂不可用，请改用 search_abstracts 进行关键词搜索。"
    except Exception as e:
        logger.error("vector_search 异常: {}", e)
        return f"语义检索失败: {e}"
