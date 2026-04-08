"""DeepAgent 构建：单一 agent + 7 工具 + 领域知识 prompt"""

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from loguru import logger

from deep_paper_qa.config import get_llm
from deep_paper_qa.prompts import SYSTEM_PROMPT
from deep_paper_qa.tools.ask_user import ask_user
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.generate_chart import generate_chart
from deep_paper_qa.tools.search_abstracts import search_abstracts
from deep_paper_qa.tools.search_arxiv import search_arxiv
from deep_paper_qa.tools.search_semantic_scholar import search_semantic_scholar
from deep_paper_qa.tools.search_web import search_web

# 路由分类标签（category → 中文说明）
CATEGORY_LABELS: dict[str, str] = {
    "sql": "元数据统计（SQL）",
    "fulltext": "全文检索",
    "vector": "语义检索",
    "deep_research": "深度研究",
    "general": "通用回答",
}

# 全部工具
ALL_TOOLS = [
    execute_sql,
    search_abstracts,
    search_arxiv,
    search_semantic_scholar,
    search_web,
    ask_user,
    generate_chart,
]

# eval 用的工具列表（排除 ask_user，避免 eval 时阻塞）
EVAL_TOOLS = [t for t in ALL_TOOLS if t.name != "ask_user"]


def build_graph(*, include_ask_user: bool = True):
    """build_agent 的别名，供 API 路由使用"""
    return build_agent(include_ask_user=include_ask_user)


def build_agent(*, include_ask_user: bool = True):
    """构建 DeepAgent 并返回 (agent, checkpointer)

    Args:
        include_ask_user: 是否包含 ask_user 工具。eval 时设为 False。
    """
    checkpointer = InMemorySaver()
    tools = ALL_TOOLS if include_ask_user else EVAL_TOOLS

    agent = create_deep_agent(
        model=get_llm(temperature=0.7),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    logger.info("DeepAgent 构建完成 | tools={}", [t.name for t in tools])
    return agent, checkpointer
