# Deep Research 功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 ReAct Agent 上扩展"深度研究模式"，用户通过 `/research` 前缀触发多轮迭代检索，每阶段可介入引导方向。

**Architecture:** 新增 `ask_user` tool（内部调用 Chainlit `AskUserMessage`），在 system prompt 末尾追加深度研究模式规则，app.py 识别 `/research` 前缀并调整 `recursion_limit`。现有 3 个检索 tool 完全复用。

**Tech Stack:** LangGraph, LangChain, Chainlit (`AskUserMessage`), asyncio, pytest

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `src/deep_paper_qa/tools/ask_user.py` | **新增** — `ask_user` tool，封装 Chainlit `AskUserMessage` |
| `src/deep_paper_qa/prompts.py` | **修改** — 末尾追加深度研究模式 prompt |
| `src/deep_paper_qa/agent.py` | **修改** — tool 列表加入 `ask_user` |
| `src/deep_paper_qa/app.py` | **修改** — 识别 `/research` 前缀，调整 recursion_limit，处理 `ask_user` 事件 |
| `tests/test_ask_user.py` | **新增** — `ask_user` tool 单元测试 |
| `tests/test_agent.py` | **修改** — 验证新 tool 已注册 |

---

### Task 1: 实现 `ask_user` tool

**Files:**
- Create: `src/deep_paper_qa/tools/ask_user.py`
- Test: `tests/test_ask_user.py`

- [ ] **Step 1: 编写 `ask_user` 的 failing test**

```python
# tests/test_ask_user.py
"""ask_user 工具测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestAskUser:
    """ask_user 工具测试"""

    @pytest.mark.asyncio
    async def test_returns_user_response(self) -> None:
        """正常情况：用户回复后返回回复内容"""
        mock_response = MagicMock()
        mock_response.output = "继续"

        with patch("deep_paper_qa.tools.ask_user.cl") as mock_cl:
            mock_ask = AsyncMock(return_value=mock_response)
            mock_cl.AskUserMessage.return_value = MagicMock(send=mock_ask)

            from deep_paper_qa.tools.ask_user import ask_user

            result = await ask_user.ainvoke({
                "summary": "找到 5 篇 RAG 相关论文",
                "question": "是否继续下一个子问题？",
            })
            assert result == "继续"

    @pytest.mark.asyncio
    async def test_timeout_returns_default(self) -> None:
        """超时情况：返回默认提示"""
        with patch("deep_paper_qa.tools.ask_user.cl") as mock_cl:
            mock_ask = AsyncMock(return_value=None)
            mock_cl.AskUserMessage.return_value = MagicMock(send=mock_ask)

            from deep_paper_qa.tools.ask_user import ask_user

            result = await ask_user.ainvoke({
                "summary": "找到 5 篇论文",
                "question": "是否继续？",
            })
            assert "继续" in result

    @pytest.mark.asyncio
    async def test_formats_message_with_summary_and_question(self) -> None:
        """验证展示给用户的消息包含 summary 和 question"""
        mock_response = MagicMock()
        mock_response.output = "总结"

        with patch("deep_paper_qa.tools.ask_user.cl") as mock_cl:
            mock_ask = AsyncMock(return_value=mock_response)
            mock_cl.AskUserMessage.return_value = MagicMock(send=mock_ask)

            from deep_paper_qa.tools.ask_user import ask_user

            await ask_user.ainvoke({
                "summary": "阶段性发现摘要",
                "question": "下一步？",
            })

            # 验证 AskUserMessage 被调用，且 content 包含 summary 和 question
            call_args = mock_cl.AskUserMessage.call_args
            content = call_args[1]["content"]
            assert "阶段性发现摘要" in content
            assert "下一步？" in content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_ask_user.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'deep_paper_qa.tools.ask_user'`

- [ ] **Step 3: 实现 `ask_user` tool**

```python
# src/deep_paper_qa/tools/ask_user.py
"""ask_user 工具：深度研究模式中暂停等待用户输入"""

import chainlit as cl
from langchain_core.tools import tool
from loguru import logger


@tool
async def ask_user(summary: str, question: str) -> str:
    """暂停研究流程，向用户展示当前发现并等待指令。仅在深度研究模式中使用。

    在每个研究阶段结束后调用，展示阶段性发现摘要，询问用户下一步操作。
    用户可以回复"继续"、"调整方向: ..."、"总结"等指令。

    Args:
        summary: 当前阶段的发现摘要，展示给用户
        question: 向用户提的问题（如"是否继续下一个子问题？"）
    """
    content = f"**研究进展**\n\n{summary}\n\n---\n\n{question}"
    logger.info("ask_user | summary_len={} | question={}", len(summary), question[:100])

    response = await cl.AskUserMessage(content=content, timeout=300).send()

    if response is None:
        logger.info("ask_user | 用户超时未回复，默认继续")
        return "用户未回复，请继续执行下一个子问题。"

    logger.info("ask_user | 用户回复: {}", response.output[:200])
    return response.output
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_ask_user.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/tools/ask_user.py tests/test_ask_user.py
git commit -m "feat: 新增 ask_user 工具，支持深度研究模式中暂停等待用户输入"
```

---

### Task 2: 追加深度研究模式 Prompt

**Files:**
- Modify: `src/deep_paper_qa/prompts.py:145`

- [ ] **Step 1: 编写 prompt 内容校验的 failing test**

在 `tests/test_agent.py` 末尾追加:

```python
class TestDeepResearchPrompt:
    """深度研究模式 prompt 测试"""

    def test_system_prompt_contains_deep_research_section(self) -> None:
        """system prompt 包含深度研究模式规则"""
        from deep_paper_qa.prompts import SYSTEM_PROMPT

        assert "深度研究模式" in SYSTEM_PROMPT
        assert "ask_user" in SYSTEM_PROMPT
        assert "/research" in SYSTEM_PROMPT
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_agent.py::TestDeepResearchPrompt -v`
Expected: FAIL — `AssertionError` (当前 prompt 不含深度研究模式)

- [ ] **Step 3: 在 prompts.py 末尾追加深度研究模式规则**

在 `src/deep_paper_qa/prompts.py` 的 `SYSTEM_PROMPT` 字符串末尾（第 145 行 `"""` 之前）追加:

```python
深度研究模式：

当用户消息以 /research 开头时，进入深度研究模式。这是一个多轮迭代研究流程，适用于综述类、技术演进、跨领域对比等复杂学术问题。

第一步：制定研究计划
- 分析用户问题，分解为 3-5 个可检索的子问题
- 为每个子问题注明计划使用的工具（execute_sql / search_abstracts / vector_search）
- 调用 ask_user() 展示研究计划，等待用户确认或调整
- 用户可能修改、删除或新增子问题，据此调整计划

第二步：逐个执行子问题
- 按计划顺序执行每个子问题，每个子问题最多调用 2 次检索工具
- 每个子问题完成后，调用 ask_user() 展示该阶段发现的关键论文和结论
- ask_user 的 summary 要简洁：列出关键发现（论文标题+会议+年份）和初步结论
- ask_user 的 question 固定为："请选择：继续下一个子问题 / 调整方向（请说明）/ 直接生成总结"
- 根据用户回复决定：继续、调整后续计划、或跳到总结

第三步：综合总结
- 当用户回复"总结"或所有子问题执行完毕时，进入总结阶段
- 综合所有阶段的发现，生成结构化回答
- 必须引用具体论文（标题、会议、年份）
- 如有不同子问题的结果可以对比，给出对比分析

深度研究模式约束：
- 每个子问题最多调用 2 次检索工具
- 总计最多 15 次工具调用（不含 ask_user）
- 普通模式的效率规则在深度研究模式中不适用（允许多次检索同一主题的不同方面）
- 关键词扩展规则仍然适用
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_agent.py::TestDeepResearchPrompt -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/prompts.py tests/test_agent.py
git commit -m "feat: system prompt 追加深度研究模式规则"
```

---

### Task 3: Agent 注册 `ask_user` tool

**Files:**
- Modify: `src/deep_paper_qa/agent.py:1-52`

- [ ] **Step 1: 编写 tool 注册校验的 failing test**

在 `tests/test_agent.py` 的 `TestBuildAgent` 类中追加:

```python
    def test_agent_has_ask_user_tool(self) -> None:
        """Agent 应包含 ask_user 工具"""
        from deep_paper_qa.agent import build_agent

        agent, _ = build_agent()
        tool_names = [t.name for t in agent.tools]
        assert "ask_user" in tool_names
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_agent.py::TestBuildAgent::test_agent_has_ask_user_tool -v`
Expected: FAIL — `ask_user` 不在 tool_names 中

- [ ] **Step 3: 修改 agent.py，加入 ask_user tool**

在 `src/deep_paper_qa/agent.py` 中:

1. 添加 import:
```python
from deep_paper_qa.tools.ask_user import ask_user
```

2. 修改 tools 列表:
```python
    tools = [execute_sql, search_abstracts, vector_search, ask_user]
```

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_agent.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add src/deep_paper_qa/agent.py tests/test_agent.py
git commit -m "feat: Agent 注册 ask_user 工具"
```

---

### Task 4: Chainlit UI 适配

**Files:**
- Modify: `src/deep_paper_qa/app.py:36-155`

- [ ] **Step 1: 修改 `on_message` — 识别 `/research` 前缀并调整 recursion_limit**

在 `src/deep_paper_qa/app.py` 的 `on_message` 函数中，替换消息处理逻辑开头部分:

```python
@cl.on_message
async def on_message(message: cl.Message) -> None:
    """处理用户消息，记录完整事件链"""
    thread_id = cl.user_session.get("thread_id")

    # 检测深度研究模式
    user_content = message.content
    is_research = user_content.startswith("/research")
    if is_research:
        user_content = user_content[len("/research"):].strip()
        if not user_content:
            await cl.Message(content="请在 /research 后输入您的研究问题。").send()
            return
        await cl.Message(content="🔬 已进入深度研究模式，将分阶段进行多轮检索。").send()

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50 if is_research else 30,
    }

    # 记录用户消息
    logger.info("用户消息 | thread_id={} | research={} | content={}", thread_id, is_research, user_content)
    _conv_logger.log_user_message(thread_id, message.content)
```

后续 `astream_events` 调用中，将 `message.content` 替换为 `user_content`:

```python
        async for event in _agent.astream_events(
            {"messages": [HumanMessage(content=user_content)]},
            config=config,
            version="v2",
        ):
```

- [ ] **Step 2: 修改 `on_tool_start` — `ask_user` tool 不展示为普通 Step**

在 `on_tool_start` 分支中，对 `ask_user` 做特殊处理（不创建 Step UI，因为 `ask_user` 自己通过 `AskUserMessage` 展示内容）:

```python
            # 工具调用开始
            if kind == "on_tool_start":
                tool_name = name
                tool_input = event.get("data", {}).get("input", {})
                run_id = event.get("run_id", "")

                logger.info(
                    "Tool调用 | thread_id={} | tool={} | input={}",
                    thread_id, tool_name, tool_input,
                )
                _conv_logger.log_tool_start(thread_id, tool_name, tool_input)

                tool_timings[run_id] = (tool_name, time.monotonic())
                tool_call_count += 1
                if tool_name not in tools_used:
                    tools_used.append(tool_name)

                # ask_user 工具通过 AskUserMessage 自行展示，不创建 Step
                if tool_name != "ask_user":
                    step = cl.Step(name=f"🔧 {tool_name}", type="tool")
                    step.input = str(tool_input)
                    await step.send()
                    cl.user_session.set(f"step_{run_id}", step)
```

- [ ] **Step 3: 运行全量测试确认无回归**

Run: `uv run pytest tests/ -v`
Expected: ALL PASS

- [ ] **Step 4: 提交**

```bash
git add src/deep_paper_qa/app.py
git commit -m "feat: Chainlit 适配深度研究模式，识别 /research 前缀并处理 ask_user 事件"
```

---

### Task 5: 端到端手动验证

- [ ] **Step 1: 启动应用**

Run: `uv run chainlit run src/deep_paper_qa/app.py`

- [ ] **Step 2: 测试普通问答（回归测试）**

在 UI 中输入: `2024 年 NeurIPS 有多少论文？`
Expected: 正常返回统计结果，行为与之前一致

- [ ] **Step 3: 测试深度研究模式**

在 UI 中输入: `/research Transformer 在医学影像分割领域的主流方法有哪些？各自优劣？`
Expected:
1. 显示"已进入深度研究模式"
2. Agent 输出研究计划（3-5 个子问题）
3. 弹出 AskUserMessage 等待确认
4. 回复"继续"后 Agent 执行第一个子问题
5. 每个子问题完成后再次弹出 AskUserMessage
6. 回复"总结"后 Agent 生成综合回答

- [ ] **Step 4: 测试空 /research 命令**

在 UI 中输入: `/research`
Expected: 提示"请在 /research 后输入您的研究问题。"

- [ ] **Step 5: 测试用户调整方向**

在 UI 中输入: `/research RAG 和长上下文方法的对比`
在第一个子问题完成后回复: `调整方向：重点关注 2024-2025 的论文`
Expected: Agent 根据用户指令调整后续检索范围
