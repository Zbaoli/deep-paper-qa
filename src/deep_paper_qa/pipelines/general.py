"""普通问题 Pipeline：ReAct Agent"""

from typing import Any

from langchain_core.messages import trim_messages
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from deep_paper_qa.config import settings
from deep_paper_qa.prompts import GENERAL_PROMPT
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.search_abstracts import search_abstracts

# 消息裁剪：保留最近 N 轮对话
_trimmer = trim_messages(
    max_tokens=16000,
    strategy="last",
    token_counter=len,
    include_system=True,
    allow_partial=False,
)


def _pre_model_hook(state: dict[str, Any]) -> dict[str, Any]:
    """裁剪消息后传给 LLM"""
    trimmed = _trimmer.invoke(state["messages"])
    return {"llm_input_messages": trimmed}


def build_general_subgraph():
    """构建普通问题 ReAct subgraph"""
    model = ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
    )

    return create_react_agent(
        model,
        tools=[execute_sql, search_abstracts],
        prompt=GENERAL_PROMPT,
        pre_model_hook=_pre_model_hook,
    )
