# Deep Paper QA

AI 科研论文智能问答助手。用户用自然语言提问，Agent 自动判断查元数据（→ PostgreSQL SQL）还是查论文内容（→ RAG 向量检索 API），然后综合回答。

## 架构

```
┌─────────────────────────────────────┐
│      FastAPI + Vue Frontend         │
└──────────────┬──────────────────────┘
               │ async
┌──────────────▼──────────────────────┐
│     LangGraph ReAct Agent           │
│  (ChatOpenAI + MemorySaver)         │
└──────┬──────────────────┬───────────┘
       │                  │
┌──────▼──────┐    ┌──────▼──────┐
│ execute_sql │    │vector_search│
│ (asyncpg)   │    │ (aiohttp)   │
└──────┬──────┘    └──────┬──────┘
       │                  │
┌──────▼──────┐    ┌──────▼──────┐
│ PostgreSQL  │    │ RAG API     │
│ papers 表   │    │ (Qdrant)    │
└─────────────┘    └─────────────┘
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repo-url>
cd deep_paper_qa

# 安装依赖
uv sync --all-extras
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入实际的数据库连接、LLM API Key 等
```

### 3. 初始化数据库

```bash
uv run python scripts/init_db.py
```

### 4. 启动应用

```bash
uv run uvicorn deep_paper_qa.api:app --reload
```

访问 http://localhost:8000 开始使用。

## 使用示例

- **统计问题**: "ACL 2025 有多少篇论文？"
- **内容问题**: "RAG 的 chunking 策略有哪些改进？"
- **混合问题**: "2025 年高引的 RAG 论文都提出了什么方法？"

## 测试

```bash
uv run pytest tests/ -v
```

## 评测

```bash
uv run python eval/run_eval.py
```

30 个评测问题（10 统计 / 10 内容 / 10 混合），评估工具路由正确性和回答质量。

## 技术栈

| 组件 | 选型 |
|------|------|
| Agent 框架 | LangGraph (ReAct) |
| LLM | ChatOpenAI |
| 数据库 | PostgreSQL + asyncpg |
| 向量检索 | 外部 RAG API + aiohttp |
| Web 框架 | FastAPI |
| 前端 | Vue.js |
| 配置 | pydantic-settings |
| 日志 | loguru |

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql://localhost:5432/deep_paper_qa` |
| `LLM_BASE_URL` | LLM API 地址 | `https://api.openai.com/v1` |
| `LLM_MODEL` | 模型名称 | `gpt-4o` |
| `LLM_API_KEY` | API Key | — |
| `RAG_API_URL` | RAG 检索 API 地址 | `http://localhost:8000/api/search` |
