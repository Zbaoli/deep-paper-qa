"""search_semantic_scholar 工具：搜索 Semantic Scholar 学术论文"""

import asyncio

import aiohttp
from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings

_S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
_S2_FIELDS = "title,abstract,year,citationCount,authors,venue,openAccessPdf,externalIds"


def _format_results(data: dict) -> str:
    """格式化 Semantic Scholar API 响应"""
    papers = data.get("data", [])
    if not papers:
        return "未找到相关论文。"

    lines: list[str] = []
    for i, p in enumerate(papers, 1):
        title = p.get("title", "")
        year = p.get("year", "")
        venue = p.get("venue", "")
        citations = p.get("citationCount", 0)

        # 作者（取前 3）
        authors_raw = p.get("authors", [])
        authors = [a.get("name", "") for a in authors_raw[:3]]
        if len(authors_raw) > 3:
            authors.append(f"等共 {len(authors_raw)} 位作者")
        authors_str = ", ".join(authors)

        # 摘要截断
        abstract = (p.get("abstract") or "").strip().replace("\n", " ")
        if len(abstract) > settings.abstract_max_chars:
            abstract = abstract[: settings.abstract_max_chars] + "..."

        # PDF 链接
        pdf_info = p.get("openAccessPdf") or {}
        pdf_url = pdf_info.get("url", "")

        # arXiv ID
        ext_ids = p.get("externalIds") or {}
        arxiv_id = ext_ids.get("ArXiv", "")

        lines.append(f"[{i}] {title}")
        meta_parts = [f"作者: {authors_str}"]
        if year:
            meta_parts.append(f"年份: {year}")
        if venue:
            meta_parts.append(f"venue: {venue}")
        meta_parts.append(f"引用: {citations}")
        lines.append(f"    {' | '.join(meta_parts)}")
        if abstract:
            lines.append(f"    摘要: {abstract}")
        if pdf_url:
            lines.append(f"    PDF: {pdf_url}")
        elif arxiv_id:
            lines.append(f"    arXiv: {arxiv_id}")
        lines.append("")

    lines.append(f"共找到 {len(papers)} 篇论文（Semantic Scholar）。")
    return "\n".join(lines)


@tool
async def search_semantic_scholar(
    query: str,
    max_results: int = 5,
    fields_of_study: str = "",
    year: str = "",
) -> str:
    """搜索 Semantic Scholar 学术论文数据库。适用于：查询引用数据、跨数据库搜索论文、按领域和年份过滤。

    注意：本地数据库已包含 2020-2025 年主流 AI 会议论文。仅在以下情况使用此工具：
    - 需要引用数据（本地数据库引用数可能不准确或缺失）
    - 需要查找本地数据库未收录的论文
    - 需要跨领域搜索（非 AI 顶会论文）

    Args:
        query: 搜索关键词（英文）
        max_results: 最多返回条数，默认 5，最大 10
        fields_of_study: 领域过滤，如 "Computer Science"。留空不过滤。
        year: 年份过滤，如 "2024-2026" 或 "2025"。留空不过滤。
    """
    max_results = min(max_results, 10)
    logger.info(
        "search_semantic_scholar 查询: '{}', fields='{}', year='{}', max={}",
        query[:200],
        fields_of_study,
        year,
        max_results,
    )

    params: dict[str, str] = {
        "query": query,
        "limit": str(max_results),
        "fields": _S2_FIELDS,
    }
    if fields_of_study:
        params["fieldsOfStudy"] = fields_of_study
    if year:
        params["year"] = year

    headers: dict[str, str] = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key

    try:
        timeout = aiohttp.ClientTimeout(total=settings.external_search_timeout)
        async with aiohttp.ClientSession() as session:
            resp = await session.get(_S2_API, params=params, headers=headers, timeout=timeout)
            if resp.status == 429:
                logger.warning("Semantic Scholar API 限频 (429)")
                return "Semantic Scholar API 请求限频 (429)，请稍后重试。"
            if resp.status != 200:
                logger.warning("Semantic Scholar API 返回错误: status={}", resp.status)
                return f"Semantic Scholar API 返回错误 ({resp.status})，请稍后重试。"
            data = await resp.json()

        result = _format_results(data)
        logger.info("search_semantic_scholar 返回 {} 条结果", len(data.get("data", [])))
        return result
    except asyncio.TimeoutError:
        logger.warning("search_semantic_scholar 查询超时: {}", query[:100])
        return "Semantic Scholar 搜索超时，请稍后重试或使用本地数据库查询。"
    except aiohttp.ClientError as e:
        logger.warning("search_semantic_scholar 网络错误: {}", e)
        return "Semantic Scholar 服务暂不可用，请使用本地数据库查询。"
