"""深度研究 Pipeline：显式多节点 subgraph"""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import create_react_agent
from loguru import logger

from deep_paper_qa.config import get_llm
from deep_paper_qa.models import ResearchState
from deep_paper_qa.prompts import (
    RESEARCH_CLARIFY_PROMPT,
    RESEARCH_PLAN_PROMPT,
    RESEARCH_REPORT_PROMPT,
    RESEARCH_STEP_PROMPT,
)
from deep_paper_qa.tools.ask_user import ask_user
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.search_abstracts import search_abstracts
from deep_paper_qa.tools.search_arxiv import search_arxiv
from deep_paper_qa.tools.search_semantic_scholar import search_semantic_scholar
from deep_paper_qa.tools.search_web import search_web


async def clarify_node(state: ResearchState) -> dict:
    """澄清追问节点：判断问题是否足够清晰"""
    llm = get_llm()
    user_msg = state["messages"][-1].content
    result = await llm.ainvoke(
        [
            SystemMessage(content=RESEARCH_CLARIFY_PROMPT),
            HumanMessage(content=user_msg),
        ]
    )

    new_count = state.get("clarify_count", 0) + 1
    logger.info("深度研究 | 澄清第{}轮: {}", new_count, result.content[:100])
    return {
        "messages": [AIMessage(content=f"**[澄清问题 {new_count}/3]**\n\n{result.content}")],
        "clarify_count": new_count,
    }


async def ask_clarify_node(state: ResearchState) -> dict:
    """通过 ask_user 向用户展示澄清问题并等待回复"""
    last_msg = state["messages"][-1].content
    response = await ask_user.ainvoke({"summary": "正在分析您的研究问题...", "question": last_msg})
    return {"messages": [HumanMessage(content=response)]}


def should_continue_clarify(state: ResearchState) -> str:
    """判断是否继续澄清"""
    last_msg = state["messages"][-1].content
    if "问题已明确" in last_msg or state.get("clarify_count", 0) >= 3:
        return "plan"
    return "ask_clarify"


async def plan_node(state: ResearchState) -> dict:
    """生成研究计划"""
    llm = get_llm()
    user_msgs = [m.content for m in state["messages"] if isinstance(m, HumanMessage)]
    context = "\n".join(user_msgs)

    result = await llm.ainvoke(
        [SystemMessage(content=RESEARCH_PLAN_PROMPT), HumanMessage(content=context)]
    )

    try:
        plan = json.loads(result.content)
    except json.JSONDecodeError:
        logger.warning("研究计划解析失败，尝试提取列表")
        plan = [line.strip() for line in result.content.split("\n") if line.strip()]

    logger.info("深度研究 | 研究计划: {} 个子问题", len(plan))
    plan_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(plan))
    return {
        "plan": plan,
        "current_step": 0,
        "messages": [AIMessage(content=f"**[研究计划]** 共 {len(plan)} 个子问题：\n\n{plan_text}")],
    }


async def ask_plan_confirm_node(state: ResearchState) -> dict:
    """向用户展示研究计划并等待确认"""
    plan = state.get("plan", [])
    plan_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(plan))
    response = await ask_user.ainvoke(
        {
            "summary": f"已制定研究计划，共 {len(plan)} 个子问题：\n\n{plan_text}",
            "question": "请确认计划，或提出修改意见。回复\u300c继续\u300d开始执行。",
        }
    )
    return {"messages": [HumanMessage(content=response)]}


async def research_step_node(state: ResearchState) -> dict:
    """执行当前子问题的检索"""
    plan = state.get("plan", [])
    step_idx = state.get("current_step", 0)
    findings = state.get("findings", [])

    if step_idx >= len(plan):
        return {}

    current_question = plan[step_idx]
    logger.info("深度研究 | 执行子问题 {}/{}: {}", step_idx + 1, len(plan), current_question)

    llm = get_llm()
    prompt = RESEARCH_STEP_PROMPT.format(current_question=current_question)
    step_agent = create_react_agent(
        llm,
        tools=[execute_sql, search_abstracts, search_arxiv, search_semantic_scholar, search_web],
        prompt=prompt,
    )

    result = await step_agent.ainvoke({"messages": [HumanMessage(content=current_question)]})
    ai_messages = [m for m in result["messages"] if isinstance(m, AIMessage) and m.content]
    finding = ai_messages[-1].content if ai_messages else "未找到相关结果"

    new_findings = [*findings, f"### 子问题 {step_idx + 1}: {current_question}\n\n{finding}"]
    total = len(plan)
    return {
        "findings": new_findings,
        "current_step": step_idx + 1,
        "messages": [
            AIMessage(
                content=f"**[子问题 {step_idx + 1}/{total}]** {current_question}\n\n{finding}"
            )
        ],
    }


async def ask_step_confirm_node(state: ResearchState) -> dict:
    """子问题执行后，向用户展示发现并等待指令"""
    findings = state.get("findings", [])
    latest_finding = findings[-1] if findings else "无"
    step_idx = state.get("current_step", 0)
    total = len(state.get("plan", []))

    question = "请选择：继续下一个子问题 / 调整方向（请说明）/ 直接生成总结"
    if step_idx >= total:
        question = "所有子问题已执行完毕。回复\u300c总结\u300d生成研究报告。"

    response = await ask_user.ainvoke(
        {"summary": f"子问题 {step_idx}/{total} 完成。\n\n{latest_finding}", "question": question}
    )
    return {"messages": [HumanMessage(content=response)]}


def should_continue_research(state: ResearchState) -> str:
    """判断是否继续执行子问题"""
    last_msg = state["messages"][-1].content if state["messages"] else ""
    if "总结" in last_msg or state.get("current_step", 0) >= len(state.get("plan", [])):
        return "report"
    return "research_step"


async def report_node(state: ResearchState) -> dict:
    """生成最终研究报告"""
    llm = get_llm()
    findings_text = "\n\n".join(state.get("findings", []))
    prompt = RESEARCH_REPORT_PROMPT.format(findings=findings_text)
    result = await llm.ainvoke([SystemMessage(content=prompt)])
    logger.info("深度研究 | 报告生成完成，长度={}", len(result.content))
    return {"messages": [AIMessage(content=f"**[研究报告]**\n\n{result.content}")]}


def build_research_subgraph() -> StateGraph:
    """构建深度研究 subgraph"""
    graph = StateGraph(ResearchState)

    graph.add_node("clarify", clarify_node)
    graph.add_node("ask_clarify", ask_clarify_node)
    graph.add_node("plan", plan_node)
    graph.add_node("ask_plan_confirm", ask_plan_confirm_node)
    graph.add_node("research_step", research_step_node)
    graph.add_node("ask_step_confirm", ask_step_confirm_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("clarify")
    graph.add_conditional_edges(
        "clarify", should_continue_clarify, {"plan": "plan", "ask_clarify": "ask_clarify"}
    )
    graph.add_edge("ask_clarify", "clarify")
    graph.add_edge("plan", "ask_plan_confirm")
    graph.add_edge("ask_plan_confirm", "research_step")
    graph.add_edge("research_step", "ask_step_confirm")
    graph.add_conditional_edges(
        "ask_step_confirm",
        should_continue_research,
        {"research_step": "research_step", "report": "report"},
    )
    graph.add_edge("report", END)

    return graph.compile()
