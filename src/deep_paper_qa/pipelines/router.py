"""路由节点：LLM 六分类"""

import re

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from deep_paper_qa.config import get_llm
from deep_paper_qa.models import RouteCategory
from deep_paper_qa.prompts import ROUTER_PROMPT

# 有效分类值集合
_VALID_CATEGORIES = {c.value for c in RouteCategory}


def _parse_category(text: str) -> RouteCategory | None:
    """从 LLM 文本响应中解析分类结果"""
    text = text.strip().lower()

    if text in _VALID_CATEGORIES:
        return RouteCategory(text)

    json_match = re.search(r'"category"\s*:\s*"(\w+)"', text)
    if json_match and json_match.group(1) in _VALID_CATEGORIES:
        return RouteCategory(json_match.group(1))

    found = None
    for cat in _VALID_CATEGORIES:
        if cat in text:
            found = cat
    if found:
        return RouteCategory(found)

    return None


async def classify_question(question: str) -> RouteCategory:
    """对用户问题进行六分类"""
    try:
        llm = get_llm()
        result = await llm.ainvoke(
            [
                SystemMessage(content=ROUTER_PROMPT),
                HumanMessage(content=question),
            ]
        )
        category = _parse_category(result.content)
        if category is None:
            logger.warning("路由分类解析失败，回退到 general | raw='{}'", result.content[:100])
            return RouteCategory.GENERAL

        logger.info("路由分类 | question='{}' | category={}", question[:80], category.value)
        return category
    except Exception as e:
        logger.warning("路由分类异常，回退到 general | error={}", e)
        return RouteCategory.GENERAL
