## 前端体验优化 + 评测更新

路由架构已实现，本文档覆盖配套的前端展示优化和评测系统适配。

---

### 1. 路由过程可视化

用户提交问题后，在回答前展示路由决策过程：

- 显示 "正在分析问题类型..." 加载提示
- 路由完成后显示分类结果标签，如 "📊 趋势分析" / "🔬 深度研究" / "💬 普通问答"
- 用 Chainlit `cl.Step(name="路由", type="tool")` 包裹，可展开查看分类详情

改动文件：`app.py`（在 `astream_events` 循环前插入路由提示）、`agent.py`（router_node 输出 category 到 messages 以便前端捕获）

### 2. 趋势分析数据可视化

趋势分析的按年统计数据以图表形式展示，而非纯文本。

方案：
- 在 `trend.py` 的 `synthesize_node` 中，用 `plotly` 生成柱状图/折线图
- 通过 Chainlit `cl.Plotly` 元素嵌入消息流
- 图表内容：X 轴为年份，Y 轴为论文数量，标注各阶段分界线

改动文件：`pipelines/trend.py`（synthesize_node 增加图表生成）、`pyproject.toml`（新增 plotly 依赖）

### 3. 深度研究进度指示

深度研究执行过程中，向用户展示当前进度：

- 每个节点切换时发送进度消息：
  - "🔍 澄清问题中（1/3）"
  - "📋 正在制定研究计划..."
  - "📖 执行子问题 2/4: xxx"
  - "📝 正在生成研究报告..."
- 用 Chainlit `cl.Step` 嵌套展示各子问题的检索过程

改动文件：`pipelines/research.py`（各节点增加进度消息输出）、`app.py`（捕获进度事件并展示）

### 4. 欢迎语和 Starters 更新

更新 `app.py` 中的欢迎语和示例问题，体现新能力：

```python
@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    return [
        cl.Starter(label="会议论文统计", message="各会议论文数量是多少？"),
        cl.Starter(label="RAG 研究趋势", message="RAG 近三年的发展趋势怎么样？"),
        cl.Starter(label="深度调研", message="总结 2023-2025 年 LLM Agent 的研究脉络"),
        cl.Starter(label="高引论文推荐", message="推荐一些高引用的大语言模型论文"),
    ]
```

欢迎语增加能力说明："支持论文统计查询、内容检索、研究趋势分析和深度调研。"

改动文件：`app.py`

### 5. 评测脚本适配新架构

当前 `eval/run_eval.py` 的问题：
- `build_agent()` 已改为 `build_graph()`
- 路由正确性判断只有 sql/content/mixed 三种，缺少 research/trend/reject
- `questions.jsonl` 缺少新题型测试题

改动：
- `run_eval.py`：`build_agent` → `build_graph`，新增 trend/research/reject 的路由正确性判断
- `questions.jsonl`：补充趋势分析（5 题）、深度研究（3 题）、拒答（3 题）测试题
- `judge.py` / `judge_prompt.py`：评分维度适配新题型（trend 类侧重数据准确性，research 类侧重结构和覆盖度）

### 6. 评测 Dashboard 更新

当前 `eval/dashboard.html`（937 行）只展示 sql/content/mixed 三种题型。

更新：
- 题型筛选器增加 trend/research/reject 选项
- 新增"路由分类"列，展示每题被路由到哪个 pipeline
- 趋势分析题型增加统计数据预览（如果有）
- 按 pipeline 维度汇总统计（各 pipeline 的平均分、路由准确率）
- 颜色编码扩展：trend 用蓝色、research 用紫色、reject 用灰色

改动文件：`eval/dashboard.html`

---

## 实现优先级

### P0（影响基本可用性）

- **评测脚本适配**（第 5 项）— 当前 `run_eval.py` 直接报错，无法运行
- **欢迎语和 Starters 更新**（第 4 项）— 改动最小，立即生效

### P1（提升用户体验）

- **路由过程可视化**（第 1 项）
- **深度研究进度指示**（第 3 项）

### P2（锦上添花）

- **趋势分析数据可视化**（第 2 项）— 需要新增 plotly 依赖
- **评测 Dashboard 更新**（第 6 项）
