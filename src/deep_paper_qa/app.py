"""Chainlit 入口：DeepAgent 流式输出 + 中间步骤展示 + 日志记录"""

import re
import time
import uuid

import chainlit as cl
import plotly.io as pio
from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_agent
from deep_paper_qa.conversation_logger import ConversationLogger
from deep_paper_qa.logging_setup import setup_logging

setup_logging()

_agent, _checkpointer = build_agent()
_conv_logger = ConversationLogger()

# DeepAgents 内置工具名称（用于特殊展示）
_BUILTIN_TOOL_LABELS = {
    "write_todos": "📋 制定计划",
    "task": "🔀 委派子任务",
}


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
    """处理用户消息"""
    if cl.user_session.get("waiting_for_ask_user"):
        return

    thread_id = cl.user_session.get("thread_id")
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50,
    }

    logger.info("用户消息 | thread_id={} | content={}", thread_id, message.content)
    _conv_logger.log_user_message(thread_id, message.content)

    msg_start = time.monotonic()
    tool_call_count = 0
    tools_used: list[str] = []
    tool_timings: dict[str, tuple[str, float]] = {}

    final_msg = cl.Message(content="")
    await final_msg.send()

    try:
        async for event in _agent.astream_events(
            {"messages": [HumanMessage(content=message.content)]},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")
            name = event.get("name", "")

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
                    display_name = _BUILTIN_TOOL_LABELS.get(tool_name, tool_name)
                    step = cl.Step(name=display_name, type="tool")
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

            # LLM 流式输出（统一流式，不再区分管线）
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    await final_msg.stream_token(chunk.content)

        # 处理图表（generate_chart 输出嵌入在最终消息中）
        if "<!--plotly:" in final_msg.content:
            plotly_match = re.search(r"<!--plotly:(.*?)-->", final_msg.content, re.DOTALL)
            if plotly_match:
                chart_json = plotly_match.group(1)
                final_msg.content = re.sub(
                    r"<!--plotly:.*?-->\n*", "", final_msg.content, flags=re.DOTALL
                )
                try:
                    fig = pio.from_json(chart_json)
                    final_msg.elements = [
                        cl.Plotly(name="数据图表", figure=fig, display="inline")
                    ]
                except Exception as plot_err:
                    logger.warning("Plotly 图表渲染失败: {}", plot_err)

        await final_msg.update()

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
