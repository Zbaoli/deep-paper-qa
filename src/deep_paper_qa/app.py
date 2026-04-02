"""Chainlit 入口：Agent 流式输出 + 中间步骤展示 + 日志记录"""

import time
import uuid

import chainlit as cl
from langchain_core.messages import HumanMessage
from loguru import logger

from deep_paper_qa.agent import build_agent
from deep_paper_qa.conversation_logger import ConversationLogger
from deep_paper_qa.logging_setup import setup_logging

# 初始化日志
setup_logging()

# 全局 Agent 实例
_agent, _checkpointer = build_agent()

# 结构化事件记录器
_conv_logger = ConversationLogger()


@cl.on_chat_start
async def on_chat_start() -> None:
    """初始化会话"""
    thread_id = str(uuid.uuid4())
    cl.user_session.set("thread_id", thread_id)
    logger.info("新会话启动 | thread_id={}", thread_id)
    await cl.Message(
        content="你好！我是 AI 科研论文问答助手。可以问我关于论文的统计信息或内容问题。"
    ).send()


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
        await cl.Message(
            content="🔬 已进入深度研究模式，将分阶段进行多轮检索。"
        ).send()

    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 50 if is_research else 30,
    }

    # 记录用户消息
    logger.info(
        "用户消息 | thread_id={} | research={} | content={}",
        thread_id, is_research, user_content,
    )
    _conv_logger.log_user_message(thread_id, message.content)

    # 会话级统计
    msg_start = time.monotonic()
    tool_call_count = 0
    tools_used: list[str] = []
    # tool 调用计时：run_id -> (tool_name, start_time)
    tool_timings: dict[str, tuple[str, float]] = {}

    final_msg = cl.Message(content="")
    await final_msg.send()

    try:
        async for event in _agent.astream_events(
            {"messages": [HumanMessage(content=user_content)]},
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

                # loguru 详细日志
                logger.info(
                    "Tool调用 | thread_id={} | tool={} | input={}",
                    thread_id, tool_name, tool_input,
                )
                # JSONL 事件
                _conv_logger.log_tool_start(thread_id, tool_name, tool_input)

                # 记录开始时间
                tool_timings[run_id] = (tool_name, time.monotonic())
                tool_call_count += 1
                if tool_name not in tools_used:
                    tools_used.append(tool_name)

                # ask_user 工具通过 AskUserMessage 自行展示，不创建 Step
                if tool_name != "ask_user":
                    step = cl.Step(name=tool_name, type="tool")
                    step.input = str(tool_input)
                    await step.send()
                    cl.user_session.set(f"step_{run_id}", step)

            # 工具调用结束
            elif kind == "on_tool_end":
                run_id = event.get("run_id", "")
                output = event.get("data", {}).get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                output_str = str(output)

                # 计算耗时
                duration_ms = 0
                tool_name = "unknown"
                if run_id in tool_timings:
                    tool_name, start_t = tool_timings.pop(run_id)
                    duration_ms = int((time.monotonic() - start_t) * 1000)

                # loguru 详细日志
                logger.info(
                    "Tool返回 | thread_id={} | tool={} | duration_ms={} | "
                    "output_len={} | output={}",
                    thread_id, tool_name, duration_ms,
                    len(output_str), output_str[:1000],
                )
                # JSONL 事件
                _conv_logger.log_tool_end(
                    thread_id, tool_name, duration_ms, output_str
                )

                # Chainlit 更新步骤
                step = cl.user_session.get(f"step_{run_id}")
                if step:
                    step.output = (
                        output_str[:500] if len(output_str) > 500 else output_str
                    )
                    await step.update()

            # LLM 流式输出
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    await final_msg.stream_token(chunk.content)

        await final_msg.update()

        # 会话统计
        total_ms = int((time.monotonic() - msg_start) * 1000)
        logger.info(
            "会话统计 | thread_id={} | total_ms={} | tool_calls={} | tools_used={}",
            thread_id, total_ms, tool_call_count, tools_used,
        )
        # JSONL 汇总事件
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
