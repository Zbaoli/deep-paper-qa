# DeepAgents 重写实验设计

> 分支：`experiment/deepagents`
> 日期：2026-04-08
> 目标：用 LangChain DeepAgents 替换手动路由+多管线架构，让 agent 自主规划调度，对比效果

## 1. 背景与目标

当前架构为 6 路路由 + 5 条专用管线（general、research、trend、reading、compare），
每条管线有独立的状态管理和流程控制。这次实验：

- **去掉手动路由**，用 `create_deep_agent()` 构建单一 agent
- **保留全部工具 + 领域知识 prompt**，但不约束 agent 行为
- **新增通用可视化工具**，替代 trend 管线的硬编码柱状图
- **用现有 eval 框架 (30 题) 对比**两个分支的得分

## 2. 方案选择

评估了三种方案，选定 **方案 B：DeepAgents + 丰富 system prompt**。

| 方案 | 描述 | 不选理由 |
|------|------|----------|
| A 纯 DeepAgents 最小 prompt | 只提供工具和极简 prompt | 丢失关键领域知识（schema、数据质量），eval 分数必然低 |
| **B DeepAgents + 领域知识** | 单一 agent + 完整领域知识 prompt | ✅ 选定 |
| C DeepAgents + middleware | 用中间件重建管线逻辑 | 工作量大，偏离"自由发挥"实验目的 |

## 3. 整体架构

### 现有架构
```
Chainlit → Router(6路) → {General|Research|Trend|Reading|Compare|Reject} → 各自管线
```

### 新架构
```
Chainlit → DeepAgent(单一 agent，自主规划) → 7 个工具
```

DeepAgents 内置能力：

| 内置能力 | 是否启用 | 理由 |
|----------|----------|------|
| Planning（write_todos） | ✅ 启用 | 替代 research 管线的手动规划 |
| Filesystem backend | ✅ 启用 | 多步研究时卸载中间结果 |
| Sub-agents（task） | ✅ 启用 | 复杂问题自动委派子任务 |
| Persistent memory | ❌ 不启用 | 实验阶段不需要跨会话记忆 |

## 4. 工具清单

| 工具 | 来源 | 说明 |
|------|------|------|
| execute_sql | 现有，原样复用 | Text-to-SQL，SELECT only |
| search_abstracts | 现有，原样复用 | 全文+向量混合搜索 |
| search_arxiv | 现有，原样复用 | arXiv API 搜索 |
| search_semantic_scholar | 现有，原样复用 | Semantic Scholar API |
| search_web | 现有，原样复用 | Tavily 网页搜索 |
| ask_user | 现有，原样复用 | 仅用于歧义澄清（prompt 约束） |
| generate_chart | **新建** | 通用 Plotly 可视化 |

## 5. generate_chart 工具设计

```python
@tool
async def generate_chart(
    chart_type: str,    # bar/line/scatter/pie/heatmap/area/box
    data: dict,         # {"x": [...], "y": [...]} 或 {"labels": [...], "values": [...]}
    title: str,
    x_label: str = "",
    y_label: str = "",
) -> str:
    """根据数据生成 Plotly 图表，返回 <!--plotly:{json}--> 格式。"""
```

要点：
- 支持 7 种图表类型，agent 根据数据特征自主选择
- 输出 `<!--plotly:{json}-->` 格式，复用 app.py 现有的图表渲染逻辑
- 内部用 `plotly.graph_objects` 构建，统一中文友好的默认样式
- 数据校验：x/y 长度一致性检查，不合法时返回错误信息

## 6. System Prompt 策略

从现有 `prompts.py` 提取领域知识，合并为单一 SYSTEM_PROMPT：

**包含：**
- 数据库 schema（papers 表字段、类型、约束）
- SQL 编写规范（SELECT only、年份范围 2020-2025、directions 不可用）
- 关键词扩展规则（RAG → retrieval augmented generation 等）
- 工具优先级提示（本地 DB 优先，外部搜索补充）
- ask_user 仅用于问题歧义时澄清
- generate_chart 使用说明和输出格式

**不包含：**
- 路由分类逻辑
- 各管线的步骤流程
- 输出格式硬性要求

## 7. app.py 适配

### 改动点

1. **Agent 初始化**：导入 `create_deep_agent` 返回的图，去掉多子图构建
2. **流式输出**：去掉按 RouteCategory 区分流式/非流式的分支，统一走 `astream_events()`
3. **工具展示**：新增 DeepAgents 内置工具的 UI 展示
   - `write_todos` → "📋 制定计划"步骤
   - `task` → "🔀 委派子任务"步骤
   - `generate_chart` → 复用现有 Plotly 渲染
4. **删除**：路由分流逻辑、pipeline 特有的 state 提取和消息覆盖

### 不变
- ask_user 通过 `cl.AskUserMessage` 的路径
- conversation_logger 日志记录
- 会话级 checkpointer

## 8. Eval 适配

- 导入新 agent，调用接口不变（`ainvoke({"messages": [...]})`)
- eval 时移除 ask_user 工具或 mock 返回空字符串
- 去掉 RouteCategory 相关的分类统计（如有）
- 对比方式：main 分支跑基线 → experiment/deepagents 跑实验 → 逐题对比

## 9. 文件变更总览

| 操作 | 文件 | 说明 |
|------|------|------|
| 重写 | `agent.py` | 81 行 → ~30 行，`create_deep_agent()` |
| 新建 | `tools/generate_chart.py` | 通用 Plotly 可视化工具 |
| 重写 | `prompts.py` | 多个 prompt → 单一 SYSTEM_PROMPT |
| 修改 | `app.py` | 去掉路由分流，统一流式，适配内置工具事件 |
| 修改 | `models.py` | 删除 RouteCategory、ResearchState、TrendState |
| 修改 | `eval/run_eval.py` | 适配新 agent，mock ask_user |
| 修改 | `pyproject.toml` | 添加 `deepagents` 依赖 |
| 删除 | `pipelines/router.py` | 不再需要 |
| 删除 | `pipelines/general.py` | 不再需要 |
| 删除 | `pipelines/research.py` | 不再需要 |
| 删除 | `pipelines/trend.py` | 不再需要 |
| 删除 | `pipelines/reading.py` | 不再需要 |
| 删除 | `pipelines/compare.py` | 不再需要 |

不变：`tools/execute_sql.py`、`search_abstracts.py`、`search_arxiv.py`、`search_semantic_scholar.py`、`search_web.py`、`ask_user.py`、`config.py`、`conversation_logger.py`

## 10. 风险点

1. DeepAgents 的 `write_todos`/`task` 内置工具事件格式需要实际调试确定 Chainlit 展示逻辑
2. `generate_chart` 的 `<!--plotly:{json}-->` 格式需和 app.py 的解析正则对齐
3. eval 中 mock ask_user 的策略需验证不影响 agent 行为
4. DeepAgents 对 OpenAI 兼容 API 的支持程度需要验证（项目用非 OpenAI 的 LLM 服务）
