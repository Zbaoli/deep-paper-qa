"""Chainlit 入口：Agent 流式输出 + 中间步骤展示 + 日志记录"""

import time
import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_graph
from deep_paper_qa.conversation_logger import ConversationLogger
from deep_paper_qa.logging_setup import setup_logging

# 初始化日志
setup_logging()

# 全局 Graph 实例
_graph, _checkpointer = build_graph()

# 结构化事件记录器
_conv_logger = ConversationLogger()


@cl.set_starters
async def set_starters() -> list[cl.Starter]:
    """提供示例问题，引导新用户快速上手"""
    return [
        cl.Starter(label="会议论文统计", message="各会议论文数量是多少？"),
        cl.Starter(label="RAG 研究趋势", message="RAG 近三年的发展趋势怎么样？"),
        cl.Starter(label="深度调研", message="总结 2023-2025 年 LLM Agent 的研究脉络"),
        cl.Starter(label="高引论文推荐", message="推荐一些高引用的大语言模型论文"),
    ]


@cl.on_chat_start
async def on_chat_start() -> None:
    """初始化会话"""
    thread_id = str(uuid.uuid4())
    cl.user_session.set("thread_id", thread_id)
    logger.info("新会话启动 | thread_id={}", thread_id)
    await cl.Message(
        content="你好！我是 AI 科研论文问答助手，支持论文统计查询、内容检索、研究趋势分析和深度调研。"
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """处理用户消息，记录完整事件链"""
    # 如果有 ask_user 正在等待回复，跳过新的 graph 调用（让 AskUserMessage 接收回复）
    if cl.user_session.get("waiting_for_ask_user"):
        return

    thread_id = cl.user_session.get("thread_id")

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50,
    }

    # 记录用户消息
    logger.info("用户消息 | thread_id={} | content={}", thread_id, message.content)
    _conv_logger.log_user_message(thread_id, message.content)

    # 会话级统计
    msg_start = time.monotonic()
    tool_call_count = 0
    tools_used: list[str] = []
    tool_timings: dict[str, tuple[str, float]] = {}

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
            {"messages": [HumanMessage(content=message.content)]},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            name = event.get("name", "")

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

            # 工具调用开始
            if kind == "on_tool_start":
                tool_name = name
                tool_input = event.get("data", {}).get("input", {})
                run_id = event.get("run_id", "")

                logger.info(
                    "Tool调用 | thread_id={} | tool={} | input={}",
                    thread_id,
                    tool_name,
                    tool_input,
                )
                _conv_logger.log_tool_start(thread_id, tool_name, tool_input)

                tool_timings[run_id] = (tool_name, time.monotonic())
                tool_call_count += 1
                if tool_name not in tools_used:
                    tools_used.append(tool_name)

                if tool_name == "ask_user":
                    cl.user_session.set("waiting_for_ask_user", True)
                else:
                    step = cl.Step(name=tool_name, type="tool")
                    step.input = str(tool_input)
                    await step.send()
                    cl.user_session.set(f"step_{run_id}", step)

            # 工具调用结束
            elif kind == "on_tool_end":
                if name == "ask_user":
                    cl.user_session.set("waiting_for_ask_user", False)
                run_id = event.get("run_id", "")
                output = event.get("data", {}).get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                output_str = str(output)

                duration_ms = 0
                tool_name = "unknown"
                if run_id in tool_timings:
                    tool_name, start_t = tool_timings.pop(run_id)
                    duration_ms = int((time.monotonic() - start_t) * 1000)

                logger.info(
                    "Tool返回 | thread_id={} | tool={} | duration_ms={} | "
                    "output_len={} | output={}",
                    thread_id,
                    tool_name,
                    duration_ms,
                    len(output_str),
                    output_str[:1000],
                )
                _conv_logger.log_tool_end(thread_id, tool_name, duration_ms, output_str)

                step = cl.user_session.get(f"step_{run_id}")
                if step:
                    step.output = output_str[:500] if len(output_str) > 500 else output_str
                    await step.update()

            # LLM 流式输出（跳过路由节点的 LLM 输出）
            elif kind == "on_chat_model_stream" and router_shown:
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    await final_msg.stream_token(chunk.content)

        # 从 checkpointer 获取最终消息（处理非流式 pipeline 如 research/trend）
        try:
            from langchain_core.messages import AIMessage as _AIMessage

            state = _graph.get_state(config)
            msgs = state.values.get("messages", [])
            # 取最后一条 AI 消息
            for m in reversed(msgs):
                if isinstance(m, _AIMessage) and m.content:
                    # 如果是研究报告或趋势报告，用 state 中的完整内容覆盖流式碎片
                    if "**[研究报告]**" in m.content or "<!--plotly:" in m.content:
                        final_msg.content = m.content
                    # 如果流式输出为空，用 state 中的内容兜底
                    elif not final_msg.content.strip():
                        final_msg.content = m.content
                    break
        except Exception as state_err:
            logger.warning("获取最终状态失败: {}", state_err)

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

        await final_msg.update()

        # 会话统计
        total_ms = int((time.monotonic() - msg_start) * 1000)
        logger.info(
            "会话统计 | thread_id={} | total_ms={} | tool_calls={} | tools_used={}",
            thread_id,
            total_ms,
            tool_call_count,
            tools_used,
        )
        _conv_logger.log_agent_reply(
            thread_id,
            final_msg.content,
            total_ms,
            tool_call_count,
            tools_used,
        )

    except Exception as e:
        logger.error("Agent 执行异常 | thread_id={} | error={}", thread_id, e)
        final_msg.content = f"抱歉，处理您的问题时出现错误：{e}"
        await final_msg.update()
