# 六分类路由架构设计

## 背景

当前系统是单一 ReAct Agent，所有问题（普通问答、深度研究）走同一条路径，深度研究通过 `/research` 前缀 + prompt 条件分支实现。问题：

1. 路由靠用户手动加前缀，不是系统自动判断
2. 深度研究的多步流程全靠 prompt 约束，LLM 容易跳步
3. 无显式状态管理，中间结果在消息历史中隐式维护

## 目标

将单一 Agent 改造为 **路由节点 + 6 条独立 pipeline** 的 LangGraph 显式图，自动分类用户问题并路由到对应 subgraph。

## 架构

```
用户消息
  │
  ▼
路由节点（LLM 分类）
  ├─ reject     → 拒答（模板回复）
  ├─ general    → ReAct subgraph
  ├─ research   → DeepResearch subgraph
  ├─ reading    → PaperReading subgraph（P2，暂占位）
  ├─ compare    → PaperCompare subgraph（P2，暂占位）
  └─ trend      → TrendAnalysis subgraph
```

## 各 Pipeline 详细设计

### 路由节点

- **实现方式**：LLM structured output，返回 `{"category": "general" | "research" | "reading" | "compare" | "trend" | "reject"}`
- **模型**：复用现有 `settings.llm_model`，用轻量 prompt + few-shot 示例
- **输入**：用户当前消息
- **输出**：分类标签

路由 prompt 需包含每个类别的判断标准和 2-3 个 few-shot 示例（参见 `doc/2026-04-08-agentic-rag.md` 中的示例）。

分类判断标准：

| 类别 | 判断标准 |
|------|---------|
| reject | 与 AI 论文无关 |
| general | 1-4 次工具调用可回答（统计、检索、混合） |
| research | 可拆解为 3+ 个子问题，需要结构化研究报告 |
| reading | 针对一篇特定论文的深入解读 |
| compare | 针对两篇+论文的多维度对比 |
| trend | 时间维度的统计趋势 + 各阶段代表作 |

### 1. 拒答（reject）

- 不调用 LLM，直接返回模板字符串："我是 AI 科研论文问答助手，只能回答与 AI 论文相关的问题。"
- 零 token 消耗。

### 2. 普通问题（general → ReAct subgraph）

- 基本沿用现有 `create_react_agent` 逻辑
- 从 prompt 中**移除**深度研究相关指令，保持 prompt 精简
- 工具不变：`execute_sql` + `search_abstracts`
- `recursion_limit`: 30

### 3. 深度研究（research → DeepResearch subgraph）

从 prompt 约束改为 LangGraph 显式节点：

```
clarify（澄清追问，最多 3 轮）
  → plan（生成研究简报，拆解 3-5 个子问题，用户确认）
  → research_loop（循环：执行子问题检索 → 压缩中间结果 → ask_user 确认）
  → report（综合所有中间结果，生成结构化报告）
```

**状态**（TypedDict）：
- `messages`: 消息历史
- `plan`: 研究计划（子问题列表）
- `current_step`: 当前执行的子问题索引
- `findings`: 各子问题的压缩结果
- `clarify_count`: 已追问次数

**工具**：`execute_sql` + `search_abstracts` + `ask_user`

**用户交互**：所有需要用户输入的节点（clarify、plan 确认、research_loop 阶段汇报）统一通过 `ask_user` 工具实现，与现有 Chainlit `AskUserMessage` 集成。

**约束**：
- 每个子问题最多 2 次检索工具调用
- 总计最多 15 次工具调用（不含 ask_user）
- `recursion_limit`: 50

### 4. 论文精读（reading → PaperReading subgraph）

**P2，暂返回占位消息**："论文精读功能开发中，敬请期待。目前可以使用普通问答查询论文摘要信息。"

未来实现需要：PDF 下载解析能力，分章节提取 + 逐段总结流程。

### 5. 论文对比（compare → PaperCompare subgraph）

**P2，暂返回占位消息**："论文对比功能开发中，敬请期待。目前可以使用普通问答查询并对比论文摘要。"

未来实现需要：全文 PDF 支持，多维度对齐对比（问题定义、方法、实验、结果）。

### 6. 趋势分析（trend → TrendAnalysis subgraph）

固定流程，不使用 ReAct 自主决策：

```
generate_sql（根据用户问题生成按年统计 SQL）
  → execute_stats（执行 SQL，获取数量趋势数据）
  → identify_phases（根据数据识别增长/平稳/下降阶段）
  → search_representatives（为每个阶段检索代表性论文）
  → synthesize（综合统计数据 + 代表作，生成趋势分析报告）
```

**状态**（TypedDict）：
- `messages`: 消息历史
- `query_topic`: 提取的研究主题
- `stats_data`: SQL 统计结果
- `phases`: 识别出的阶段列表
- `representative_papers`: 各阶段代表作
- `report`: 最终报告

**工具**：`execute_sql` + `search_abstracts`

## 文件改动范围

| 文件 | 改动 |
|------|------|
| `src/deep_paper_qa/agent.py` | 重写：构建主图（路由 + 各 subgraph） |
| `src/deep_paper_qa/prompts.py` | 重写：拆分为路由 prompt + 各 pipeline 独立 prompt |
| `src/deep_paper_qa/app.py` | 简化：移除 `/research` 手动前缀检测逻辑，路由由 graph 自动处理 |
| `src/deep_paper_qa/pipelines/` | 新增目录，每个 pipeline 独立文件 |
| `src/deep_paper_qa/pipelines/__init__.py` | 新增 |
| `src/deep_paper_qa/pipelines/router.py` | 新增：路由节点实现 |
| `src/deep_paper_qa/pipelines/general.py` | 新增：ReAct subgraph |
| `src/deep_paper_qa/pipelines/research.py` | 新增：DeepResearch subgraph |
| `src/deep_paper_qa/pipelines/reading.py` | 新增：PaperReading 占位 |
| `src/deep_paper_qa/pipelines/compare.py` | 新增：PaperCompare 占位 |
| `src/deep_paper_qa/pipelines/trend.py` | 新增：TrendAnalysis subgraph |
| `src/deep_paper_qa/models.py` | 扩展：新增各 pipeline 的 State TypedDict |
| `tests/test_router.py` | 新增：路由分类准确性测试 |
| `tests/test_agent.py` | 更新：适配新架构 |

## 不变的部分

- `config.py`、`conversation_logger.py`、`logging_setup.py` 不改动
- `tools/` 目录下所有工具实现不改动（`execute_sql`、`search_abstracts`、`vector_search`、`ask_user`、`sql_utils`）
- 数据库 schema 不改动
- Chainlit UI 框架不改动（仍通过 `astream_events` 流式输出）

## 非目标

- 不引入新的外部依赖（LangGraph 已在使用）
- 不改变现有工具的接口和行为
- 不实现全文 PDF 解析（P2 scope）
- 不改变数据库 schema
