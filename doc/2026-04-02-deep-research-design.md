# 学术 Deep Research 功能设计

> 日期：2026-04-02
> 状态：已确认

## 目标

在现有 ReAct Agent 上扩展"深度研究模式"，支持用户对复杂学术问题进行多轮迭代检索和综合分析。用户通过 `/research` 前缀显式触发，研究过程中可在每个阶段介入引导方向。

## 适用场景

- 综述类问题（某领域主流方法有哪些？各自优劣？）
- 技术演进追踪（某技术从 2020 到 2025 怎么发展的？）
- 跨领域关联发现（A 领域的方法有没有被用到 B 领域？）
- 方法选型决策（几种方案各自在什么条件下表现好？）
- 研究空白发现（某方向还有哪些没覆盖？）

## 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 输出形式 | 渐进式流式输出 | 每轮结果逐步呈现，用户可中途引导 |
| 触发方式 | 显式触发（`/research` 前缀） | 用户主动选择，避免误触 |
| 用户介入 | 每阶段暂停等用户确认 | 用户决定继续/调整/总结 |
| 数据源 | MVP 仅现有数据库，架构预留外部数据源接口 | 先验证核心流程 |
| 终止条件 | 用户控制（每轮结束后决定继续或总结） | 配合每阶段介入机制 |
| 与现有 Agent 关系 | 同一 Agent 扩展 | 改动最小，共享工具 |
| 研究计划生成 | 纯 prompt 驱动 | 省一次 LLM 调用，更简单 |

## 整体控制流

```
用户: /research <问题>

Agent:
  1. 分析问题，分解为 3-5 个子问题，输出研究计划
     → 调用 ask_user() 展示计划，等用户确认/调整

  2. 按计划逐个执行子问题
     → 每个子问题调用 1-2 次现有 tool (search_abstracts / vector_search / execute_sql)
     → 每个子问题完成后调用 ask_user() 展示阶段性发现
     → 用户回复: "继续" / "调整方向: ..." / "总结"

  3. 用户说"总结"或所有子问题完成
     → 综合所有发现，生成结构化回答（含论文引用）
```

## 新增 Tool: `ask_user`

```python
async def ask_user(summary: str, question: str) -> str
```

- **summary**: 当前阶段的发现摘要，展示给用户
- **question**: 向用户提的问题（如"是否继续？要调整方向吗？"）
- **返回值**: 用户的回复文本
- **实现**: 内部调用 `cl.AskUserMessage(content=..., timeout=300).send()`
- **超时**: 用户 5 分钟不回复则超时，Agent 自动继续或终止

## Prompt 改造

在现有 system prompt 末尾追加深度研究模式规则（约 30-40 行）：

```
## 深度研究模式

当用户消息以 /research 开头时，进入深度研究模式：

### 第一步：制定研究计划
- 分析用户问题，分解为 3-5 个子问题
- 用 ask_user() 展示计划，等用户确认或调整
- 用户可能修改/删除/新增子问题

### 第二步：逐个执行子问题
- 每个子问题使用 1-2 次检索工具
- 每个子问题完成后调用 ask_user()，展示发现并询问：
  "继续下一个子问题 / 调整方向 / 直接生成总结"
- 如果用户给出新指令，据此调整后续计划

### 第三步：综合总结
- 用户说"总结"或所有子问题完成后
- 综合所有阶段发现，生成结构化回答
- 必须引用具体论文（标题、会议、年份）

### 约束
- 每个子问题最多调用 2 次检索工具
- 总计最多 15 次工具调用（不含 ask_user）
- ask_user 的 summary 要简洁，列出关键发现即可
```

## Chainlit UI 改造

1. **触发识别**: `on_message` 检测 `/research` 前缀，去掉前缀后传给 Agent，UI 标记研究模式
2. **ask_user 交互**: Agent 调用 `ask_user` 时展示 summary + 弹出 `AskUserMessage` 等待输入
3. **阶段性展示**: 每个 tool call 仍走现有 Step UI，不需要改
4. **流式输出**: Agent 推理和总结部分复用现有 `on_chat_model_stream`，不需要改

## 代码改动范围

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `src/deep_paper_qa/tools/ask_user.py` | 新增 | `ask_user` tool 实现 |
| `src/deep_paper_qa/prompts.py` | 修改 | 追加深度研究模式 prompt（~30-40 行） |
| `src/deep_paper_qa/agent.py` | 修改 | tool 列表加入 `ask_user`；`recursion_limit` 提高到 50 |
| `src/deep_paper_qa/app.py` | 修改 | 识别 `/research` 前缀；处理 `ask_user` 事件展示 |
| `tests/test_ask_user.py` | 新增 | mock `cl.AskUserMessage` 测试 |
| `eval/questions.jsonl` | 修改 | 追加深度研究类测试问题 |

**不需要改动**: 三个现有 tool、config.py、conversation_logger.py。

## 后续扩展方向

- 接入外部数据源（Semantic Scholar API 等）
- 支持生成最终结构化报告（Markdown 导出）
- 研究过程的 JSONL 日志扩展（记录阶段划分、用户介入点）
