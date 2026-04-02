"""ask_user 工具测试"""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_cl_mock(send_return_value: MagicMock | None) -> MagicMock:
    """构造 chainlit mock，返回指定的 send 结果"""
    mock_cl = MagicMock()
    mock_ask_msg = MagicMock()
    mock_ask_msg.send = AsyncMock(return_value=send_return_value)
    mock_cl.AskUserMessage.return_value = mock_ask_msg
    return mock_cl


class TestAskUser:
    """ask_user 工具测试"""

    @pytest.mark.asyncio
    async def test_returns_user_response(self) -> None:
        """正常情况：用户回复后返回回复内容"""
        mock_response = MagicMock()
        mock_response.output = "继续"

        mock_cl = _make_cl_mock(mock_response)
        # 在模块加载前注入 sys.modules，避免触发 chainlit 懒加载机制
        sys.modules["chainlit"] = mock_cl  # type: ignore[assignment]
        # 重新加载模块以使用 mock
        if "deep_paper_qa.tools.ask_user" in sys.modules:
            del sys.modules["deep_paper_qa.tools.ask_user"]

        from deep_paper_qa.tools.ask_user import ask_user

        result = await ask_user.ainvoke({
            "summary": "找到 5 篇 RAG 相关论文",
            "question": "是否继续下一个子问题？",
        })
        assert result == "继续"

    @pytest.mark.asyncio
    async def test_timeout_returns_default(self) -> None:
        """超时情况：返回默认提示"""
        mock_cl = _make_cl_mock(None)
        sys.modules["chainlit"] = mock_cl  # type: ignore[assignment]
        if "deep_paper_qa.tools.ask_user" in sys.modules:
            del sys.modules["deep_paper_qa.tools.ask_user"]

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

        mock_cl = _make_cl_mock(mock_response)
        sys.modules["chainlit"] = mock_cl  # type: ignore[assignment]
        if "deep_paper_qa.tools.ask_user" in sys.modules:
            del sys.modules["deep_paper_qa.tools.ask_user"]

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
