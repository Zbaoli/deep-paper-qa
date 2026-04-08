"""FastAPI 入口：API 路由 + CORS + 静态文件"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from deep_paper_qa.config import settings
from deep_paper_qa.logging_setup import setup_logging
from deep_paper_qa.routers import chat, papers, stats

setup_logging()

app = FastAPI(title="Deep Paper QA", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(papers.router, prefix="/api")
app.include_router(stats.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """健康检查"""
    return {"status": "ok"}
