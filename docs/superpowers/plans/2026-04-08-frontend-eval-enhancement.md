# 前端体验优化 + 评测更新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 适配新六分类路由架构的前端展示优化（路由可视化、进度指示、趋势图表）和评测系统更新

**Architecture:** app.py 增加路由事件捕获和展示逻辑；research.py 各节点输出进度 AIMessage；trend.py 生成 plotly 图表 JSON 嵌入回复；评测脚本和 dashboard 扩展支持 6 种题型

**Tech Stack:** Chainlit (cl.Step, cl.Plotly), plotly, LangGraph astream_events

---

## 文件结构

```
src/deep_paper_qa/
├── app.py                      # 修改：路由可视化 + 进度捕获 + 欢迎语更新
├── agent.py                    # 修改：router_node 输出分类标签到 messages
├── pipelines/
│   ├── research.py             # 修改：各节点增加进度 AIMessage
│   └── trend.py                # 修改：synthesize_node 生成 plotly 图表
eval/
├── run_eval.py                 # 修改：build_graph + 新题型路由判断
├── questions.jsonl             # 修改：追加 11 题（trend/research/reject）
├── judge_prompt.py             # 修改：新增 trend/research 评分重点
└── dashboard.html              # 修改：新增题型颜色 + 筛选器 + pipeline 列
pyproject.toml                  # 修改：新增 plotly 依赖
```

---

### Task 1: 欢迎语和 Starters 更新

**Files:**
- Modify: `src/deep_paper_qa/app.py:24-43`

- [ ] **Step 1: 更新 Starters 和欢迎语**

在 `src/deep_paper_qa/app.py` 中，替换 `set_starters` 和 `on_chat_start` 函数：

将：
```python
@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    """提供示例问题，引导新用户快速上手"""
    return [
        cl.Starter(label="会议论文统计", message="各会议论文数量是多少？"),
        cl.Starter(label="RAG 研究趋势", message="RAG 最近几年的研究趋势怎么样？"),
        cl.Starter(label="高引论文推荐", message="推荐一些高引用的大语言模型论文"),
        cl.Starter(label="作者论文查询", message="Yann LeCun 发了哪些论文？"),
    ]
```

替换为：
```python
@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    """提供示例问题，引导新用户快速上手"""
    return [
        cl.Starter(label="会议论文统计", message="各会议论文数量是多少？"),
        cl.Starter(label="RAG 研究趋势", message="RAG 近三年的发展趋势怎么样？"),
        cl.Starter(label="深度调研", message="总结 2023-2025 年 LLM Agent 的研究脉络"),
        cl.Starter(label="高引论文推荐", message="推荐一些高引用的大语言模型论文"),
    ]
```

将欢迎语：
```python
    await cl.Message(
        content="你好！我是 AI 科研论文问答助手。可以问我关于论文的统计信息或内容问题。"
    ).send()
```

替换为：
```python
    await cl.Message(
        content="你好！我是 AI 科研论文问答助手，支持论文统计查询、内容检索、研究趋势分析和深度调研。"
    ).send()
```

- [ ] **Step 2: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/app.py`
Expected: 无错误

- [ ] **Step 3: 提交**

```bash
git add src/deep_paper_qa/app.py
git commit -m "feat: 更新欢迎语和 Starters 体现新能力"
```

---

### Task 2: 路由过程可视化

**Files:**
- Modify: `src/deep_paper_qa/agent.py:25-30`
- Modify: `src/deep_paper_qa/app.py:66-74`

- [ ] **Step 1: 修改 router_node 输出分类标签到 messages**

在 `src/deep_paper_qa/agent.py` 中，修改 `router_node` 函数，让它把分类结果写入一条 AIMessage（带 metadata 标记），供前端捕获：

将：
```python
async def router_node(state: MainState) -> dict:
    """路由节点：提取用户最新消息并分类"""
    last_msg = state["messages"][-1].content
    category = await classify_question(last_msg)
    logger.info("路由决策 | category={}", category.value)
    return {"category": category.value}
```

替换为：
```python
# 路由分类标签映射
CATEGORY_LABELS = {
    "reject": "拒答",
    "general": "普通问答",
    "research": "深度研究",
    "reading": "论文精读",
    "compare": "论文对比",
    "trend": "趋势分析",
}


async def router_node(state: MainState) -> dict:
    """路由节点：提取用户最新消息并分类"""
    last_msg = state["messages"][-1].content
    category = await classify_question(last_msg)
    label = CATEGORY_LABELS.get(category.value, category.value)
    logger.info("路由决策 | category={} | label={}", category.value, label)
    return {"category": category.value}
```

- [ ] **Step 2: 修改 app.py 在回答前展示路由结果**

在 `src/deep_paper_qa/app.py` 的 `on_message` 函数中，在 `final_msg` 发送前，插入路由可视化逻辑。在事件循环之前加入路由展示：

将 `on_message` 中的：
```python
    final_msg = cl.Message(content="")
    await final_msg.send()

    try:
        async for event in _graph.astream_events(
```

替换为：
```python
    # 路由分类标签映射
    category_labels = {
        "reject": "拒答",
        "general": "普通问答",
        "research": "深度研究",
        "reading": "论文精读",
        "compare": "论文对比",
        "trend": "趋势分析",
    }
    router_shown = False

    final_msg = cl.Message(content="")
    await final_msg.send()

    try:
        async for event in _graph.astream_events(
```

然后在事件循环内，`on_tool_start` 之前添加路由事件捕获。在 `kind = event.get("event", "")` 后面、`if kind == "on_tool_start":` 前面，插入：

```python
            # 路由节点完成时展示分类结果
            if kind == "on_chain_end" and name == "router" and not router_shown:
                try:
                    output = event.get("data", {}).get("output", {})
                    cat = output.get("category", "")
                    if cat:
                        label = category_labels.get(cat, cat)
                        step = cl.Step(name="路由分类", type="tool")
                        step.output = f"问题类型：{label}"
                        await step.send()
                        router_shown = True
                except Exception:
                    pass
```

- [ ] **Step 3: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/agent.py src/deep_paper_qa/app.py`
Expected: 无错误

- [ ] **Step 4: 提交**

```bash
git add src/deep_paper_qa/agent.py src/deep_paper_qa/app.py
git commit -m "feat: 路由过程可视化，前端展示分类结果"
```

---

### Task 3: 深度研究进度指示

**Files:**
- Modify: `src/deep_paper_qa/pipelines/research.py`

在各节点执行时输出进度消息。由于 astream_events 会捕获所有 AIMessage，我们在各节点返回的 messages 中增加进度提示，前端自动通过流式输出展示。

- [ ] **Step 1: 修改 clarify_node 增加进度提示**

在 `src/deep_paper_qa/pipelines/research.py` 中，修改 `clarify_node` 的返回：

将：
```python
    return {
        "messages": [AIMessage(content=result.content)],
        "clarify_count": new_count,
    }
```

替换为：
```python
    return {
        "messages": [AIMessage(content=f"**[澄清问题 {new_count}/3]**\n\n{result.content}")],
        "clarify_count": new_count,
    }
```

- [ ] **Step 2: 修改 plan_node 增加进度提示**

在 `plan_node` 函数末尾，修改返回：

将：
```python
    logger.info("深度研究 | 研究计划: {} 个子问题", len(plan))
    return {"plan": plan, "current_step": 0}
```

替换为：
```python
    logger.info("深度研究 | 研究计划: {} 个子问题", len(plan))
    plan_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(plan))
    return {
        "plan": plan,
        "current_step": 0,
        "messages": [AIMessage(content=f"**[研究计划]** 共 {len(plan)} 个子问题：\n\n{plan_text}")],
    }
```

- [ ] **Step 3: 修改 research_step_node 增加进度提示**

在 `research_step_node` 函数中，修改 `new_findings` 赋值后的返回：

将：
```python
    return {
        "findings": new_findings,
        "current_step": step_idx + 1,
    }
```

替换为：
```python
    total = len(state["plan"])
    return {
        "findings": new_findings,
        "current_step": step_idx + 1,
        "messages": [AIMessage(content=f"**[子问题 {step_idx + 1}/{total}]** {current_question}\n\n{finding}")],
    }
```

- [ ] **Step 4: 修改 report_node 增加进度提示**

在 `report_node` 函数中，修改返回：

将：
```python
    return {"messages": [AIMessage(content=report)]}
```

替换为：
```python
    return {"messages": [AIMessage(content=f"**[研究报告]**\n\n{report}")]}
```

- [ ] **Step 5: 运行现有测试确认不破坏**

Run: `uv run pytest tests/test_research.py -v`
Expected: 全部 PASS（进度前缀不影响测试逻辑）

- [ ] **Step 6: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/pipelines/research.py`
Expected: 无错误

- [ ] **Step 7: 提交**

```bash
git add src/deep_paper_qa/pipelines/research.py
git commit -m "feat: 深度研究各节点增加进度指示"
```

---

### Task 4: 趋势分析数据可视化

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/deep_paper_qa/pipelines/trend.py`

- [ ] **Step 1: 添加 plotly 依赖**

在 `pyproject.toml` 的 `dependencies` 列表中追加 `"plotly>=6.0"`：

将：
```toml
dependencies = [
    "langgraph>=0.3",
    "langchain-openai>=0.3",
    "langchain-core>=0.3",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "chainlit>=2.0",
    "loguru>=0.7",
    "python-dotenv>=1.0",
    "asyncpg>=0.30",
    "aiohttp>=3.9",
]
```

替换为：
```toml
dependencies = [
    "langgraph>=0.3",
    "langchain-openai>=0.3",
    "langchain-core>=0.3",
    "pydantic>=2.0",
    "pydantic-settings>=2.0",
    "chainlit>=2.0",
    "loguru>=0.7",
    "python-dotenv>=1.0",
    "asyncpg>=0.30",
    "aiohttp>=3.9",
    "plotly>=6.0",
]
```

- [ ] **Step 2: 安装依赖**

Run: `uv sync --all-extras`

- [ ] **Step 3: 修改 trend.py 的 execute_stats_node 解析统计数据**

在 `src/deep_paper_qa/pipelines/trend.py` 中，修改 `execute_stats_node` 增加结构化数据解析。同时在 `TrendState` 的实际使用中，我们需要把原始统计数据保留供图表使用。

在文件顶部追加 import：
```python
import re
```

修改 `execute_stats_node`：

将：
```python
async def execute_stats_node(state: TrendState) -> dict:
    """执行统计 SQL"""
    sql = state["stats_data"]  # 上一步存的是 SQL
    result = await execute_sql.ainvoke({"sql": sql})
    logger.info("趋势分析 | 统计结果: {}", result[:200])
    return {"stats_data": result}
```

替换为：
```python
async def execute_stats_node(state: TrendState) -> dict:
    """执行统计 SQL"""
    sql = state["stats_data"]  # 上一步存的是 SQL
    result = await execute_sql.ainvoke({"sql": sql})
    logger.info("趋势分析 | 统计结果: {}", result[:200])
    return {"stats_data": result}


def _parse_year_counts(stats_text: str) -> list[tuple[int, int]]:
    """从统计结果文本中提取 (年份, 数量) 列表"""
    pairs: list[tuple[int, int]] = []
    for line in stats_text.split("\n"):
        match = re.match(r"\s*(\d{4})\s*\|\s*(\d+)", line)
        if match:
            pairs.append((int(match.group(1)), int(match.group(2))))
    return sorted(pairs)
```

- [ ] **Step 4: 修改 synthesize_node 生成 plotly 图表 JSON**

修改 `synthesize_node`：

将：
```python
    logger.info("趋势分析 | 报告生成完成，长度={}", len(report))
    return {"report": report, "messages": [AIMessage(content=report)]}
```

替换为：
```python
    # 生成 plotly 图表 JSON
    chart_json = ""
    year_counts = _parse_year_counts(state["stats_data"])
    if year_counts:
        import plotly.graph_objects as go

        years = [str(y) for y, _ in year_counts]
        counts = [c for _, c in year_counts]
        fig = go.Figure(data=[go.Bar(x=years, y=counts, marker_color="#3b82f6")])
        fig.update_layout(
            title=f"{state['query_topic']} — 论文数量趋势",
            xaxis_title="年份",
            yaxis_title="论文数量",
            template="plotly_dark",
            height=400,
        )
        chart_json = fig.to_json()

    logger.info("趋势分析 | 报告生成完成，长度={} | 含图表={}", len(report), bool(chart_json))
    # 将图表 JSON 嵌入 report 的 metadata，供前端渲染
    content = report
    if chart_json:
        content = f"<!--plotly:{chart_json}-->\n\n{report}"
    return {"report": report, "messages": [AIMessage(content=content)]}
```

- [ ] **Step 5: 修改 app.py 捕获 plotly 标记并渲染图表**

在 `src/deep_paper_qa/app.py` 的事件循环中，`on_chat_model_stream` 分支后、`await final_msg.update()` 前，修改 final_msg 后处理逻辑。

在 `await final_msg.update()` 这一行之前，插入：

```python
        # 处理趋势分析图表
        if "<!--plotly:" in final_msg.content:
            import re as _re

            plotly_match = _re.search(r"<!--plotly:(.*?)-->", final_msg.content, _re.DOTALL)
            if plotly_match:
                chart_json = plotly_match.group(1)
                final_msg.content = _re.sub(
                    r"<!--plotly:.*?-->\n*", "", final_msg.content, flags=_re.DOTALL
                )
                try:
                    import plotly.io as pio

                    fig = pio.from_json(chart_json)
                    elements = [cl.Plotly(name="趋势图", figure=fig, display="inline")]
                    final_msg.elements = elements
                except Exception as plot_err:
                    logger.warning("Plotly 图表渲染失败: {}", plot_err)

```

- [ ] **Step 6: 运行现有测试确认不破坏**

Run: `uv run pytest tests/test_trend.py -v`
Expected: 全部 PASS

- [ ] **Step 7: 运行 lint**

Run: `uv run ruff check src/deep_paper_qa/pipelines/trend.py src/deep_paper_qa/app.py`
Expected: 无错误

- [ ] **Step 8: 提交**

```bash
git add pyproject.toml src/deep_paper_qa/pipelines/trend.py src/deep_paper_qa/app.py
git commit -m "feat: 趋势分析数据可视化（plotly 柱状图）"
```

---

### Task 5: 评测脚本适配新架构

**Files:**
- Modify: `eval/run_eval.py`
- Modify: `eval/questions.jsonl`
- Modify: `eval/judge_prompt.py`

- [ ] **Step 1: 修改 run_eval.py 导入**

在 `eval/run_eval.py` 中：

将第 14 行：
```python
from deep_paper_qa.agent import build_agent
```

替换为：
```python
from deep_paper_qa.agent import build_graph
```

将第 255 行：
```python
    agent, checkpointer = build_agent()
```

替换为：
```python
    agent, checkpointer = build_graph()
```

- [ ] **Step 2: 扩展路由正确性判断**

在 `eval/run_eval.py` 中，修改 `eval_one` 函数的路由正确性判断逻辑（约第 81-103 行）。

将：
```python
    if q_type == "sql":
        tool_correct = "execute_sql" in called_set or no_tool_but_reasonable
    elif q_type == "content":
        tool_correct = (
            bool(called_set & {"vector_search", "search_abstracts"})
            or no_tool_but_reasonable
        )
    elif q_type == "mixed":
        expected = set(q.get("expected_tools", []))
        content_tools = {"vector_search", "search_abstracts"}
        # search_abstracts/vector_search 带非空 where 参数也视为完成了筛选意图
        content_with_where = any(
            td["name"] in content_tools
            and "'where':" in td["input"]
            and "'where': ''" not in td["input"]
            and "'where': \"\"" not in td["input"]
            for td in tool_details
        )
        has_sql = (
            "execute_sql" in called_set or content_with_where
        ) if "execute_sql" in expected else True
        has_content = bool(called_set & content_tools) if expected & content_tools else True
        tool_correct = has_sql and has_content
```

替换为：
```python
    if q_type == "sql":
        tool_correct = "execute_sql" in called_set or no_tool_but_reasonable
    elif q_type == "content":
        tool_correct = (
            bool(called_set & {"vector_search", "search_abstracts"})
            or no_tool_but_reasonable
        )
    elif q_type == "mixed":
        expected = set(q.get("expected_tools", []))
        content_tools = {"vector_search", "search_abstracts"}
        content_with_where = any(
            td["name"] in content_tools
            and "'where':" in td["input"]
            and "'where': ''" not in td["input"]
            and "'where': \"\"" not in td["input"]
            for td in tool_details
        )
        has_sql = (
            "execute_sql" in called_set or content_with_where
        ) if "execute_sql" in expected else True
        has_content = bool(called_set & content_tools) if expected & content_tools else True
        tool_correct = has_sql and has_content
    elif q_type == "trend":
        # 趋势分析需要同时用 SQL 统计和内容检索
        tool_correct = "execute_sql" in called_set and bool(
            called_set & {"search_abstracts", "vector_search"}
        )
    elif q_type == "research":
        # 深度研究需要多次工具调用
        tool_correct = len(tools_called) >= 3
    elif q_type == "reject":
        # 拒答不应调用任何工具
        tool_correct = len(called_set) == 0
```

- [ ] **Step 3: 扩展报告生成的题型分组**

在 `eval/run_eval.py` 的 `_generate_report` 函数中：

将第 199 行：
```python
        for t in ["sql", "content", "mixed"]:
```

替换为：
```python
        for t in ["sql", "content", "mixed", "trend", "research", "reject"]:
```

将第 235 行（路由详情部分）同样替换：
```python
        for t in ["sql", "content", "mixed"]:
```

替换为：
```python
        for t in ["sql", "content", "mixed", "trend", "research", "reject"]:
```

- [ ] **Step 4: 追加新题型到 questions.jsonl**

在 `eval/questions.jsonl` 末尾追加以下 11 行：

```
{"id": 66, "type": "trend", "question": "RAG 近三年的发展趋势怎么样？", "expected_tools": ["execute_sql", "search_abstracts"]}
{"id": 67, "type": "trend", "question": "知识蒸馏这个方向是在升温还是降温？", "expected_tools": ["execute_sql", "search_abstracts"]}
{"id": 68, "type": "trend", "question": "2020-2025 年 GAN 相关论文的数量变化和研究重心转移", "expected_tools": ["execute_sql", "search_abstracts"]}
{"id": 69, "type": "trend", "question": "Transformer 架构改进的研究热度变化", "expected_tools": ["execute_sql", "search_abstracts"]}
{"id": 70, "type": "trend", "question": "多模态大模型这个方向近几年论文数量趋势如何？", "expected_tools": ["execute_sql", "search_abstracts"]}
{"id": 71, "type": "research", "question": "调研 AI for Science 在蛋白质结构预测方向的最新进展", "expected_tools": ["search_abstracts"]}
{"id": 72, "type": "research", "question": "总结 2023-2025 年 LLM Agent 的研究脉络，包括关键论文和技术路线", "expected_tools": ["search_abstracts"]}
{"id": 73, "type": "research", "question": "梳理 text-to-image 从 GAN 到 diffusion 的技术演进，给出综述报告", "expected_tools": ["search_abstracts"]}
{"id": 74, "type": "reject", "question": "今天天气怎么样？"}
{"id": 75, "type": "reject", "question": "帮我写一段 Python 排序代码"}
{"id": 76, "type": "reject", "question": "帮我润色一下我的论文摘要"}
```

- [ ] **Step 5: 更新 judge_prompt.py 新增题型评分重点**

在 `eval/judge_prompt.py` 的 `JUDGE_SYSTEM_PROMPT` 中，找到 `## 按题型的评分重点` 部分：

将：
```python
## 按题型的评分重点

- **sql 题型**：accuracy 权重最高（统计数据必须准确），citation 看数据引用而非论文引用，efficiency 期望 1-2 次调用
- **content 题型**：accuracy 和 citation 权重最高（论文信息必须来自工具数据），efficiency 期望 1-3 次调用
- **mixed 题型**：综合评估，既看统计数据准确性也看内容引用质量，efficiency 期望 2-4 次调用
```

替换为：
```python
## 按题型的评分重点

- **sql 题型**：accuracy 权重最高（统计数据必须准确），citation 看数据引用而非论文引用，efficiency 期望 1-2 次调用
- **content 题型**：accuracy 和 citation 权重最高（论文信息必须来自工具数据），efficiency 期望 1-3 次调用
- **mixed 题型**：综合评估，既看统计数据准确性也看内容引用质量，efficiency 期望 2-4 次调用
- **trend 题型**：accuracy 侧重统计数据准确性（按年数量必须正确），completeness 看是否覆盖各阶段代表作，efficiency 期望 3-6 次调用（SQL 统计 + 分阶段检索）
- **research 题型**：completeness 权重最高（是否覆盖了问题的多个方面），clarity 侧重报告结构是否清晰，citation 要求每个子问题都有论文支撑，efficiency 期望 5-10 次调用
- **reject 题型**：accuracy 看是否正确拒绝（不编造论文信息），efficiency 期望 0 次调用，completeness 看拒绝后是否给出引导建议
```

- [ ] **Step 6: 运行 lint**

Run: `uv run ruff check eval/run_eval.py eval/judge_prompt.py`
Expected: 无错误

- [ ] **Step 7: 提交**

```bash
git add eval/run_eval.py eval/questions.jsonl eval/judge_prompt.py
git commit -m "feat: 评测脚本适配新架构，新增 trend/research/reject 题型"
```

---

### Task 6: 评测 Dashboard 更新

**Files:**
- Modify: `eval/dashboard.html`

这是一个大型单文件 HTML（937 行），需要修改 CSS 变量、筛选器、表格列。

- [ ] **Step 1: 添加新题型 CSS 颜色变量**

在 `eval/dashboard.html` 的 CSS `:root` 部分（约第 27-29 行），在 `--mixed-color` 之后追加：

```css
    --trend-color: #60a5fa;
    --research-color: #a78bfa;
    --reject-color: #6b7280;
```

- [ ] **Step 2: 添加新题型 badge 和 pill 样式**

在 `.type-badge.mixed` 之后（约第 177 行）追加：

```css
  .type-badge.trend { background: rgba(96,165,250,0.15); color: var(--trend-color); }
  .type-badge.research { background: rgba(167,139,250,0.15); color: var(--research-color); }
  .type-badge.reject { background: rgba(107,114,128,0.15); color: var(--reject-color); }
```

在 `.pill-mixed` 之后（约第 285 行）追加：

```css
  .pill-trend { background: rgba(96,165,250,0.15); color: var(--trend-color); }
  .pill-research { background: rgba(167,139,250,0.15); color: var(--research-color); }
  .pill-reject { background: rgba(107,114,128,0.15); color: var(--reject-color); }
```

- [ ] **Step 3: 更新 JS 中的筛选器列表**

在 dashboard.html 的 JavaScript 中，找到渲染筛选器按钮的位置（使用 `filter-btn` 的地方）。搜索 `const filters`  或筛选按钮生成逻辑，将题型列表从 `['all','sql','content','mixed']` 扩展为 `['all','sql','content','mixed','trend','research','reject']`。

具体搜索包含 `filter` 和 `sql.*content.*mixed` 的行，在 `mixed` 后追加 `trend`、`research`、`reject`。

- [ ] **Step 4: 更新 JS 中的颜色映射**

找到约第 690 行的 `const colors` 对象，或类似的颜色映射。确保新题型有对应颜色。搜索 `typeColors` 或题型颜色映射，追加：

```javascript
trend: 'var(--trend-color)', research: 'var(--research-color)', reject: 'var(--reject-color)'
```

- [ ] **Step 5: 运行 lint（验证 HTML 语法）**

在浏览器中打开 `eval/dashboard.html`，确认页面正常加载，新筛选按钮可见。

- [ ] **Step 6: 提交**

```bash
git add eval/dashboard.html
git commit -m "feat: 评测 Dashboard 新增 trend/research/reject 题型支持"
```

---

### Task 7: 全量测试 + 最终验证

**Files:**
- 无新文件

- [ ] **Step 1: 运行全量测试**

Run: `uv run pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 2: 运行 lint + format**

Run: `uv run ruff check src/ tests/ eval/ && uv run ruff format src/ tests/ eval/`
Expected: 无错误

- [ ] **Step 3: 提交格式化改动（如有）**

```bash
git add -A
git commit -m "style: ruff format 格式化"
```
