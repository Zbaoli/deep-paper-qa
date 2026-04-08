# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI 科研论文智能问答助手（81,913 篇 AI 会议论文，2020-2025）。用户自然语言提问，LangGraph ReAct Agent 自动路由到 Text-to-SQL（元数据统计）、全文检索或向量语义检索，综合回答。

## 常用命令

```bash
uv sync --all-extras          # 安装所有依赖（含 dev）
uv run chainlit run src/deep_paper_qa/app.py   # 启动应用 (http://localhost:8000)
uv run pytest tests/ -v       # 运行全部测试
uv run pytest tests/test_execute_sql.py -v     # 运行单个测试文件
uv run pytest tests/ -v -k "test_name"         # 运行单个测试用例
uv run ruff check src/ tests/                  # Lint
uv run ruff format src/ tests/                 # Format
uv run python eval/run_eval.py                 # 评测（30 题）
uv run python scripts/init_db.py               # 初始化数据库 schema
uv run python scripts/import_papers.py <dir>   # 导入论文数据
uv run python scripts/embed_abstracts.py       # 生成向量嵌入
```

## 架构

```
Chainlit UI (app.py)
  └─ LangGraph 多管线 Agent (agent.py) + InMemorySaver
       ├─ execute_sql    — asyncpg → PostgreSQL（元数据统计，仅 SELECT）
       ├─ search_abstracts — 全文检索 + 向量语义检索（本地数据库）
       ├─ search_arxiv   — aiohttp → arXiv API（最新预印本）
       ├─ search_semantic_scholar — aiohttp → Semantic Scholar API（引用数据、跨库搜索）
       └─ search_web     — aiohttp → Tavily API（网络搜索、非学术信息）
```

- **agent.py**: 多管线路由（general/research/trend/reading/compare），各子图绑定工具，system prompt 来自 prompts.py
- **prompts.py**: 各管线 system prompt，包含工具选择策略（本地优先、联网补充）、SQL 模式、关键词扩展规则
- **config.py**: `pydantic-settings` 加载 `.env`，所有配置项集中管理
- **app.py**: Chainlit 入口，处理消息流式输出、tool call 展示、loguru + JSONL 双日志
- **conversation_logger.py**: 每个对话写独立 JSONL 文件到 `logs/`

## 数据库

PostgreSQL 16 + pgvector，单表 `papers`：
- 关键字段：`id, title, abstract, year, conference, authors, citations, abstract_embedding(1024), directions`
- 索引：GIN 全文索引、HNSW 向量索引、B-tree(year/conference/citations)
- `directions` 字段数据质量差，system prompt 已禁用

## 测试

- pytest + pytest-asyncio（`asyncio_mode = "auto"`）
- 测试用 mock 替代真实数据库和 API 调用
- 测试文件：`test_execute_sql.py`, `test_vector_search.py`, `test_agent.py`, `test_conversation_logger.py`

## 配置

复制 `.env.example` → `.env`。核心变量：
- `DATABASE_URL` — PostgreSQL 连接串
- `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY` — LLM 配置（OpenAI 兼容）
- `EMBEDDING_BASE_URL` / `EMBEDDING_MODEL` / `EMBEDDING_DIM` — 嵌入服务
- `SEMANTIC_SCHOLAR_API_KEY` — Semantic Scholar API key（可选，提高速率限制）
- `TAVILY_API_KEY` — Tavily Search API key（必填，启用网络搜索）

## Docker

`docker/docker-compose.yml` 启动 PostgreSQL(pgvector) + RAGFlow 全套服务（8 容器）。PostgreSQL 端口 10001。

## Ruff 配置

- target: Python 3.11, line-length: 100
