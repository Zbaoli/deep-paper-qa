"""search_arxiv 工具：搜索 arXiv 预印本论文"""

import asyncio
import xml.etree.ElementTree as ET
from urllib.parse import quote

import aiohttp
from langchain_core.tools import tool
from loguru import logger

from deep_paper_qa.config import settings

_ARXIV_API = "http://export.arxiv.org/api/query"
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def _parse_entries(xml_text: str) -> list[dict]:
    """解析 arXiv Atom XML 返回条目列表"""
    root = ET.fromstring(xml_text)
    entries = []
    for entry in root.findall("atom:entry", _NS):
        # 标题
        title_el = entry.find("atom:title", _NS)
        title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""

        # 作者（取前 3）
        authors_els = entry.findall("atom:author/atom:name", _NS)
        authors = [a.text.strip() for a in authors_els[:3] if a.text]
        if len(authors_els) > 3:
            authors.append(f"等共 {len(authors_els)} 位作者")

        # 摘要
        summary_el = entry.find("atom:summary", _NS)
        abstract = (
            (summary_el.text or "").strip().replace("\n", " ") if summary_el is not None else ""
        )
        if len(abstract) > settings.abstract_max_chars:
            abstract = abstract[: settings.abstract_max_chars] + "..."

        # 发布年份
        published_el = entry.find("atom:published", _NS)
        year = (published_el.text or "")[:4] if published_el is not None else ""

        # 分类
        cat_el = entry.find("arxiv:primary_category", _NS)
        category = cat_el.get("term", "") if cat_el is not None else ""

        # 链接
        arxiv_url = ""
        pdf_url = ""
        for link in entry.findall("atom:link", _NS):
            if link.get("title") == "pdf":
                pdf_url = link.get("href", "")
            elif link.get("rel") == "alternate":
                arxiv_url = link.get("href", "")

        entries.append(
            {
                "title": title,
                "authors": authors,
                "year": year,
                "category": category,
                "abstract": abstract,
                "url": arxiv_url,
                "pdf_url": pdf_url,
            }
        )
    return entries


def _format_results(entries: list[dict]) -> str:
    """格式化结果为可读字符串"""
    if not entries:
        return "未找到相关 arXiv 论文。可尝试换用英文关键词或更宽泛的搜索词。"

    lines: list[str] = []
    for i, e in enumerate(entries, 1):
        authors_str = ", ".join(e["authors"])
        lines.append(f"[{i}] {e['title']}")
        lines.append(f"    作者: {authors_str} | 年份: {e['year']} | 分类: {e['category']}")
        if e["abstract"]:
            lines.append(f"    摘要: {e['abstract']}")
        lines.append(f"    链接: {e['url']}")
        lines.append("")

    lines.append(f"共找到 {len(entries)} 篇 arXiv 论文。")
    return "\n".join(lines)


@tool
async def search_arxiv(
    query: str,
    max_results: int = 5,
    category: str = "",
) -> str:
    """搜索 arXiv 预印本论文。适用于：查找最新预印本、数据库未收录的论文、特定 arXiv 分类下的论文。

    注意：本地数据库已包含 2020-2025 年主流 AI 会议论文。仅在以下情况使用此工具：
    - 需要查找最新预印本（尚未被会议收录）
    - 需要查找本地数据库未收录的会议/领域的论文
    - 用户明确要求搜索 arXiv

    Args:
        query: 搜索关键词（英文）
        max_results: 最多返回条数，默认 5，最大 10
        category: arXiv 分类过滤，如 "cs.CL"、"cs.AI"、"cs.LG"。留空不过滤。
    """
    max_results = min(max_results, 10)
    logger.info(
        "search_arxiv 查询: '{}', category='{}', max_results={}",
        query[:200],
        category,
        max_results,
    )

    search_query = f"all:{quote(query)}"
    if category:
        search_query += f"+AND+cat:{category}"

    url = (
        f"{_ARXIV_API}?search_query={search_query}"
        f"&sortBy=relevance&sortOrder=descending&max_results={max_results}"
    )

    try:
        timeout = aiohttp.ClientTimeout(total=settings.external_search_timeout)
        async with aiohttp.ClientSession() as session:
            resp = await session.get(url, timeout=timeout)
            if resp.status != 200:
                logger.warning("arXiv API 返回错误: status={}", resp.status)
                return f"arXiv API 返回错误 ({resp.status})，请稍后重试。"
            xml_text = await resp.text()

        entries = _parse_entries(xml_text)
        result = _format_results(entries)
        logger.info("search_arxiv 返回 {} 条结果", len(entries))
        return result
    except asyncio.TimeoutError:
        logger.warning("search_arxiv 查询超时: {}", query[:100])
        return "arXiv 搜索超时，请稍后重试或使用本地数据库查询。"
    except aiohttp.ClientError as e:
        logger.warning("search_arxiv 网络错误: {}", e)
        return "arXiv 服务暂不可用，请使用本地数据库查询。"
    except ET.ParseError as e:
        logger.error("search_arxiv XML 解析失败: {}", e)
        return "arXiv 返回数据解析失败，请稍后重试。"
