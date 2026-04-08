"""search_web 工具：Tavily 通用网络搜索"""

import asyncio

import aiohttp
from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings

_TAVILY_API = "https://api.tavily.com/search"


def _format_results(data: dict) -> str:
    """格式化 Tavily 搜索结果"""
    results = data.get("results", [])
    if not results:
        return "未找到相关网页结果。"

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "").strip().replace("\n", " ")
        score = r.get("score", 0)

        if len(content) > 500:
            content = content[:500] + "..."

        lines.append(f"[{i}] {title}")
        lines.append(f"    链接: {url}")
        lines.append(f"    摘要: {content}")
        lines.append(f"    相关度: {score:.2f}")
        lines.append("")

    lines.append(f"共找到 {len(results)} 条网页结果。")
    return "\n".join(lines)


@tool
async def search_web(
    query: str,
    max_results: int = 5,
) -> str:
    """搜索互联网获取最新信息。适用于：查找非论文信息，如会议日期、行业动态、开源项目、博客文章、教程等。

    注意：此工具搜索整个互联网，不限于学术论文。仅在以下情况使用此工具：
    - 需要非学术信息（会议截止日期、行业新闻、产品发布等）
    - 需要查找开源项目、GitHub 仓库、技术博客
    - 其他学术搜索工具无法回答的问题

    Args:
        query: 搜索关键词
        max_results: 最多返回条数，默认 5，最大 10
    """
    max_results = min(max_results, 10)
    logger.info("search_web 查询: '{}', max_results={}", query[:200], max_results)

    if not settings.tavily_api_key:
        return "Tavily API key 未配置，无法进行网络搜索。请在 .env 中设置 TAVILY_API_KEY。"

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }

    try:
        timeout = aiohttp.ClientTimeout(total=settings.external_search_timeout)
        async with aiohttp.ClientSession() as session:
            resp = await session.post(_TAVILY_API, json=payload, timeout=timeout)
            if resp.status != 200:
                logger.warning("Tavily API 返回错误: status={}", resp.status)
                return f"Tavily API 返回错误 ({resp.status})，请稍后重试。"
            data = await resp.json()

        result = _format_results(data)
        logger.info("search_web 返回 {} 条结果", len(data.get("results", [])))
        return result
    except asyncio.TimeoutError:
        logger.warning("search_web 查询超时: {}", query[:100])
        return "网络搜索超时，请稍后重试。"
    except aiohttp.ClientError as e:
        logger.warning("search_web 网络错误: {}", e)
        return "网络搜索服务暂不可用，请稍后重试。"
