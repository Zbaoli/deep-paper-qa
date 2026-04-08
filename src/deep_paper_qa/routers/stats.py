"""统计数据 API 路由"""

from fastapi import APIRouter
from loguru import logger

from deep_paper_qa.tools.execute_sql import get_readonly_pool

router = APIRouter(tags=["stats"])


@router.get("/stats")
async def stats() -> dict:
    """论文统计数据"""
    pool = await get_readonly_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM papers")

        by_year = await conn.fetch(
            "SELECT year, COUNT(*) AS count FROM papers GROUP BY year ORDER BY year"
        )

        by_conference = await conn.fetch(
            "SELECT conference, COUNT(*) AS count FROM papers "
            "GROUP BY conference ORDER BY count DESC"
        )

    logger.info("API stats | total={}", total)
    return {
        "total_papers": total,
        "by_year": [dict(r) for r in by_year],
        "by_conference": [dict(r) for r in by_conference],
    }
