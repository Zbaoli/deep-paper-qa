"""论文对比 Pipeline（P2 占位）"""

from langgraph.graph import MessagesState


COMPARE_PLACEHOLDER = "论文对比功能开发中，敬请期待。目前可以使用普通问答查询并对比论文摘要。"


async def paper_compare_node(state: MessagesState) -> dict:
    """论文对比占位节点"""
    from langchain_core.messages import AIMessage

    return {"messages": [AIMessage(content=COMPARE_PLACEHOLDER)]}
