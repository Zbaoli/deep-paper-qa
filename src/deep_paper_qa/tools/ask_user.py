"""ask_user 工具：暂停等待用户输入（基于 asyncio.Event，脱离 Chainlit）"""

import asyncio
from typing import Annotated, Any

from langchain_core.tools import InjectedToolArg, tool
from loguru import logger

# thread_id → (Event, 回复内容) 映射
_pending: dict[str, dict[str, Any]] = {}

# 默认超时（秒）
_DEFAULT_TIMEOUT = 300


def get_pending_question(thread_id: str) -> dict[str, Any] | None:
    """获取指定 thread 当前等待中的问题，无则返回 None"""
    entry = _pending.get(thread_id)
    if entry and not entry["event"].is_set():
        return {"question": entry["question"], "summary": entry["summary"]}
    return None


def submit_reply(thread_id: str, reply: str) -> bool:
    """提交用户回复，唤醒等待中的 ask_user。成功返回 True。"""
    entry = _pending.get(thread_id)
    if entry and not entry["event"].is_set():
        entry["reply"] = reply
        entry["event"].set()
        logger.info("ask_user | thread={} | 收到用户回复: {}", thread_id, reply[:200])
        return True
    logger.warning("ask_user | thread={} | 无等待中的问题", thread_id)
    return False


@tool
async def ask_user(
    summary: str,
    question: str,
    thread_id: Annotated[str, InjectedToolArg] = "",
    timeout: Annotated[float, InjectedToolArg] = 0,
) -> str:
    """暂停研究流程，向用户展示当前发现并等待指令。仅在深度研究模式中使用。

    在每个研究阶段结束后调用，展示阶段性发现摘要，询问用户下一步操作。
    用户可以回复"继续"、"调整方向: ..."、"总结"等指令。

    Args:
        summary: 当前阶段的发现摘要，展示给用户
        question: 向用户提的问题（如"是否继续下一个子问题？"）
    """
    effective_timeout = timeout if timeout > 0 else _DEFAULT_TIMEOUT
    logger.info(
        "ask_user | thread={} | summary_len={} | question={}",
        thread_id,
        len(summary),
        question[:100],
    )

    event = asyncio.Event()
    _pending[thread_id] = {
        "event": event,
        "question": question,
        "summary": summary,
        "reply": "",
    }

    try:
        await asyncio.wait_for(event.wait(), timeout=effective_timeout)
        reply = _pending[thread_id]["reply"]
        logger.info("ask_user | thread={} | 用户回复: {}", thread_id, reply[:200])
        return reply
    except asyncio.TimeoutError:
        logger.info("ask_user | thread={} | 用户超时未回复", thread_id)
        return "用户未回复，请继续执行下一个子问题。"
    finally:
        _pending.pop(thread_id, None)
