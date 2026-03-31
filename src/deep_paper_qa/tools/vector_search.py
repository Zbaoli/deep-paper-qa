"""vector_search 工具：调用 RAG 项目 API 进行语义检索"""

import aiohttp
from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings


def _truncate_chunk(text: str) -> str:
    """截断文档片段到最大长度"""
    if len(text) > settings.vector_chunk_max_chars:
        return text[: settings.vector_chunk_max_chars] + "..."
    return text


def _format_chunks(chunks: list[dict]) -> str:
    """格式化检索结果为可读字符串"""
    if not chunks:
        return "未找到相关论文内容。"

    lines: list[str] = []
    for i, chunk in enumerate(chunks[: settings.vector_search_top_k], 1):
        title = chunk.get("paper_title", chunk.get("title", "未知论文"))
        paper_id = chunk.get("paper_id", chunk.get("id", ""))
        content = _truncate_chunk(chunk.get("content", chunk.get("text", "")))
        score = chunk.get("score", 0)

        lines.append(f"[{i}] {title} ({paper_id})")
        if score:
            lines.append(f"    相关度: {score:.3f}")
        lines.append(f"    {content}")
        lines.append("")

    return "\n".join(lines)


@tool
async def vector_search(query: str) -> str:
    """语义检索论文内容。用于回答关于论文方法、实验、结论等内容级问题。

    输入自然语言查询，返回最相关的论文段落。

    Args:
        query: 自然语言检索查询
    """
    logger.info("vector_search 查询: {}", query[:200])

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                settings.rag_api_url,
                json={"query": query, "top_k": settings.vector_search_top_k},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.warning("RAG API 返回错误 {}: {}", resp.status, error_text[:200])
                    return f"内容检索服务返回错误（HTTP {resp.status}），请稍后重试。"

                data = await resp.json()

        # 兼容不同的 API 响应格式
        chunks = data.get("chunks", data.get("results", data.get("data", [])))
        result = _format_chunks(chunks)
        logger.info("vector_search 返回 {} 个片段", len(chunks))
        return result

    except aiohttp.ClientError as e:
        logger.warning("RAG API 连接失败: {}", e)
        return "内容检索服务暂不可用，请稍后重试。可以尝试使用 SQL 查询获取论文基本信息。"
    except Exception as e:
        logger.error("vector_search 异常: {}", e)
        return f"内容检索失败: {e}"
