"""Chainlit 入口：Agent 流式输出 + 中间步骤展示"""

import uuid

import chainlit as cl
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from loguru import logger

from deep_paper_qa.agent import build_agent

# 全局 Agent 实例
_agent, _trimmer, _checkpointer = build_agent()


@cl.on_chat_start
async def on_chat_start() -> None:
    """初始化会话"""
    thread_id = str(uuid.uuid4())
    cl.user_session.set("thread_id", thread_id)
    logger.info("新会话启动: thread_id={}", thread_id)
    await cl.Message(content="你好！我是 AI 科研论文问答助手。可以问我关于论文的统计信息或内容问题。").send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """处理用户消息"""
    thread_id = cl.user_session.get("thread_id")
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 10,
    }

    logger.info("收到用户消息: thread_id={}, content={}", thread_id, message.content[:100])

    # 创建最终回复的 Message（用于流式更新）
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

            # 工具调用开始 → 展示中间步骤
            if kind == "on_tool_start":
                tool_name = name
                tool_input = event.get("data", {}).get("input", {})
                step = cl.Step(name=f"🔧 {tool_name}", type="tool")
                step.input = str(tool_input)
                await step.send()
                cl.user_session.set(f"step_{event.get('run_id')}", step)

            # 工具调用结束 → 更新步骤结果
            elif kind == "on_tool_end":
                run_id = event.get("run_id")
                step = cl.user_session.get(f"step_{run_id}")
                output = event.get("data", {}).get("output", "")
                if hasattr(output, "content"):
                    output = output.content
                output_str = str(output)
                if step:
                    step.output = output_str[:500] if len(output_str) > 500 else output_str
                    await step.update()

            # LLM 流式输出 token
            elif kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk", None)
                if chunk and hasattr(chunk, "content") and chunk.content:
                    await final_msg.stream_token(chunk.content)

        await final_msg.update()

    except Exception as e:
        logger.error("Agent 执行异常: {}", e)
        final_msg.content = f"抱歉，处理您的问题时出现错误：{e}"
        await final_msg.update()
