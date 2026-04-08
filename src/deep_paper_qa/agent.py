"""主图构建：路由 + 各 Pipeline subgraph 编排"""

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from loguru import logger

from deep_paper_qa.models import RouteCategory
from deep_paper_qa.pipelines.compare import paper_compare_node
from deep_paper_qa.pipelines.general import build_general_subgraph
from deep_paper_qa.pipelines.reading import paper_reading_node
from deep_paper_qa.pipelines.research import build_research_subgraph
from deep_paper_qa.pipelines.router import classify_question
from deep_paper_qa.pipelines.trend import build_trend_subgraph

# 拒答模板
REJECT_MESSAGE = "我是 AI 科研论文问答助手，只能回答与 AI 论文相关的问题。"


class MainState(MessagesState):
    """主图状态"""

    category: str


# 路由分类标签映射
CATEGORY_LABELS = {
    "reject": "拒答",
    "general": "普通问答",
    "research": "深度研究",
    "reading": "论文精读",
    "compare": "论文对比",
    "trend": "趋势分析",
}


async def router_node(state: MainState) -> dict:
    """路由节点：提取用户最新消息并分类"""
    last_msg = state["messages"][-1].content
    category = await classify_question(last_msg)
    label = CATEGORY_LABELS.get(category.value, category.value)
    logger.info("路由决策 | category={} | label={}", category.value, label)
    return {"category": category.value}


async def reject_node(state: MainState) -> dict:
    """拒答节点"""
    return {"messages": [AIMessage(content=REJECT_MESSAGE)]}


def route_by_category(state: dict) -> str:
    """根据路由分类结果决定下一个节点"""
    return state.get("category", "general")


def build_graph():
    """构建并返回主图 + checkpointer"""
    checkpointer = InMemorySaver()

    graph = StateGraph(MainState)

    graph.add_node("router", router_node)
    graph.add_node("reject", reject_node)
    graph.add_node("general", build_general_subgraph())
    graph.add_node("research", build_research_subgraph())
    graph.add_node("reading", paper_reading_node)
    graph.add_node("compare", paper_compare_node)
    graph.add_node("trend", build_trend_subgraph())

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        route_by_category,
        {c.value: c.value for c in RouteCategory},
    )
    for node in RouteCategory:
        graph.add_edge(node.value, END)

    compiled = graph.compile(checkpointer=checkpointer)
    return compiled, checkpointer
