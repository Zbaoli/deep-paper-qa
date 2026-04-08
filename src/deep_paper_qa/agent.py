"""主图构建：路由 + 各 Pipeline subgraph 编排"""

from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from loguru import logger

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


async def router_node(state: MainState) -> dict:
    """路由节点：提取用户最新消息并分类"""
    last_msg = state["messages"][-1].content
    category = await classify_question(last_msg)
    logger.info("路由决策 | category={}", category.value)
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

    # 添加节点
    graph.add_node("router", router_node)
    graph.add_node("reject", reject_node)
    graph.add_node("general", build_general_subgraph())
    graph.add_node("research", build_research_subgraph())
    graph.add_node("reading", paper_reading_node)
    graph.add_node("compare", paper_compare_node)
    graph.add_node("trend", build_trend_subgraph())

    # 设置入口
    graph.set_entry_point("router")

    # 路由条件边
    graph.add_conditional_edges("router", route_by_category, {
        "reject": "reject",
        "general": "general",
        "research": "research",
        "reading": "reading",
        "compare": "compare",
        "trend": "trend",
    })

    # 所有终端节点连接到 END
    graph.add_edge("reject", END)
    graph.add_edge("general", END)
    graph.add_edge("research", END)
    graph.add_edge("reading", END)
    graph.add_edge("compare", END)
    graph.add_edge("trend", END)

    compiled = graph.compile(checkpointer=checkpointer)
    return compiled, checkpointer
