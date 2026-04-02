"""ReAct Agent 构建"""

from typing import Any

from langchain_core.messages import trim_messages
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent

from deep_paper_qa.config import settings
from deep_paper_qa.prompts import SYSTEM_PROMPT
from deep_paper_qa.tools.ask_user import ask_user
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.search_abstracts import search_abstracts
from deep_paper_qa.tools.vector_search import vector_search


def build_agent():
    """构建并返回 ReAct Agent"""
    model = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )

    checkpointer = InMemorySaver()

    # 消息裁剪：保留最近 N 轮对话
    # deepseek-chat 不支持 ChatOpenAI 的 token 计数，改用字符数估算（~4 字符/token）
    trimmer = trim_messages(
        max_tokens=16000,
        strategy="last",
        token_counter=len,
        include_system=True,
        allow_partial=False,
    )

    def pre_model_hook(state: dict[str, Any]) -> dict[str, Any]:
        """裁剪消息后传给 LLM"""
        trimmed = trimmer.invoke(state["messages"])
        return {"llm_input_messages": trimmed}

    tools = [execute_sql, search_abstracts, vector_search, ask_user]

    agent = create_react_agent(
        model,
        tools=tools,
        checkpointer=checkpointer,
        prompt=SYSTEM_PROMPT,
        pre_model_hook=pre_model_hook,
    )

    return agent, checkpointer
