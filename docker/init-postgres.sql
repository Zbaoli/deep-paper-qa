-- Deep Paper QA: PostgreSQL 初始化
-- 容器首次启动时自动执行

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
