"""PostgreSQL schema 初始化脚本：创建 papers 表 + 索引"""

import asyncio
import os

import asyncpg
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

DDL = """
CREATE TABLE IF NOT EXISTS papers (
    id          TEXT PRIMARY KEY,   -- arxiv:2312.07559
    title       TEXT NOT NULL,
    abstract    TEXT,
    year        INT NOT NULL,
    conference  TEXT,               -- ACL, EMNLP, NeurIPS...
    venue_type  TEXT,               -- conference, journal, preprint
    authors     TEXT[],             -- PostgreSQL 数组
    citations   INT DEFAULT 0,
    directions  TEXT[],             -- 研究方向标签
    url         TEXT,
    pdf_url     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
CREATE INDEX IF NOT EXISTS idx_papers_conference ON papers(conference);
CREATE INDEX IF NOT EXISTS idx_papers_citations ON papers(citations);
"""


async def init_db() -> None:
    """创建 papers 表和索引"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL 环境变量未设置")
        raise SystemExit(1)

    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(DDL)
        logger.info("数据库初始化完成：papers 表 + 索引已创建")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(init_db())
