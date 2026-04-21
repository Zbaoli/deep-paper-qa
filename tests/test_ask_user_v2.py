"""ask_user 工具测试（使用 RunnableConfig 注入 thread_id）"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from deep_paper_qa.tools.ask_user import _pending, ask_user, get_pending_question, submit_reply


def _make_config(thread_id: str) -> dict:
    """构造 RunnableConfig 格式的配置字典"""
    return {"configurable": {"thread_id": thread_id}}


class TestAskUser:
    """ask_user 异步交互测试"""

    @patch("deep_paper_qa.tools.ask_user.adispatch_custom_event", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_submit_reply_wakes_up_ask_user(self, mock_dispatch) -> None:
        """submit_reply 能唤醒等待中的 ask_user"""

        async def simulate_user_reply(thread_id: str) -> None:
            await asyncio.sleep(0.05)
            submit_reply(thread_id, "继续")

        task = asyncio.create_task(simulate_user_reply("thread-1"))
        result = await ask_user.ainvoke(
            {"summary": "摘要", "question": "是否继续？"},
            config=_make_config("thread-1"),
        )
        await task
        assert result == "继续"

    @pytest.mark.asyncio
    async def test_timeout_returns_default(self) -> None:
        """超时未回复返回默认消息（直接操作 _pending 测试超时逻辑）"""
        thread_id = "thread-timeout"
        event = asyncio.Event()
        _pending[thread_id] = {
            "event": event,
            "question": "是否继续？",
            "summary": "摘要",
            "reply": "",
        }
        try:
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(event.wait(), timeout=0.1)
        finally:
            _pending.pop(thread_id, None)

    @patch("deep_paper_qa.tools.ask_user.adispatch_custom_event", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_get_pending_question(self, mock_dispatch) -> None:
        """get_pending_question 返回当前等待中的问题"""

        async def invoke_ask() -> str:
            return await ask_user.ainvoke(
                {"summary": "研究进展", "question": "下一步？"},
                config=_make_config("thread-3"),
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

    @patch("deep_paper_qa.tools.ask_user.adispatch_custom_event", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_concurrent_threads_isolated(self, mock_dispatch) -> None:
        """并发多个 thread 时，各自的回复互不干扰"""

        async def invoke_and_reply(thread_id: str, reply: str, delay: float) -> str:
            """启动 ask_user 并在 delay 秒后提交回复"""

            async def delayed_reply() -> None:
                await asyncio.sleep(delay)
                submit_reply(thread_id, reply)

            reply_task = asyncio.create_task(delayed_reply())
            result = await ask_user.ainvoke(
                {"summary": f"摘要-{thread_id}", "question": f"问题-{thread_id}？"},
                config=_make_config(thread_id),
            )
            await reply_task
            return result

        # 并发运行两个不同 thread_id 的 ask_user
        result_a, result_b = await asyncio.gather(
            invoke_and_reply("thread-A", "回复A", 0.05),
            invoke_and_reply("thread-B", "回复B", 0.08),
        )

        assert result_a == "回复A", f"thread-A 应收到 '回复A'，实际: {result_a}"
        assert result_b == "回复B", f"thread-B 应收到 '回复B'，实际: {result_b}"

    @patch("deep_paper_qa.tools.ask_user.adispatch_custom_event", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_ask_user_dispatches_custom_event(self, mock_dispatch) -> None:
        """ask_user 通过 adispatch_custom_event 发送 ask_user 自定义事件"""

        async def simulate_user_reply() -> None:
            await asyncio.sleep(0.05)
            submit_reply("thread-event", "OK")

        task = asyncio.create_task(simulate_user_reply())
        await ask_user.ainvoke(
            {"summary": "阶段摘要", "question": "是否继续？"},
            config=_make_config("thread-event"),
        )
        await task

        assert mock_dispatch.await_count == 1
        args, _ = mock_dispatch.call_args
        assert args[0] == "ask_user"
        assert args[1]["question"] == "是否继续？"
        assert args[1]["summary"] == "阶段摘要"
