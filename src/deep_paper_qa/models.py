"""Pydantic 数据模型"""

from enum import Enum
from typing import Any

from langgraph.graph import MessagesState
from pydantic import BaseModel


class PaperRecord(BaseModel):
    """论文元数据记录（对应 PostgreSQL papers 表）"""

    id: str
    title: str
    abstract: str | None = None
    year: int
    conference: str | None = None
    venue_type: str | None = None
    authors: list[str] = []
    citations: int = 0
    directions: list[str] = []
    url: str | None = None
    pdf_url: str | None = None


class SearchChunk(BaseModel):
    """向量检索返回的单个文档片段"""

    paper_id: str = ""
    paper_title: str = ""
    content: str = ""
    score: float = 0.0


class SearchResult(BaseModel):
    """向量检索结果"""

    query: str
    chunks: list[SearchChunk] = []


class RouteCategory(str, Enum):
    """路由分类枚举"""

    REJECT = "reject"
    GENERAL = "general"
    RESEARCH = "research"
    READING = "reading"
    COMPARE = "compare"
    TREND = "trend"


class RouterOutput(BaseModel):
    """路由节点的 LLM structured output"""

    category: RouteCategory


class ResearchState(MessagesState):
    """深度研究 pipeline 状态"""

    plan: list[str]
    current_step: int
    findings: list[str]
    clarify_count: int


class TrendState(MessagesState):
    """趋势分析 pipeline 状态"""

    query_topic: str
    stats_data: str
    phases: list[dict[str, Any]]
    representative_papers: list[str]
    report: str
