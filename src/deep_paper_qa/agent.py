"""DeepAgent 构建：主 agent + search subagent"""

from deepagents import CompiledSubAgent, create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger

from deep_paper_qa.config import get_llm, get_search_agent_llm
from deep_paper_qa.prompts import SEARCH_AGENT_PROMPT, SYSTEM_PROMPT
from deep_paper_qa.tools.ask_user import ask_user
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.generate_chart import generate_chart
from deep_paper_qa.tools.search_abstracts import search_abstracts
from deep_paper_qa.tools.search_arxiv import search_arxiv
from deep_paper_qa.tools.search_semantic_scholar import search_semantic_scholar
from deep_paper_qa.tools.search_web import search_web

# 搜索工具（由 search subagent 独占）
SEARCH_TOOLS = [
    search_abstracts,
    search_arxiv,
    search_semantic_scholar,
    search_web,
]

# 主 agent 直接使用的工具
MAIN_TOOLS = [
    execute_sql,
    ask_user,
    generate_chart,
]

# eval 用的主 agent 工具（排除 ask_user）
EVAL_MAIN_TOOLS = [t for t in MAIN_TOOLS if t.name != "ask_user"]


def _build_search_subagent():
    """构建 Search SubAgent：独立 LLM + 4 个搜索工具"""
    search_llm = get_search_agent_llm(temperature=0.3)
    search_graph = create_deep_agent(
        model=search_llm,
        tools=SEARCH_TOOLS,
        system_prompt=SEARCH_AGENT_PROMPT,
        name="search-agent",
    )
    return CompiledSubAgent(
        name="search-agent",
        description=(
            "对抽象的研究问题进行 query 重写、分解，"
            "调用多种搜索工具检索论文和信息，返回综合研究摘要。"
            "当需要搜索论文内容、查找相关工作、了解研究领域时委派给它。"
        ),
        runnable=search_graph,
    )


def build_graph(*, include_ask_user: bool = True):
    """build_agent 的别名，供 API 路由使用"""
    return build_agent(include_ask_user=include_ask_user)


def build_agent(*, include_ask_user: bool = True):
    """构建 DeepAgent 并返回 (agent, checkpointer)

    Args:
        include_ask_user: 是否包含 ask_user 工具。eval 时设为 False。
    """
    checkpointer = InMemorySaver()
    tools = MAIN_TOOLS if include_ask_user else EVAL_MAIN_TOOLS
    search_subagent = _build_search_subagent()

    agent = create_deep_agent(
        model=get_llm(temperature=0.7),
        tools=tools,
        subagents=[search_subagent],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
        name="paper-qa",
    )

    tool_names = [t.name for t in tools]
    logger.info(
        "DeepAgent 构建完成 | tools={} | subagents=[search-agent]",
        tool_names,
    )
    return agent, checkpointer
