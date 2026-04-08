"""论文精读 Pipeline（P2 占位）"""

from langchain_core.messages import AIMessage
from langgraph.graph import MessagesState

READING_PLACEHOLDER = "论文精读功能开发中，敬请期待。目前可以使用普通问答查询论文摘要信息。"


async def paper_reading_node(state: MessagesState) -> dict:
    """论文精读占位节点"""
    return {"messages": [AIMessage(content=READING_PLACEHOLDER)]}
