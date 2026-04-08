"""普通问题 Pipeline：ReAct Agent"""

from typing import Any

from langchain_core.messages import trim_messages
from langgraph.prebuilt import create_react_agent

from deep_paper_qa.config import get_llm
from deep_paper_qa.prompts import GENERAL_PROMPT
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.search_abstracts import search_abstracts

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
    return create_react_agent(
        get_llm(temperature=0.7),
        tools=[execute_sql, search_abstracts],
        prompt=GENERAL_PROMPT,
        pre_model_hook=_pre_model_hook,
    )
