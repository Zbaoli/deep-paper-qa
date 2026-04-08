"""论文浏览 API 路由"""

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from deep_paper_qa.tools.execute_sql import get_readonly_pool

router = APIRouter(tags=["papers"])


@router.get("/papers")
async def search_papers(
    q: str = Query("", description="搜索关键词"),
    year: int | None = Query(None, description="年份过滤"),
    conference: str | None = Query(None, description="会议过滤"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
) -> dict:
    """搜索论文列表"""
    conditions: list[str] = []
    params: list = []
    param_idx = 1

    if q:
        conditions.append(
            f"to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(abstract,''))"
            f" @@ websearch_to_tsquery('english', ${param_idx})"
        )
        params.append(q)
        param_idx += 1

    if year:
        conditions.append(f"year = ${param_idx}")
        params.append(year)
        param_idx += 1

    if conference:
        conditions.append(f"conference = ${param_idx}")
        params.append(conference)
        param_idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size

    sql = f"""
        SELECT id, title, year, conference, citations,
               LEFT(abstract, 200) AS abstract
        FROM papers
        {where}
        ORDER BY citations DESC, year DESC
        LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([page_size, offset])

    logger.info("API papers | q='{}' year={} conf={} page={}", q, year, conference, page)

    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        records = await conn.fetch(sql, *params)

    papers = [dict(r) for r in records]
    return {"papers": papers, "page": page, "page_size": page_size}


@router.get("/papers/{paper_id}")
async def paper_detail(paper_id: str) -> dict:
    """论文详情"""
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT id, title, abstract, year, conference, venue_type, "
            "authors, citations, url, pdf_url FROM papers WHERE id = $1",
            paper_id,
        )

    if not record:
        raise HTTPException(status_code=404, detail="论文不存在")

    return dict(record)
