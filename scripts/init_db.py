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

-- 全文检索索引（title + abstract）
CREATE INDEX IF NOT EXISTS idx_papers_fts ON papers
    USING GIN (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(abstract, '')));
"""


READONLY_ROLE_DDL = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'dpqa_readonly') THEN
        CREATE ROLE dpqa_readonly WITH LOGIN PASSWORD 'dpqa_readonly_pass';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE current_database() TO dpqa_readonly;
GRANT USAGE ON SCHEMA public TO dpqa_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dpqa_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO dpqa_readonly;
"""


async def init_db() -> None:
    """创建 papers 表、索引和只读角色"""
    database_url = os.getenv("PG_DATABASE_URL")
    if not database_url:
        logger.error("PG_DATABASE_URL 环境变量未设置")
        raise SystemExit(1)

    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(DDL)
        logger.info("数据库初始化完成：papers 表 + 索引已创建")

        # 创建只读角色（用于 search_abstracts 和 vector_search 的安全隔离）
        try:
            await conn.execute(READONLY_ROLE_DDL)
            logger.info("只读角色 dpqa_readonly 已创建/更新")
        except Exception as e:
            logger.warning("只读角色创建失败（非致命）: {}", e)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(init_db())
