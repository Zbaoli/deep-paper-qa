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

    # Chainlit 2.x 返回 StepDict (dict)，用户回复在 "output" 键中
    user_reply = response.get("output", "") if isinstance(response, dict) else str(response)
    logger.info("ask_user | 用户回复: {}", user_reply[:200])
    return user_reply
