"""从本地 JSON 文件批量导入论文元数据到 PostgreSQL

用法：
    uv run python scripts/import_papers.py /Volumes/新加卷/papers

目录结构：
    papers/
    ├── acl/
    │   ├── 2025/
    │   │   ├── acl-2025-long-1.json           # 主元数据
    │   │   ├── acl-2025-long-1.openalex.json   # OpenAlex（含引用数）
    │   │   └── ...
    │   └── ...
    └── ...
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# 批量插入大小
BATCH_SIZE = 500

# 会议名标准化映射
CONFERENCE_MAP = {
    "aaai": "AAAI",
    "acl": "ACL",
    "emnlp": "EMNLP",
    "iclr": "ICLR",
    "icml": "ICML",
    "ijcai": "IJCAI",
    "kdd": "KDD",
    "naacl": "NAACL",
    "neurips": "NeurIPS",
    "www": "WWW",
}

INSERT_SQL = """
INSERT INTO papers (id, title, abstract, year, conference, venue_type, authors, citations, directions, url, pdf_url)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
ON CONFLICT (id) DO UPDATE SET
    citations = EXCLUDED.citations,
    directions = EXCLUDED.directions
"""


def parse_paper(meta_path: Path) -> dict | None:
    """解析单篇论文的 JSON 元数据 + OpenAlex 引用数据"""
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("解析失败 {}: {}", meta_path.name, e)
        return None

    paper_id = meta.get("paper_id", "")
    if not paper_id or not meta.get("title"):
        return None

    # 读取 OpenAlex 数据（可选，用于引用数）
    openalex_path = meta_path.with_suffix("").with_suffix(".openalex.json")
    citations = 0
    if openalex_path.exists():
        try:
            oa = json.loads(openalex_path.read_text(encoding="utf-8"))
            citations = oa.get("cited_by_count", 0) or 0
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

    # 清理 abstract（去除 <br/> 标签和 null 字节）
    abstract = meta.get("abstract", "") or ""
    abstract = abstract.replace("<br/>", "").replace("\x00", "").strip()

    # 标准化会议名
    raw_conf = meta.get("conference", "")
    conference = CONFERENCE_MAP.get(raw_conf.lower(), raw_conf.upper()) if raw_conf else None

    # keywords 作为 directions
    keywords_raw = meta.get("keywords", [])
    # 只保留有意义的关键词（过滤掉太通用的）
    generic_keywords = {
        "Computer science", "Mathematics", "Engineering", "Psychology",
        "Geography", "Physics", "Chemistry", "Biology", "Sociology",
        "Philosophy", "Economics", "Medicine", "Geodesy",
    }
    directions = [k for k in keywords_raw if k not in generic_keywords][:10]

    def clean(s: str) -> str:
        """去除 PostgreSQL 不接受的 null 字节"""
        return s.replace("\x00", "") if s else s

    return {
        "id": paper_id,
        "title": clean(meta["title"]),
        "abstract": abstract[:5000] if abstract else None,
        "year": meta.get("year", 0),
        "conference": conference,
        "venue_type": "conference",
        "authors": [clean(a) for a in meta.get("authors", [])],
        "citations": citations,
        "directions": [clean(d) for d in directions],
        "url": clean(meta.get("source_url", "") or ""),
        "pdf_url": clean(meta.get("pdf_url", "") or ""),
    }


async def import_papers(papers_dir: str) -> None:
    """扫描目录并批量导入论文"""
    database_url = os.getenv("PG_DATABASE_URL")
    if not database_url:
        logger.error("PG_DATABASE_URL 环境变量未设置")
        raise SystemExit(1)

    root = Path(papers_dir)
    if not root.is_dir():
        logger.error("目录不存在: {}", papers_dir)
        raise SystemExit(1)

    # 收集所有主 JSON 文件（排除 openalex 和 _failures）
    logger.info("扫描目录: {}", root)
    json_files = sorted(
        p for p in root.rglob("*.json")
        if not p.name.endswith(".openalex.json")
        and p.name != "_failures.json"
        and not p.name.startswith("._")
    )
    total = len(json_files)
    logger.info("发现 {} 个论文 JSON 文件", total)

    # 连接数据库
    conn = await asyncpg.connect(database_url)
    logger.info("数据库连接成功")

    imported = 0
    skipped = 0
    batch: list[tuple] = []

    try:
        for i, path in enumerate(json_files):
            paper = parse_paper(path)
            if paper is None:
                skipped += 1
                continue

            batch.append((
                paper["id"],
                paper["title"],
                paper["abstract"],
                paper["year"],
                paper["conference"],
                paper["venue_type"],
                paper["authors"],
                paper["citations"],
                paper["directions"],
                paper["url"],
                paper["pdf_url"],
            ))

            if len(batch) >= BATCH_SIZE:
                await conn.executemany(INSERT_SQL, batch)
                imported += len(batch)
                batch.clear()
                if imported % 5000 == 0:
                    logger.info("进度: {}/{} ({:.1f}%) | 已导入: {} | 跳过: {}",
                                i + 1, total, (i + 1) / total * 100, imported, skipped)

        # 导入剩余
        if batch:
            await conn.executemany(INSERT_SQL, batch)
            imported += len(batch)

    finally:
        await conn.close()

    logger.info("导入完成: 共 {} 篇 | 跳过 {} 个无效文件", imported, skipped)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: uv run python scripts/import_papers.py <papers_dir>")
        print("示例: uv run python scripts/import_papers.py /Volumes/新加卷/papers")
        sys.exit(1)

    asyncio.run(import_papers(sys.argv[1]))
