"""Pydantic 数据模型"""

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
