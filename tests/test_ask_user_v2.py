"""ask_user 工具测试（脱离 Chainlit，基于 asyncio.Event）"""

import asyncio

import pytest

from deep_paper_qa.tools.ask_user import ask_user, get_pending_question, submit_reply


class TestAskUser:
    """ask_user 异步交互测试"""

    @pytest.mark.asyncio
    async def test_submit_reply_wakes_up_ask_user(self) -> None:
        """submit_reply 能唤醒等待中的 ask_user"""

        async def simulate_user_reply(thread_id: str) -> None:
            await asyncio.sleep(0.05)
            submit_reply(thread_id, "继续")

        task = asyncio.create_task(simulate_user_reply("thread-1"))
        result = await ask_user.ainvoke(
            {"summary": "摘要", "question": "是否继续？", "thread_id": "thread-1"}
        )
        await task
        assert result == "继续"

    @pytest.mark.asyncio
    async def test_timeout_returns_default(self) -> None:
        """超时未回复返回默认消息"""
        result = await ask_user.ainvoke(
            {
                "summary": "摘要",
                "question": "是否继续？",
                "thread_id": "thread-2",
                "timeout": 0.1,
            }
        )
        assert "未回复" in result

    @pytest.mark.asyncio
    async def test_get_pending_question(self) -> None:
        """get_pending_question 返回当前等待中的问题"""

        async def invoke_ask() -> str:
            return await ask_user.ainvoke(
                {"summary": "研究进展", "question": "下一步？", "thread_id": "thread-3"}
            )

        task = asyncio.create_task(invoke_ask())
        await asyncio.sleep(0.05)

        pending = get_pending_question("thread-3")
        assert pending is not None
        assert pending["question"] == "下一步？"
        assert pending["summary"] == "研究进展"

        submit_reply("thread-3", "总结")
        result = await task
        assert result == "总结"

    @pytest.mark.asyncio
    async def test_no_pending_question(self) -> None:
        """没有等待中的问题时返回 None"""
        pending = get_pending_question("nonexistent")
        assert pending is None
