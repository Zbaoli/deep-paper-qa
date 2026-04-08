"""路由节点：LLM 六分类"""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from deep_paper_qa.config import settings
from deep_paper_qa.models import RouteCategory, RouterOutput
from deep_paper_qa.prompts import ROUTER_PROMPT


def _get_router_llm() -> ChatOpenAI:
    """获取路由分类用的 LLM（with_structured_output）"""
    llm = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0,
    )
    return llm.with_structured_output(RouterOutput)


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
        logger.info("路由分类 | question='{}' | category={}", question[:80], result.category.value)
        return result.category
    except Exception as e:
        logger.warning("路由分类异常，回退到 general | error={}", e)
        return RouteCategory.GENERAL
