# Deep Paper QA — 工程实现计划

## Context

构建 AI 科研论文智能问答助手。用户用自然语言提问，Agent 自动判断是查元数据/统计（→ PostgreSQL SQL）还是查论文内容（→ RAG 项目向量检索 API），然后综合回答。

基于设计文档：`~/.gstack/projects/deep_paper_qa/baoli-unknown-design-20260330-210006.md`

## 审查决策记录

| 决策 | 结果 | 理由 |
|------|------|------|
| LLM 集成 | ChatOpenAI 直连模型提供商 | 一个进程，新手友好 |
| 前端 | Chainlit | Agent 中间步骤完整展示 |
| Tool 数量 | 2 个（execute_sql + vector_search） | 减少 Agent 决策负担 |
| SQL 安全 | 语句级校验（正则拒绝非 SELECT） | 用户选择，生产环境建议加 DB 层防护 |
| Token 控制 | 三层截断（SQL结果 + 向量结果 + 对话历史） | 必做，防止 context 爆炸 |
| 数据源 | PostgreSQL 元数据本项目管，Qdrant 是外部 RAG 项目 | 分工明确 |

## 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| Agent 框架 | `langgraph>=0.3` | `create_react_agent` 预构建 ReAct |
| LLM | `langchain-openai` (ChatOpenAI) | `base_url` 直指模型提供商 |
| 数据库 | PostgreSQL + `asyncpg` | 论文元数据存储 |
| 向量检索 | 外部 RAG 项目 API + `aiohttp` | 语义检索调用 |
| 数据模型 | Pydantic v2（IO）+ TypedDict（State） | LangGraph 要求 state 用 TypedDict |
| 前端 | Chainlit | Agent 步骤流式展示 |
| 日志 | loguru | — |
| 配置 | pydantic-settings + python-dotenv | — |
| 包管理 | uv | — |

## 核心架构

```
┌─────────────────────────────────────────────────┐
│                   Chainlit UI                    │
│  (聊天 + Agent 中间步骤 + 表格/列表结果展示)       │
└──────────────────────┬──────────────────────────┘
                       │ async
┌──────────────────────▼──────────────────────────┐
│          LangGraph ReAct Agent                   │
│  create_react_agent(model, tools, checkpointer)  │
│                                                  │
│  State: TypedDict {messages: list[BaseMessage]}  │
│  Model: ChatOpenAI(base_url=provider)            │
│  Checkpointer: MemorySaver                       │
│  Messages: trim_messages(max_tokens=...)         │
│  recursion_limit: 10                             │
└──────────┬──────────────────┬───────────────────┘
           │                  │
    ┌──────▼──────┐    ┌──────▼──────┐
    │ execute_sql │    │vector_search│
    │             │    │             │
    │ Text-to-SQL │    │ 调用 RAG    │
    │ PostgreSQL  │    │ 项目 API    │
    └──────┬──────┘    └──────┬──────┘
           │                  │
    ┌──────▼──────┐    ┌──────▼──────┐
    │ PostgreSQL  │    │ RAG 项目    │
    │ papers 表   │    │ 向量检索API │
    └─────────────┘    └─────────────┘
```

## PostgreSQL Schema

```sql
CREATE TABLE papers (
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

CREATE INDEX idx_papers_year ON papers(year);
CREATE INDEX idx_papers_conference ON papers(conference);
CREATE INDEX idx_papers_citations ON papers(citations);
```

## System Prompt 要点

```
你是一个 AI 科研论文问答助手。你有两个工具：

1. execute_sql: 查询 PostgreSQL 数据库中的论文元数据。数据库 schema:
   {CREATE TABLE DDL}

   注意：authors 和 directions 是 TEXT[] 数组类型。
   查询数组用 ANY()：WHERE 'RAG' = ANY(directions)
   查询数组长度用 array_length()：array_length(authors, 1)

   示例：
   - "ACL 2025 多少篇论文" → SELECT COUNT(*) FROM papers WHERE year=2025 AND conference='ACL'
   - "2025 高引 RAG 论文" → SELECT title, citations FROM papers WHERE year=2025 AND 'RAG'=ANY(directions) ORDER BY citations DESC LIMIT 10

   只允许 SELECT 查询。禁止 INSERT/UPDATE/DELETE。
   查询结果最多返回 20 行。

2. vector_search: 语义检索论文内容。用于回答关于论文方法、实验、结论等内容级问题。
   输入自然语言查询，返回相关论文段落。

规则：
- 统计/元数据问题 → 用 execute_sql
- 内容/方法论问题 → 用 vector_search
- 混合问题 → 先 execute_sql 定位论文，再 vector_search 查内容
- 回答必须基于工具返回的数据，禁止编造论文信息
- 引用论文时附带 title 和 id
```

## 项目结构

```
deep_paper_qa/
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── src/
│   └── deep_paper_qa/
│       ├── __init__.py
│       ├── config.py            # pydantic-settings 配置
│       ├── models.py            # Pydantic 数据模型
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── execute_sql.py   # Text-to-SQL tool (asyncpg)
│       │   └── vector_search.py # 调用 RAG 项目 API (aiohttp)
│       ├── agent.py             # ReAct Agent 构建
│       ├── prompts.py           # System prompt
│       └── app.py               # Chainlit 入口
├── scripts/
│   └── init_db.py               # PostgreSQL schema 初始化 + 数据导入
├── tests/
│   ├── conftest.py
│   ├── test_execute_sql.py      # 5 tests
│   ├── test_vector_search.py    # 3 tests
│   ├── test_agent.py            # 3 tests
│   └── test_models.py           # 2 tests
└── eval/
    ├── questions.jsonl           # 30 评测问题
    └── run_eval.py               # 评测脚本
```

## 实现步骤

### Step 1: 项目初始化 + Schema
- `uv init`，配置 pyproject.toml
- 依赖：langgraph, langchain-openai, pydantic, pydantic-settings, chainlit, loguru, python-dotenv, asyncpg, aiohttp, pytest, pytest-asyncio
- 创建 .env.example（DATABASE_URL, LLM_BASE_URL, LLM_MODEL, LLM_API_KEY, RAG_API_URL）
- `scripts/init_db.py`：创建 papers 表 + 索引
- 初始化 git repo

### Step 2: 配置 + 数据模型
- `config.py`: pydantic-settings 加载环境变量
- `models.py`: PaperRecord, SearchResult 等 Pydantic 模型

### Step 3: execute_sql Tool
- asyncpg 连接池
- SQL 语句校验（正则拒绝非 SELECT）
- 查询超时 10s（`asyncpg.execute` 带 timeout）
- 结果截断：最多 20 行，abstract 截断 200 字
- 失败返回错误消息字符串（不抛异常）
- 测试：5 个 case（正常、非SELECT拒绝、语法错误、超时、空结果）

### Step 4: vector_search Tool
- aiohttp 调用 RAG 项目检索 API
- 返回 top_k=5 个 chunks，每个截断 500 字
- 失败返回错误消息
- 测试：3 个 case（正常、API不可用、空结果）

### Step 5: Agent 核心
- `prompts.py`：上述 system prompt（含 DDL + few-shot）
- `agent.py`：
  ```python
  from langgraph.prebuilt import create_react_agent
  from langgraph.checkpoint.memory import MemorySaver
  from langchain_openai import ChatOpenAI

  model = ChatOpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key, model=config.llm_model)
  checkpointer = MemorySaver()
  agent = create_react_agent(model, tools=[execute_sql, vector_search], checkpointer=checkpointer, state_modifier=system_prompt)
  ```
- `recursion_limit=10` 防止无限循环
- `trim_messages` 保留最近 6 轮对话
- 测试：3 个 case（统计路由、内容路由、多轮上下文）

### Step 6: Chainlit 前端
- `app.py`：
  - `@cl.on_message` → agent.astream_events()
  - 展示中间步骤（tool 调用名 + 参数 + 结果摘要）
  - thread_id 关联 checkpointer 实现多轮对话
- 这是最难的部分，Chainlit + LangGraph async streaming 集成需要仔细调试

### Step 7: 评测 + README
- 30 个评测问题（10 统计 / 10 内容 / 10 混合），JSONL 格式
- `run_eval.py`：批量运行，对比期望结果
- 评估方式：SQL 正确性（exact match）+ 回答质量（LLM-as-judge with rubric）
- README：quick start, 架构图, 环境配置说明

## Token 控制策略

```
┌─────────────────────────────────┐
│         Token 预算分配           │
├─────────────────────────────────┤
│ System Prompt (DDL+few-shot)    │  ~800 tokens
│ 对话历史 (trim_messages 6轮)    │  ~2000 tokens
│ Tool 返回结果 (截断后)          │  ~1500 tokens
│ Agent 推理 + 最终回答           │  ~1700 tokens
├─────────────────────────────────┤
│ 总计                            │  ~6000 tokens
│ 模型上限（留余量）              │  8000+ tokens
└─────────────────────────────────┘
```

## 错误处理

| 场景 | 处理 |
|------|------|
| SQL 非 SELECT | 拒绝执行，返回"只允许查询操作" |
| SQL 语法错误 | 返回 PG 错误信息，Agent 可修正重试 |
| SQL 超时 | 返回"查询超时，请简化查询条件" |
| 查询空结果 | 返回"未找到匹配结果"，Agent 建议放宽条件 |
| RAG API 不可用 | 返回"内容检索服务暂不可用"，Agent 用 SQL 尽力回答 |
| Agent 循环过多 | recursion_limit=10 强制停止 |
| 对话过长 | trim_messages 自动裁剪 |

## 关键风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| Chainlit + LangGraph async 集成难度 | 开发时间超预期 | Step 6 是最难的，预留充足时间 |
| LLM 生成错误 SQL | 查询失败 | few-shot 示例 + Agent 能看到 PG 错误并重试 |
| TEXT[] 数组语法 LLM 不熟 | 查询失败 | system prompt 显式教 ANY() 语法 |
| SQL 正则绕过 | 数据安全 | 已知简化，生产加 DB 只读用户 |

## 验证方案

1. `uv run pytest` — 13 个单元测试全通过
2. `uv run chainlit run src/deep_paper_qa/app.py` — UI 可访问
3. 手动测试："ACL 2025 多少篇论文" → 返回准确数字
4. 手动测试："RAG chunking 策略改进" → 返回内容 + 引用
5. 手动测试多轮追问
6. `uv run python eval/run_eval.py` — 30 题评测

## NOT in scope

| 项目 | 理由 |
|------|------|
| 数据库只读用户/RBAC | 用户选择 MVP 简化，生产环境建议加上 |
| citation_analysis | Phase 2 |
| 数据入库 pipeline | PostgreSQL 用脚本导入，Qdrant 由 RAG 项目管理 |
| PostgreSQL checkpointer | 开发用 MemorySaver |
| Docker Compose | Phase 2 |
| PyPI 发包 | Phase 2 |
| LiteLLM proxy | 可选高级配置，不在默认流程中 |

## What already exists

| 组件 | 状态 |
|------|------|
| RAG 项目（Qdrant + 检索 API） | 已有，外部依赖 |
| PostgreSQL 实例 | 需要用户自备 |
| 项目代码 | 无（绿地） |

## Failure Modes

| 失败场景 | 有测试？ | 有错误处理？ | 用户看到？ |
|----------|---------|-------------|-----------|
| SQL 非 SELECT | 是 | 是（拒绝） | 清晰错误 |
| SQL 语法错误 | 是 | 是（返回 PG 错误） | Agent 重试或报错 |
| SQL 超时 | 是 | 是（timeout） | "查询超时" |
| RAG API 挂 | 是 | 是（错误消息） | Agent 降级用 SQL |
| Agent 无限循环 | 否 | 是（recursion_limit） | 强制停止 |
| Token 爆 | 否 | 是（trim_messages） | 老消息被裁剪 |

**Critical gap**: 无。所有高风险失败场景都有错误处理。Agent 无限循环和 Token 爆没有专门测试，但有框架级防护。

## 并行化策略

| Step | 模块 | 依赖 |
|------|------|------|
| Step 1-2 | 项目初始化、配置、模型 | — |
| Step 3 | execute_sql | Step 1-2 |
| Step 4 | vector_search | Step 1-2 |
| Step 5 | Agent 核心 | Step 3, 4 |
| Step 6 | Chainlit | Step 5 |
| Step 7 | 评测 + README | Step 5 |

**Lane A**: Step 1-2 → Step 3 → Step 5 → Step 6
**Lane B**: Step 4（与 Step 3 并行，都依赖 Step 1-2）
**Lane C**: Step 7（与 Step 6 并行，都依赖 Step 5）

Step 3 和 Step 4 可以在不同 worktree 中并行开发。Step 6 和 Step 7 也可以并行。

## TODOS

1. **PostgreSQL 只读用户防护** — 生产环境为 execute_sql 创建只读 DB 用户 + schema 级权限控制。当前 MVP 仅做正则校验，正则可被绕过。
2. **评测分层完善** — 增加 Layer 3 工具选择正确性评估（统计问题应走 SQL，内容问题应走向量），当前只做了 SQL 正确性 + 回答质量。

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 6 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| Outside Voice | Claude subagent | Independent plan challenge | 1 | ISSUES_FOUND | 9 findings, 3 resolved via user decisions |

**VERDICT:** ENG REVIEW CLEARED — ready to implement.
