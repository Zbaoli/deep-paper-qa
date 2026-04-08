"""趋势分析 Pipeline：固定流程 subgraph"""

import asyncio
import json
import re

import plotly.graph_objects as go
from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, StateGraph
from loguru import logger

from deep_paper_qa.config import get_llm
from deep_paper_qa.models import TrendState
from deep_paper_qa.prompts import (
    TREND_PHASES_PROMPT,
    TREND_REPORT_PROMPT,
    TREND_SQL_PROMPT,
)
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.search_abstracts import search_abstracts


async def generate_sql_node(state: TrendState) -> dict:
    """根据用户问题生成按年统计 SQL"""
    user_msg = state["messages"][-1].content
    llm = get_llm()
    prompt = TREND_SQL_PROMPT.format(question=user_msg)
    result = await llm.ainvoke([SystemMessage(content=prompt)])

    sql = result.content.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    logger.info("趋势分析 | 生成 SQL: {}", sql[:200])
    return {"query_topic": user_msg, "stats_data": sql}


async def execute_stats_node(state: TrendState) -> dict:
    """执行统计 SQL"""
    sql = state.get("stats_data", "")
    result = await execute_sql.ainvoke({"sql": sql})
    logger.info("趋势分析 | 统计结果: {}", result[:200])
    return {"stats_data": result}


def _parse_year_counts(stats_text: str) -> list[tuple[int, int]]:
    """从统计结果文本中提取 (年份, 数量) 列表"""
    pairs: list[tuple[int, int]] = []
    for line in stats_text.split("\n"):
        match = re.match(r"\s*(\d{4})\s*\|\s*(\d+)", line)
        if match:
            pairs.append((int(match.group(1)), int(match.group(2))))
    return sorted(pairs)


async def identify_phases_node(state: TrendState) -> dict:
    """根据统计数据识别趋势阶段"""
    llm = get_llm()
    prompt = TREND_PHASES_PROMPT.format(stats_data=state["stats_data"])
    result = await llm.ainvoke([SystemMessage(content=prompt)])

    try:
        phases = json.loads(result.content)
    except json.JSONDecodeError:
        logger.warning("趋势阶段解析失败，使用空列表")
        phases = []

    logger.info("趋势分析 | 识别阶段: {}", phases)
    return {"phases": phases}


def _build_where(years: str) -> str:
    """从年份范围字符串构造 SQL WHERE 条件"""
    if "-" in years:
        start, end = years.split("-", 1)
        return f"year BETWEEN {start.strip()} AND {end.strip()}"
    if years.strip().isdigit():
        return f"year = {years.strip()}"
    return ""


async def search_representatives_node(state: TrendState) -> dict:
    """为每个阶段并行检索代表性论文"""
    topic = state["query_topic"]
    phases = state["phases"]

    async def search_phase(phase: dict) -> str:
        years = phase.get("years", "")
        where = _build_where(years)
        result = await search_abstracts.ainvoke(
            {"query": topic, "mode": "fulltext", "limit": 3, "where": where}
        )
        return f"### {phase.get('phase', '')} ({years})\n{result}"

    papers = await asyncio.gather(*(search_phase(p) for p in phases))
    logger.info("趋势分析 | 检索代表作完成，共 {} 个阶段", len(phases))
    return {"representative_papers": list(papers)}


async def synthesize_node(state: TrendState) -> dict:
    """综合生成趋势分析报告"""
    llm = get_llm()
    prompt = TREND_REPORT_PROMPT.format(
        topic=state["query_topic"],
        stats_data=state["stats_data"],
        phases=json.dumps(state["phases"], ensure_ascii=False),
        representative_papers="\n\n".join(state["representative_papers"]),
    )
    result = await llm.ainvoke([SystemMessage(content=prompt)])
    report = result.content

    chart_json = ""
    year_counts = _parse_year_counts(state["stats_data"])
    if year_counts:
        years = [str(y) for y, _ in year_counts]
        counts = [c for _, c in year_counts]
        fig = go.Figure(data=[go.Bar(x=years, y=counts, marker_color="#3b82f6")])
        fig.update_layout(
            title=f"{state['query_topic']} — 论文数量趋势",
            xaxis_title="年份",
            yaxis_title="论文数量",
            template="plotly_dark",
            height=400,
        )
        chart_json = fig.to_json()

    logger.info("趋势分析 | 报告生成完成，长度={} | 含图表={}", len(report), bool(chart_json))
    content = f"<!--plotly:{chart_json}-->\n\n{report}" if chart_json else report
    return {"messages": [AIMessage(content=content)]}


def build_trend_subgraph() -> StateGraph:
    """构建趋势分析 subgraph"""
    graph = StateGraph(TrendState)

    graph.add_node("generate_sql", generate_sql_node)
    graph.add_node("execute_stats", execute_stats_node)
    graph.add_node("identify_phases", identify_phases_node)
    graph.add_node("search_representatives", search_representatives_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("generate_sql")
    graph.add_edge("generate_sql", "execute_stats")
    graph.add_edge("execute_stats", "identify_phases")
    graph.add_edge("identify_phases", "search_representatives")
    graph.add_edge("search_representatives", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()
