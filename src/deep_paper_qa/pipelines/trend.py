"""趋势分析 Pipeline：固定流程 subgraph"""

import json
import re

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from loguru import logger

from deep_paper_qa.config import settings
from deep_paper_qa.models import TrendState
from deep_paper_qa.prompts import (
    TREND_PHASES_PROMPT,
    TREND_REPORT_PROMPT,
    TREND_SQL_PROMPT,
)
from deep_paper_qa.tools.execute_sql import execute_sql
from deep_paper_qa.tools.search_abstracts import search_abstracts


def _get_trend_llm() -> ChatOpenAI:
    """获取趋势分析用的 LLM"""
    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=0,
    )


async def generate_sql_node(state: TrendState) -> dict:
    """根据用户问题生成按年统计 SQL"""
    user_msg = state["messages"][-1].content
    llm = _get_trend_llm()
    prompt = TREND_SQL_PROMPT.format(question=user_msg)
    result = await llm.ainvoke([SystemMessage(content=prompt)])

    # 从 LLM 输出中提取 SQL（去掉可能的 markdown 代码块）
    sql = result.content.strip()
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    logger.info("趋势分析 | 生成 SQL: {}", sql[:200])
    return {"query_topic": user_msg, "stats_data": sql}


async def execute_stats_node(state: TrendState) -> dict:
    """执行统计 SQL"""
    sql = state.get("stats_data", "")  # 上一步存的是 SQL
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
    llm = _get_trend_llm()
    prompt = TREND_PHASES_PROMPT.format(stats_data=state["stats_data"])
    result = await llm.ainvoke([SystemMessage(content=prompt)])

    try:
        phases = json.loads(result.content)
    except json.JSONDecodeError:
        logger.warning("趋势阶段解析失败，使用空列表")
        phases = []

    logger.info("趋势分析 | 识别阶段: {}", phases)
    return {"phases": phases}


async def search_representatives_node(state: TrendState) -> dict:
    """为每个阶段检索代表性论文"""
    topic = state["query_topic"]
    papers: list[str] = []

    for phase in state["phases"]:
        years = phase.get("years", "")
        # 从年份范围提取 WHERE 条件
        where = ""
        if "-" in years:
            start, end = years.split("-", 1)
            where = f"year BETWEEN {start.strip()} AND {end.strip()}"
        elif years.strip().isdigit():
            where = f"year = {years.strip()}"

        result = await search_abstracts.ainvoke(
            {
                "query": topic,
                "mode": "fulltext",
                "limit": 3,
                "where": where,
            }
        )
        papers.append(f"### {phase.get('phase', '')} ({years})\n{result}")

    logger.info("趋势分析 | 检索代表作完成，共 {} 个阶段", len(state["phases"]))
    return {"representative_papers": papers}


async def synthesize_node(state: TrendState) -> dict:
    """综合生成趋势分析报告"""
    llm = _get_trend_llm()
    prompt = TREND_REPORT_PROMPT.format(
        topic=state["query_topic"],
        stats_data=state["stats_data"],
        phases=json.dumps(state["phases"], ensure_ascii=False),
        representative_papers="\n\n".join(state["representative_papers"]),
    )
    result = await llm.ainvoke([SystemMessage(content=prompt)])
    report = result.content

    # 生成 plotly 图表 JSON
    chart_json = ""
    year_counts = _parse_year_counts(state["stats_data"])
    if year_counts:
        import plotly.graph_objects as go

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
    content = report
    if chart_json:
        content = f"<!--plotly:{chart_json}-->\n\n{report}"
    return {"report": report, "messages": [AIMessage(content=content)]}


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
