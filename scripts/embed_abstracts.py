"""批量生成论文摘要的向量嵌入，写入 papers.abstract_embedding 列。

用法：
    uv run python scripts/embed_abstracts.py [--batch-size 32] [--max-workers 4]
"""

import argparse
import asyncio
import time

import aiohttp
import asyncpg
from loguru import logger

from deep_paper_qa.config import settings

# embedding 列和索引的 DDL
_DDL_COLUMN = f"ALTER TABLE papers ADD COLUMN IF NOT EXISTS abstract_embedding vector({settings.embedding_dim})"
_DDL_INDEX = """
    CREATE INDEX IF NOT EXISTS idx_papers_abstract_embedding
    ON papers USING hnsw (abstract_embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64)
"""


async def ensure_schema(conn: asyncpg.Connection) -> None:
    """确保 embedding 列和索引存在"""
    await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    await conn.execute(_DDL_COLUMN)
    logger.info("abstract_embedding 列已就绪 (vector({}))", settings.embedding_dim)


async def build_index(conn: asyncpg.Connection) -> None:
    """创建 HNSW 索引（在所有数据写入后调用）"""
    logger.info("开始创建 HNSW 索引...")
    t0 = time.time()
    await conn.execute(_DDL_INDEX)
    logger.info("HNSW 索引创建完成，耗时 {:.1f}s", time.time() - t0)


async def get_embedding_batch(
    session: aiohttp.ClientSession, texts: list[str]
) -> list[list[float]]:
    """批量获取 embedding 向量"""
    async with session.post(
        f"{settings.embedding_base_url}/embeddings",
        json={"model": settings.embedding_model, "input": texts},
        timeout=aiohttp.ClientTimeout(total=120),
    ) as resp:
        resp.raise_for_status()
        data = await resp.json()
        # 按 index 排序确保顺序一致
        sorted_data = sorted(data["data"], key=lambda x: x["index"])
        return [d["embedding"] for d in sorted_data]


async def process_batch(
    pool: asyncpg.Pool,
    session: aiohttp.ClientSession,
    batch: list[tuple[str, str]],
) -> int:
    """处理一批论文：获取 embedding 并写入数据库"""
    ids = [row[0] for row in batch]
    texts = [row[1] for row in batch]

    embeddings = await get_embedding_batch(session, texts)

    # 批量更新
    async with pool.acquire() as conn:
        await conn.executemany(
            "UPDATE papers SET abstract_embedding = $1::vector WHERE id = $2",
            [(f"[{','.join(str(v) for v in emb)}]", pid) for emb, pid in zip(embeddings, ids)],
        )

    return len(ids)


async def main(batch_size: int = 32, max_workers: int = 4) -> None:
    pool = await asyncpg.create_pool(settings.pg_database_url, min_size=2, max_size=max_workers + 1)

    async with pool.acquire() as conn:
        await ensure_schema(conn)

        # 统计待处理数量
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM papers WHERE abstract IS NOT NULL AND abstract != '' AND abstract_embedding IS NULL"
        )
        done_count = await conn.fetchval(
            "SELECT COUNT(*) FROM papers WHERE abstract_embedding IS NOT NULL"
        )
        logger.info("已完成: {} 篇 | 待处理: {} 篇", done_count, total)

        if total == 0:
            logger.info("所有论文已完成 embedding，跳过")
            await build_index(conn)
            await pool.close()
            return

    # 流式读取待处理数据
    processed = 0
    t0 = time.time()
    semaphore = asyncio.Semaphore(max_workers)

    async def worker(batch: list[tuple[str, str]]) -> int:
        async with semaphore:
            return await process_batch(pool, session, batch)

    async with aiohttp.ClientSession() as session:
        # 分批读取
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, LEFT(coalesce(title, '') || '. ' || coalesce(abstract, ''), 2000) AS text
                   FROM papers
                   WHERE abstract IS NOT NULL AND abstract != '' AND abstract_embedding IS NULL
                   ORDER BY id"""
            )

        logger.info("读取 {} 条待处理记录", len(rows))

        # 分批并发处理
        tasks: list[asyncio.Task] = []
        for i in range(0, len(rows), batch_size):
            batch = [(r["id"], r["text"]) for r in rows[i : i + batch_size]]
            tasks.append(asyncio.create_task(worker(batch)))

        for task in asyncio.as_completed(tasks):
            n = await task
            processed += n
            elapsed = time.time() - t0
            speed = processed / elapsed if elapsed > 0 else 0
            eta = (total - processed) / speed if speed > 0 else 0
            if processed % (batch_size * 10) == 0 or processed == total:
                logger.info(
                    "进度: {}/{} ({:.1f}%) | 速度: {:.0f} 篇/s | 预计剩余: {:.0f}s",
                    processed, total, processed / total * 100, speed, eta,
                )

    logger.info("Embedding 完成，共处理 {} 篇，耗时 {:.1f}s", processed, time.time() - t0)

    # 创建索引
    async with pool.acquire() as conn:
        await build_index(conn)

    await pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量生成论文摘要 embedding")
    parser.add_argument("--batch-size", type=int, default=32, help="每批论文数量")
    parser.add_argument("--max-workers", type=int, default=4, help="并发 worker 数")
    args = parser.parse_args()

    asyncio.run(main(batch_size=args.batch_size, max_workers=args.max_workers))
