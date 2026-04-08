"""路由节点：LLM 六分类"""

import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from deep_paper_qa.config import settings
from deep_paper_qa.models import RouteCategory
from deep_paper_qa.prompts import ROUTER_PROMPT

# 有效分类值集合
_VALID_CATEGORIES = {c.value for c in RouteCategory}


def _get_router_llm() -> ChatOpenAI:
    """获取路由分类用的 LLM"""
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0,
    )


def _parse_category(text: str) -> RouteCategory | None:
    """从 LLM 文本响应中解析分类结果

    支持多种输出格式：
    - 纯分类词: "research"
    - JSON: {"category": "research"}
    - 带解释: "这是一个研究类问题，分类为 research"
    """
    text = text.strip().lower()

    # 直接匹配
    if text in _VALID_CATEGORIES:
        return RouteCategory(text)

    # 从 JSON 中提取
    json_match = re.search(r'"category"\s*:\s*"(\w+)"', text)
    if json_match and json_match.group(1) in _VALID_CATEGORIES:
        return RouteCategory(json_match.group(1))

    # 从文本中提取最后出现的有效分类词
    found = None
    for cat in _VALID_CATEGORIES:
        if cat in text:
            found = cat
    if found:
        return RouteCategory(found)

    return None


async def classify_question(question: str) -> RouteCategory:
    """对用户问题进行六分类

    Args:
        question: 用户输入的问题文本

    Returns:
        RouteCategory 枚举值
    """
    try:
        llm = _get_router_llm()
        result = await llm.ainvoke(
            [
                SystemMessage(content=ROUTER_PROMPT),
                HumanMessage(content=question),
            ]
        )
        category = _parse_category(result.content)
        if category is None:
            logger.warning(
                "路由分类解析失败，回退到 general | raw='{}'", result.content[:100]
            )
            return RouteCategory.GENERAL

        logger.info(
            "路由分类 | question='{}' | category={}", question[:80], category.value
        )
        return category
    except Exception as e:
        logger.warning("路由分类异常，回退到 general | error={}", e)
        return RouteCategory.GENERAL
