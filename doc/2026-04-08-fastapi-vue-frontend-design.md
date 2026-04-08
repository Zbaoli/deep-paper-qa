# FastAPI + Vue 3 前端替代 Chainlit 设计

## 概述

用 FastAPI + SSE 后端 + Vue 3 SPA 前端替代 Chainlit，解决现有架构的胶水代码、前端不可定制、前后端耦合等问题。Agent 层（agent.py、pipelines、tools、prompts）完全不动。

## 设计决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 后端框架 | FastAPI + SSE | 异步原生，与 LangGraph 配合好 |
| 前端框架 | Vue 3 + Vite | 用户有 Vue 经验 |
| UI 组件库 | Naive UI | Vue 3 原生、中文友好、内置 chat/table/chart 组件 |
| 图表 | vue-echarts + ECharts | 比 Plotly 在 Vue 生态中集成更好 |
| 状态管理 | Pinia | Vue 3 官方推荐 |
| Markdown 渲染 | markdown-it | 轻量、可扩展 |
| 通信协议 | REST + SSE | 聊天用 SSE 流式，其他用 REST |

## 整体架构

```
┌─────────────────────────────────────────────────┐
│  Vue 3 SPA (Vite + Naive UI + ECharts)          │
│  ├─ /chat          聊天页面                      │
│  ├─ /explore       论文浏览/搜索                  │
│  └─ /dashboard     数据可视化                     │
└──────────────────┬──────────────────────────────┘
                   │ HTTP + SSE
┌──────────────────┴──────────────────────────────┐
│  FastAPI Backend                                 │
│  ├─ POST /api/chat          → SSE 流式响应       │
│  ├─ GET  /api/papers        → 论文列表/搜索      │
│  ├─ GET  /api/stats         → 统计数据           │
│  └─ GET  /api/conversations → 历史会话           │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────┴──────────────────────────────┐
│  LangGraph Agent (不变)                          │
│  tools: execute_sql, search_abstracts, ...       │
└─────────────────────────────────────────────────┘
```

## SSE 事件协议

### POST `/api/chat`

请求体：
```json
{"message": "用户消息", "thread_id": "uuid"}
```

响应：`text/event-stream`，每个事件一行 JSON：

```
event: route
data: {"category": "general", "label": "普通问答"}

event: tool_start
data: {"tool": "execute_sql", "input": {"sql": "SELECT ..."}, "run_id": "xxx"}

event: tool_end
data: {"tool": "execute_sql", "output": "...", "duration_ms": 120, "run_id": "xxx"}

event: token
data: {"content": "根据"}

event: chart
data: {"type": "echarts", "option": {...echarts option...}}

event: ask_user
data: {"question": "请确认研究计划...", "summary": "..."}

event: done
data: {"total_ms": 3200, "tool_calls": 2}

event: error
data: {"message": "处理失败: ..."}
```

关键设计：
- `chart` 是独立事件，前端收到后内联插入到消息流中
- `ask_user` 是独立事件，前端展示确认 UI
- `token` 事件支持所有管线流式输出
- 非流式管线把完整内容作为一个 `token` 事件发送

## 前端页面

### `/chat` — 聊天页面（主页面）

- 消息列表：用户消息 + AI 回复交替展示
- AI 消息内部支持：Markdown 渲染、内联 ECharts 图表、tool call 折叠面板
- research 管线的 `ask_user` 渲染为带按钮的确认卡片
- 路由分类标签显示在 AI 回复顶部
- 左侧栏：历史会话列表

### `/explore` — 论文浏览

- 搜索框 + 筛选条件（年份、会议、引用数范围）
- 论文列表（Naive UI DataTable，分页 + 排序）
- 点击论文展开摘要详情

### `/dashboard` — 数据可视化

- 统计卡片（总论文数、会议分布、年份分布）
- 图表区：各会议论文数量柱状图、年度趋势折线图

## 前端组件结构

```
frontend/src/
├── views/
│   ├── ChatView.vue
│   ├── ExploreView.vue
│   └── DashboardView.vue
├── components/
│   ├── chat/
│   │   ├── MessageList.vue     # 消息列表
│   │   ├── UserMessage.vue     # 用户消息气泡
│   │   ├── AiMessage.vue       # AI 回复（Markdown + 图表 + tool steps）
│   │   ├── ToolStep.vue        # 可折叠 tool call 展示
│   │   ├── AskUserCard.vue     # 研究管线确认卡片
│   │   └── ChatInput.vue       # 输入框 + 发送按钮
│   ├── explore/
│   │   ├── PaperTable.vue      # 论文表格
│   │   └── PaperFilter.vue     # 筛选条件
│   └── dashboard/
│       ├── StatCards.vue        # 统计卡片
│       └── TrendChart.vue      # ECharts 图表
├── composables/
│   ├── useChat.ts              # SSE 连接 + 消息状态管理
│   └── useApi.ts               # REST API 封装
├── stores/
│   └── chat.ts                 # Pinia store（会话列表、当前消息）
└── router/
    └── index.ts                # Vue Router 配置
```

## FastAPI 后端

### API 路由

| 路由 | 方法 | 说明 | 数据来源 |
|---|---|---|---|
| `/api/chat` | POST | 聊天 SSE 流 | LangGraph Agent |
| `/api/chat/{thread_id}/reply` | POST | ask_user 回复 | Agent 继续执行 |
| `/api/conversations` | GET | 历史会话列表 | conversation_logger |
| `/api/conversations/{id}` | GET | 单个会话消息 | conversation_logger |
| `/api/papers` | GET | 论文搜索/列表 | PostgreSQL 直查 |
| `/api/papers/{id}` | GET | 论文详情 | PostgreSQL |
| `/api/stats` | GET | 统计数据 | PostgreSQL 聚合 |

### 后端文件

| 文件 | 动作 |
|---|---|
| `app.py` | 删除（Chainlit 入口） |
| `api.py` | 新建（FastAPI 入口） |
| `routers/chat.py` | 新建（聊天路由 + SSE 事件转换） |
| `routers/papers.py` | 新建（论文浏览路由） |
| `routers/stats.py` | 新建（统计数据路由） |

### ask_user 交互方案

1. Agent 执行到 `ask_user` 时，SSE 发出 `ask_user` 事件，SSE 流暂停（async 等待）
2. 前端展示确认卡片，用户回复后 POST `/api/chat/{thread_id}/reply`
3. 后端通过 `asyncio.Event` 唤醒暂停的 SSE 流，Agent 继续执行
4. 后续事件继续在同一个 SSE 连接中推送

### 不变的部分

- `agent.py` — 主图构建
- `pipelines/` — 所有管线
- `tools/` — 所有工具
- `prompts.py`
- `config.py`（仅新增 CORS 配置）
- `conversation_logger.py`

## 项目结构

```
deep_paper_qa/
├── src/deep_paper_qa/        # Python 后端
│   ├── api.py                # FastAPI 入口（替代 app.py）
│   ├── routers/
│   │   ├── chat.py
│   │   ├── papers.py
│   │   └── stats.py
│   ├── agent.py              # 不变
│   ├── pipelines/            # 不变
│   ├── tools/                # 不变
│   └── ...
├── frontend/                 # Vue 3 前端
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── views/
│       ├── components/
│       ├── composables/
│       ├── stores/
│       └── router/
├── pyproject.toml
└── docker/
```

## 依赖变更

**移除：** `chainlit>=2.0`
**新增：** `fastapi>=0.115`, `uvicorn>=0.34`, `sse-starlette>=2.0`

## 开发模式

```bash
# 终端 1：后端
uv run uvicorn deep_paper_qa.api:app --reload --port 8000

# 终端 2：前端
cd frontend && npm run dev    # Vite dev server :5173
```

Vite 配置代理 `/api` 到后端。

## 生产部署

- **简单方案**：`npm run build` → `frontend/dist/`，FastAPI 用 `StaticFiles` 托管
- **正式方案**：Nginx 反代静态文件 + `/api` 到 FastAPI

## 迁移策略

分两步，确保任何时候都有可用版本：

1. **先建后端 API 层**：新建 `api.py` + `routers/`，与 `app.py` 并存
2. **再建前端**：Vue 项目对接 API，功能对齐后删除 `app.py` 和 `chainlit` 依赖
